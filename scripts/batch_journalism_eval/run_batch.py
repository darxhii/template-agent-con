#!/usr/bin/env python3
"""Batch-evaluate the template agent pipeline against a story manifest.

Measures wall-clock time per story and extracts **Fact-check score** (0–100) from
streamed output when the fact-checker emits `Score: XX/100` per `fact-check-score` skill.

Environment:
  AGENT_URL       Base URL (default: http://127.0.0.1:5002)
  AGENT_X_TOKEN   Optional X-Token header for SSO

Usage:
  cd agent && uv run python scripts/batch_journalism_eval/run_batch.py run \\
      --manifest scripts/batch_journalism_eval/manifest_100.json \\
      --out results/run_001.jsonl

  # Parallel streams + continue after interruption (skip ids already in JSONL):
  uv run python scripts/batch_journalism_eval/run_batch.py run \\
      --manifest scripts/batch_journalism_eval/manifest_100.json \\
      --out results/eval_100.jsonl --workers 4 --resume

  uv run python scripts/batch_journalism_eval/run_batch.py report \\
      --results results/run_001.jsonl \\
      --out results/report_run_001.md

  # Optional baseline (same story ids, produced by pointing AGENT_URL at baseline stack):
  uv run python scripts/batch_journalism_eval/run_batch.py report \\
      --results results/proposed.jsonl --baseline results/baseline.jsonl \\
      --out results/compare.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import threading
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:
    print("Install httpx: uv add httpx (or pip install httpx)", file=sys.stderr)
    raise

SCORE_RE = re.compile(
    r"(?:\*\*)?Score:\s*(\d+)\s*/\s*100",
    re.IGNORECASE | re.MULTILINE,
)
SCORE_NA_RE = re.compile(r"Score:\s*N/A", re.IGNORECASE)


def load_manifest(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "stories" in raw:
        return list(raw["stories"])
    if isinstance(raw, list):
        return raw
    raise ValueError("Manifest must be a list or {\"stories\": [...]}")


def existing_result_ids(out_path: Path) -> set[str]:
    """Story ids already recorded in JSONL (non-meta lines)."""
    if not out_path.is_file():
        return set()
    found: set[str] = set()
    for line in out_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "meta" in obj and len(obj) == 1:
            continue
        sid = obj.get("id")
        if sid is not None:
            found.add(str(sid))
    return found


def accumulate_stream_text(response: httpx.Response) -> str:
    """Parse agent /v1/stream newline-delimited JSON chunks (see UI useDataStream)."""
    parts: list[str] = []
    buffer = ""
    for chunk in response.iter_bytes():
        buffer += chunk.decode("utf-8", errors="replace")
        blocks = buffer.split("\n\n")
        buffer = blocks.pop() if blocks else ""
        for block in blocks:
            line = block.strip()
            if not line or line in ("[DONE]", "DONE", "data: [DONE]"):
                continue
            if line.startswith("data: "):
                line = line[6:].strip()
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = obj.get("type")
            c = obj.get("content")
            if t == "token" and isinstance(c, str):
                parts.append(c)
            elif t == "message":
                if isinstance(c, dict):
                    inner = c.get("content")
                    if isinstance(inner, str):
                        parts.append(inner)
                elif isinstance(c, str):
                    parts.append(c)
            elif t == "error":
                parts.append(f"\n[STREAM_ERROR] {json.dumps(c)}\n")
    return "".join(parts)


def extract_fact_check_score(full_text: str) -> tuple[int | None, str]:
    """Returns (score_or_none, status: ok|N/A|missing)."""
    if SCORE_NA_RE.search(full_text):
        return None, "N/A"
    matches = list(SCORE_RE.finditer(full_text))
    if not matches:
        return None, "missing"
    return int(matches[-1].group(1)), "ok"


def run_one(
    client: httpx.Client,
    base_url: str,
    headers: dict[str, str],
    story: dict[str, Any],
) -> dict[str, Any]:
    prompt = story["prompt"]
    story_id = story.get("id", str(uuid.uuid4()))
    thread_id = f"batch-{story_id}-{uuid.uuid4().hex[:8]}"
    body = {
        "message": prompt,
        "thread_id": thread_id,
        "session_id": thread_id,
        "user_id": os.environ.get("BATCH_USER_ID", "batch-journalism-eval"),
        "stream_tokens": True,
    }
    t0 = time.perf_counter()
    err: str | None = None
    text = ""
    try:
        with client.stream(
            "POST",
            f"{base_url.rstrip('/')}/v1/stream",
            json=body,
            headers=headers,
            timeout=httpx.Timeout(connect=30.0, read=None, write=30.0, pool=30.0),
        ) as resp:
            if resp.status_code != 200:
                err = f"HTTP {resp.status_code}: {resp.text[:500]}"
            else:
                text = accumulate_stream_text(resp)
    except Exception as e:  # noqa: BLE001
        err = f"{type(e).__name__}: {e}"
    elapsed = time.perf_counter() - t0
    score, score_status = extract_fact_check_score(text) if not err else (None, "error")

    return {
        "id": story_id,
        "category": story.get("category", ""),
        "target_words": story.get("target_words"),
        "elapsed_seconds": round(elapsed, 3),
        "fact_check_score": score,
        "score_parse_status": score_status if not err else "error",
        "http_error": err,
        "response_chars": len(text),
    }


def _run_single_story(
    base_url: str,
    headers: dict[str, str],
    story: dict[str, Any],
) -> dict[str, Any]:
    """One story = one short-lived httpx client (safe for thread-pool workers)."""
    with httpx.Client() as client:
        row = run_one(client, base_url, headers, story)
    row["prompt_excerpt"] = (story.get("prompt") or "")[:120]
    return row


def cmd_run(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    stories = load_manifest(manifest_path)
    if args.limit:
        stories = stories[: args.limit]

    base_url = os.environ.get("AGENT_URL", "http://127.0.0.1:5002")
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
    token = os.environ.get("AGENT_X_TOKEN")
    if token:
        headers["X-Token"] = token

    resume = bool(getattr(args, "resume", False))
    done_ids = existing_result_ids(out_path) if resume and out_path.is_file() else set()
    pending = [s for s in stories if str(s.get("id", "")) not in done_ids]

    fresh_file = not (resume and out_path.is_file() and out_path.stat().st_size > 0)
    if fresh_file:
        meta = {
            "started_at": datetime.now(UTC).isoformat(),
            "agent_url": base_url,
            "manifest": str(manifest_path),
            "n_stories": len(stories),
            "workers": max(1, int(args.workers)),
        }
        out_path.write_text(json.dumps({"meta": meta}) + "\n", encoding="utf-8")
    else:
        print(
            f"Resume: {len(done_ids)} story id(s) already in {out_path}, "
            f"{len(pending)} remaining.",
            flush=True,
        )

    if not pending:
        print("Nothing to run (manifest empty or all ids already in output).", flush=True)
        return 0

    workers = max(1, int(args.workers))
    write_lock = threading.Lock()
    completed = 0

    if workers == 1:
        for story in pending:
            sid = story.get("id", "?")
            print(f"[{completed + 1}/{len(pending)}] {sid} ...", flush=True)
            row = _run_single_story(base_url, headers, story)
            with write_lock:
                with out_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            completed += 1
    else:
        print(
            f"Running {len(pending)} stories with --workers {workers} "
            f"(concurrent HTTP streams; ensure the agent can handle the load).",
            flush=True,
        )
        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_map = {
                pool.submit(_run_single_story, base_url, headers, s): s for s in pending
            }
            for fut in as_completed(future_map):
                story = future_map[fut]
                sid = story.get("id", "?")
                try:
                    row = fut.result()
                except Exception as e:  # noqa: BLE001
                    row = {
                        "id": story.get("id", str(uuid.uuid4())),
                        "category": story.get("category", ""),
                        "target_words": story.get("target_words"),
                        "elapsed_seconds": 0.0,
                        "fact_check_score": None,
                        "score_parse_status": "error",
                        "http_error": f"{type(e).__name__}: {e}",
                        "response_chars": 0,
                        "prompt_excerpt": (story.get("prompt") or "")[:120],
                    }
                with write_lock:
                    completed += 1
                    with out_path.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    print(
                        f"[{completed}/{len(pending)}] {row.get('id', sid)} "
                        f"score={row.get('fact_check_score')} err={bool(row.get('http_error'))}",
                        flush=True,
                    )

    print(f"Appended {len(pending)} row(s) to {out_path}", flush=True)
    return 0


def _read_jsonl_results(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if "meta" in obj and len(obj) == 1:
            continue
        rows.append(obj)
    return rows


def cmd_report(args: argparse.Namespace) -> int:
    results_path = Path(args.results)
    rows = _read_jsonl_results(results_path)
    if not rows:
        print("No result rows found (skip meta-only lines).", file=sys.stderr)
        return 1

    baseline_map: dict[str, dict[str, Any]] = {}
    if args.baseline:
        for r in _read_jsonl_results(Path(args.baseline)):
            baseline_map[str(r["id"])] = r

    by_cat: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_cat[r.get("category") or "unknown"].append(r)

    scores_ok = [r["fact_check_score"] for r in rows if r.get("fact_check_score") is not None]
    latencies = [r["elapsed_seconds"] for r in rows if not r.get("http_error")]
    completed = sum(1 for r in rows if not r.get("http_error"))

    lines: list[str] = []
    lines.append("# Batch journalism evaluation report\n")
    lines.append(f"- **Generated:** {datetime.now(UTC).isoformat()} UTC\n")
    lines.append(f"- **Results file:** `{results_path}`\n")
    lines.append(f"- **Stories (rows):** {len(rows)}\n")
    lines.append(f"- **Pipeline completion (no HTTP error):** {completed}/{len(rows)} ({100 * completed / len(rows):.1f}%)\n")

    if latencies:
        lines.append("\n## Latency (wall time per story)\n\n")
        lines.append(f"| Metric | Seconds |\n|--------|--------:|\n")
        lines.append(f"| Mean (Y candidate) | **{statistics.mean(latencies):.2f}** |\n")
        lines.append(f"| Median | {statistics.median(latencies):.2f} |\n")
        if len(latencies) > 1:
            lines.append(f"| Stdev | {statistics.stdev(latencies):.2f} |\n")
        lines.append(f"| Min | {min(latencies):.2f} |\n")
        lines.append(f"| Max | {max(latencies):.2f} |\n")

    lines.append("\n## Fact-check score\n\n")
    na_missing = sum(
        1 for r in rows if r.get("score_parse_status") in ("N/A", "missing") and not r.get("http_error")
    )
    lines.append(f"- Rows with parsed **Score: XX/100:** {len(scores_ok)}\n")
    lines.append(f"- Rows with **N/A** or **missing** score (non-error): {na_missing}\n")
    if scores_ok:
        z = statistics.mean(scores_ok)
        lines.append(f"- **Mean fact-check score (Z candidate):** **{z:.2f}** / 100\n")
        if len(scores_ok) > 1:
            lines.append(f"- Stdev: {statistics.stdev(scores_ok):.2f}\n")

    lines.append("\n## By category\n\n")
    lines.append(
        "| Category | N | Completed | Mean latency (s) | Mean score | Scores parsed |\n"
        "|----------|--:|:---------:|-----------------:|-----------:|:-------------:|\n"
    )
    for cat in sorted(by_cat.keys()):
        rs = by_cat[cat]
        comp = [r for r in rs if not r.get("http_error")]
        lats = [r["elapsed_seconds"] for r in comp]
        sc = [r["fact_check_score"] for r in rs if r.get("fact_check_score") is not None]
        mean_lat = f"{statistics.mean(lats):.2f}" if lats else "—"
        mean_sc = f"{statistics.mean(sc):.2f}" if sc else "—"
        parsed = len(sc)
        lines.append(
            f"| {cat} | {len(rs)} | {len(comp)} | {mean_lat} | {mean_sc} | {parsed} |\n"
        )

    if baseline_map:
        lines.append("\n## Baseline comparison (same story `id`)\n\n")
        pairs_score: list[tuple[int, int]] = []
        pairs_lat: list[tuple[float, float]] = []
        for r in rows:
            bid = str(r["id"])
            b = baseline_map.get(bid)
            if not b or r.get("http_error") or b.get("http_error"):
                continue
            if r.get("fact_check_score") is not None and b.get("fact_check_score") is not None:
                pairs_score.append((b["fact_check_score"], r["fact_check_score"]))
            pairs_lat.append((b["elapsed_seconds"], r["elapsed_seconds"]))
        if pairs_score:
            deltas = [p - q for q, p in pairs_score]
            lines.append(
                f"- **Mean Δ fact-check score (proposed − baseline):** {statistics.mean(deltas):+.2f}\n"
            )
        if pairs_lat:
            lat_d = [p - q for q, p in pairs_lat]
            lines.append(f"- **Mean Δ latency (proposed − baseline):** {statistics.mean(lat_d):+.2f} s\n")

    lines.append("\n## Abstract placeholders\n\n")
    lines.append(
        "Fill your abstract using **your** definitions of “processing time” and “fact-check score”:\n\n"
        "- **Y (seconds per story):** use **Mean** from *Latency* if wall time matches your paper’s definition.\n"
        "- **Z (average fact-check score):** use **Mean fact-check score** when `score_parse_status` is mostly `ok`.\n"
        "- **10,000 vs 100:** align the abstract’s *N* with runs (e.g. repeat this batch or aggregate shards).\n"
        "- **Baseline:** run the same manifest against your single-agent RAG endpoint; pass `--baseline` here.\n"
        "- **56% compression / RAG:** not measured by this script — log separately from your Layer 3 implementation.\n"
    )

    errors = [r for r in rows if r.get("http_error")]
    if errors:
        lines.append("\n## Errors (first 10)\n\n")
        for r in errors[:10]:
            lines.append(f"- `{r.get('id')}`: {r.get('http_error')}\n")

    out_md = Path(args.out)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote {out_md}", flush=True)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Batch journalism eval harness")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("run", help="Run manifest against AGENT_URL")
    pr.add_argument("--manifest", required=True, type=Path)
    pr.add_argument("--out", required=True, type=Path, help="JSONL output path")
    pr.add_argument("--limit", type=int, default=0, help="Only first N stories (smoke test)")
    pr.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Concurrent stories (separate HTTP streams). Default 1 (sequential).",
    )
    pr.add_argument(
        "--resume",
        action="store_true",
        help="Append only stories whose `id` is not already present in --out (skip meta lines).",
    )
    pr.set_defaults(func=cmd_run)

    prp = sub.add_parser("report", help="Generate Markdown report from JSONL")
    prp.add_argument("--results", required=True, type=Path)
    prp.add_argument("--baseline", type=Path, default=None, help="Optional baseline JSONL for comparison")
    prp.add_argument("--out", required=True, type=Path)
    prp.set_defaults(func=cmd_report)

    args = p.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

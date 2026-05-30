"""Algorithm 1: priority dequeue, pool acquire, process, enqueue next / retry / DLQ."""

from __future__ import annotations

import asyncio
import itertools
import json
import os
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any, TextIO

import httpx

from .http_client import StreamResult, backoff_seconds, stream_one_message
from .pipeline import (
    DispatchMode,
    build_user_message,
    initial_message_for_story,
    next_messages,
)
from .pools import PoolSet
from .types import AgentType, StoryMessage


def _is_terminal_success(mode: DispatchMode, msg: StoryMessage, nxt: list[StoryMessage]) -> bool:
    if nxt:
        return False
    if mode == "monolith":
        return msg.target_agent == AgentType.PIPELINE_MONOLITH
    if msg.target_agent == AgentType.NEWSLETTER_PUBLISHER:
        return True
    if msg.target_agent == AgentType.EDITOR:
        return not (msg.send_newsletter and msg.recipient_email)
    return False


def _dlq_record(msg: StoryMessage, reason: str) -> dict[str, Any]:
    d = asdict(msg)
    d["dlq_reason"] = reason
    d["target_agent"] = str(msg.target_agent)
    d["priority"] = int(msg.priority)
    return d


async def run_dispatch(
    *,
    stories: list[dict[str, Any]],
    mode: DispatchMode,
    base_url: str,
    headers: dict[str, str],
    pools: PoolSet,
    num_workers: int,
    out_fp: TextIO,
    dlq_path: Path | None,
    on_progress: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    """Run workers until every root story reaches terminal success or DLQ."""
    seq = itertools.count()
    q: asyncio.PriorityQueue[tuple[int, int, StoryMessage]] = asyncio.PriorityQueue()
    user_id = os.environ.get("DISPATCH_USER_ID", "story-dispatch-worker")
    remaining_roots: set[str] = set()
    dlq_rows: list[dict[str, Any]] = []
    state_lock = asyncio.Lock()
    active = 0
    done_event = asyncio.Event()

    def log(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    for story in stories:
        sid = str(story.get("id", uuid.uuid4()))
        remaining_roots.add(sid)
        tid = f"dispatch-{sid}-{uuid.uuid4().hex[:10]}"
        timeout = float(story.get("timeout_seconds", 900.0))
        m0 = initial_message_for_story(
            story,
            mode=mode,
            thread_id=tid,
            user_id=user_id,
            timeout_seconds=timeout,
        )
        await q.put((m0.priority.value, next(seq), m0))

    async def mark_root_done(story_id: str) -> None:
        nonlocal remaining_roots
        async with state_lock:
            remaining_roots.discard(story_id)
            if not remaining_roots and q.empty() and active == 0:
                done_event.set()

    async def worker(worker_id: int) -> None:
        nonlocal active
        async with httpx.AsyncClient() as client:
            while not done_event.is_set():
                try:
                    _pri, _s, msg = await asyncio.wait_for(q.get(), timeout=0.35)
                except TimeoutError:
                    async with state_lock:
                        if (
                            not done_event.is_set()
                            and not remaining_roots
                            and q.empty()
                            and active == 0
                        ):
                            done_event.set()
                    continue

                async with state_lock:
                    active += 1

                t0 = time.perf_counter()
                pool = pools.pool_for(msg)
                user_message = build_user_message(msg)
                sr: StreamResult
                try:
                    async with pool.acquire():
                        sr = await stream_one_message(
                            client,
                            base_url,
                            headers,
                            message=user_message,
                            thread_id=msg.thread_id,
                            session_id=msg.session_id,
                            user_id=msg.user_id,
                            timeout=msg.timeout_seconds,
                        )
                except Exception as e:  # noqa: BLE001
                    sr = StreamResult(
                        ok=False,
                        text="",
                        http_status=None,
                        stream_errors=[],
                        http_error=f"{type(e).__name__}: {e}",
                    )

                elapsed = time.perf_counter() - t0
                row: dict[str, Any] = {
                    "story_id": msg.story_id,
                    "target_agent": str(msg.target_agent),
                    "ok": sr.ok,
                    "elapsed_seconds": round(elapsed, 3),
                    "retries": msg.retries,
                    "http_status": sr.http_status,
                    "stream_errors": sr.stream_errors,
                    "http_error": sr.http_error,
                    "response_chars": len(sr.text),
                }
                out_fp.write(json.dumps(row, ensure_ascii=False) + "\n")
                out_fp.flush()
                log(
                    f"[w{worker_id}] {msg.story_id} {msg.target_agent} "
                    f"ok={sr.ok} {elapsed:.1f}s"
                )

                if sr.ok:
                    nxt = next_messages(mode, msg, sr.text)
                    if _is_terminal_success(mode, msg, nxt):
                        await mark_root_done(msg.story_id)
                    for nm in nxt:
                        await q.put((nm.priority.value, next(seq), nm))
                else:
                    if msg.retries < 3:
                        msg.retries += 1
                        delay = backoff_seconds(msg.retries)
                        log(
                            f"[w{worker_id}] retry {msg.story_id} "
                            f"{msg.target_agent} attempt={msg.retries} sleep={delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                        await q.put((msg.priority.value, next(seq), msg))
                    else:
                        reason = sr.http_error or "; ".join(sr.stream_errors) or "unknown"
                        rec = _dlq_record(msg, reason)
                        dlq_rows.append(rec)
                        if dlq_path:
                            with dlq_path.open("a", encoding="utf-8") as df:
                                df.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        await mark_root_done(msg.story_id)

                async with state_lock:
                    active -= 1
                    if (
                        not remaining_roots
                        and q.empty()
                        and active == 0
                    ):
                        done_event.set()

    workers = [asyncio.create_task(worker(i)) for i in range(max(1, num_workers))]
    await done_event.wait()
    for t in workers:
        t.cancel()
    await asyncio.gather(*workers, return_exceptions=True)
    return dlq_rows


def run_dispatch_sync(args: Any) -> int:
    """CLI sync entry: load manifest, open files, asyncio.run."""
    from scripts.batch_journalism_eval.run_batch import load_manifest

    manifest_path = Path(args.manifest)
    stories = load_manifest(manifest_path)
    if args.limit:
        stories = stories[: args.limit]

    base_url = os.environ.get("AGENT_URL", "http://127.0.0.1:5002")
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
    token = os.environ.get("AGENT_X_TOKEN")
    if token:
        headers["X-Token"] = token

    pools = PoolSet(
        max_reporter=args.max_reporter,
        max_fact_checker=args.max_fact_checker,
        max_editor=args.max_editor,
        max_publisher=args.max_publisher,
        max_pipeline_monolith=args.max_pipeline,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    dlq_path = Path(args.dlq) if args.dlq else None
    if dlq_path:
        dlq_path.parent.mkdir(parents=True, exist_ok=True)
        dlq_path.write_text("", encoding="utf-8")

    meta = {
        "dispatch": "story_dispatch",
        "mode": args.mode,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "agent_url": base_url,
        "manifest": str(manifest_path),
        "n_stories": len(stories),
        "workers": args.workers,
    }
    out_path.write_text(json.dumps({"meta": meta}) + "\n", encoding="utf-8")

    mode: DispatchMode = "staged" if args.mode == "staged" else "monolith"

    async def _run() -> None:
        with out_path.open("a", encoding="utf-8") as fp:
            await run_dispatch(
                stories=stories,
                mode=mode,
                base_url=base_url,
                headers=headers,
                pools=pools,
                num_workers=args.workers,
                out_fp=fp,
                dlq_path=dlq_path,
                on_progress=print,
            )

    asyncio.run(_run())
    print(f"Wrote stage log to {out_path}", flush=True)
    if dlq_path:
        print(f"DLQ file: {dlq_path}", flush=True)
    return 0

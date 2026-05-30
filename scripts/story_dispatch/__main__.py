"""python -m scripts.story_dispatch"""

from __future__ import annotations

import argparse
import sys

from .engine import run_dispatch_sync


def main() -> None:
    p = argparse.ArgumentParser(
        description=(
            "Event-driven journalism dispatch: priority queue, per-role pools, "
            "retries with exponential backoff, DLQ (Algorithm 1)."
        )
    )
    p.add_argument("--manifest", type=str, required=True, help="JSON manifest (list or {stories:[]})")
    p.add_argument("--out", type=str, required=True, help="JSONL log (meta line + one row per stage)")
    p.add_argument(
        "--mode",
        choices=("monolith", "staged"),
        default="monolith",
        help=(
            "monolith: one HTTP call per story (orchestrator runs full pipeline). "
            "staged: reporter → fact-checker → editor → optional newsletter as separate "
            "queued messages (uses STORY_DISPATCH_SINGLE_AGENT in system prompt)."
        ),
    )
    p.add_argument("--limit", type=int, default=None, help="Process only first N stories")
    p.add_argument("--workers", type=int, default=2, help="Concurrent dequeue workers")
    p.add_argument(
        "--max-reporter",
        type=int,
        default=2,
        help="Max concurrent reporter-stage HTTP calls (staged mode)",
    )
    p.add_argument("--max-fact-checker", type=int, default=2)
    p.add_argument("--max-editor", type=int, default=2)
    p.add_argument("--max-publisher", type=int, default=1)
    p.add_argument(
        "--max-pipeline",
        type=int,
        default=2,
        help="Max concurrent monolith pipeline HTTP calls",
    )
    p.add_argument(
        "--dlq",
        type=str,
        default=None,
        help="Append dead-letter JSONL path (optional)",
    )
    args = p.parse_args()
    sys.exit(run_dispatch_sync(args))


if __name__ == "__main__":
    main()

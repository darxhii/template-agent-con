"""Tests for batch_journalism_eval/run_batch helpers."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.batch_journalism_eval.run_batch import existing_result_ids


def test_existing_result_ids_skips_meta(tmp_path: Path) -> None:
    p = tmp_path / "out.jsonl"
    p.write_text(
        json.dumps({"meta": {"n_stories": 3}}) + "\n"
        + json.dumps({"id": "a", "fact_check_score": 90}) + "\n"
        + json.dumps({"id": "b"}) + "\n",
        encoding="utf-8",
    )
    assert existing_result_ids(p) == {"a", "b"}


def test_existing_result_ids_missing_file(tmp_path: Path) -> None:
    assert existing_result_ids(tmp_path / "nope.jsonl") == set()

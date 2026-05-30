# Batch journalism evaluation

## What this measures

- **Wall-clock seconds** per story from `POST /v1/stream` start to stream end (candidate for abstract **Y**).
- **Fact-check score** by regex on the full streamed text: last `Score: XX/100` from the fact-checker (candidate for abstract **Z**). Rows with `Score: N/A` or no match are counted separately.

It does **not** measure semantic compression %, RAG hit rate, or queue depth — log those in your Layer 3 / observability stack.

## Prereqs

- Agent API reachable (`AGENT_URL`, default `http://127.0.0.1:5002`).
- MCP + Tavily + model credentials configured so the full pipeline can finish.
- Optional: `AGENT_X_TOKEN` if your agent requires `X-Token`.

## Run 100 stories

```bash
cd agent
uv run python scripts/batch_journalism_eval/run_batch.py run \
  --manifest scripts/batch_journalism_eval/manifest_100.json \
  --out results/eval_100.jsonl
```

Smoke test (2 stories):

```bash
uv run python scripts/batch_journalism_eval/run_batch.py run \
  --manifest scripts/batch_journalism_eval/manifest_100.json \
  --out results/smoke.jsonl \
  --limit 2
```

### Parallel runs + resume

- **`--workers N`:** run **N** stories at once (each opens its own HTTP stream to the agent). Throughput rises only if the agent and upstream APIs can handle concurrent streams; otherwise you may see queuing or 429s—try `2`–`4` first.
- **`--resume`:** read `--out` and **skip** any manifest row whose `id` already appears in the JSONL (ignores the first `meta` line). Does **not** rewrite the file header; **appends** new rows only. Use after a partial run (e.g. finished through `lg-005`).

Continue from an existing `results/eval_100.jsonl`:

```bash
uv run python scripts/batch_journalism_eval/run_batch.py run \
  --manifest scripts/batch_journalism_eval/manifest_100.json \
  --out results/eval_100.jsonl \
  --workers 4 \
  --resume
```

Stories **must** have stable **`id`** fields in the manifest for resume to match.

## Report (Y, Z, tables)

```bash
uv run python scripts/batch_journalism_eval/run_batch.py report \
  --results results/eval_100.jsonl \
  --out results/report_eval_100.md
```

Baseline comparison (same `id` in both files):

```bash
# After running the same manifest against your baseline system:
uv run python scripts/batch_journalism_eval/run_batch.py report \
  --results results/proposed.jsonl \
  --baseline results/baseline_single_agent.jsonl \
  --out results/compare.md
```

## Abstract consistency

- Your abstract cites **10,000** stories; this manifest is **100**. Either update the abstract to match *N*, or run 100×100 shards and aggregate JSONL before `report`.
- **100% completion** in the abstract should match your definition (e.g. HTTP 200 + stream finished); the report uses “no `http_error`”.
- Replace **[Y]** with the report’s **Mean** latency and **[Z]** with **Mean fact-check score** only after scores parse cleanly (minimize `missing` rows).

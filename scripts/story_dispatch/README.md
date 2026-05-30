# Event-driven story dispatch (Algorithm 1)

Python worker that implements a **priority message queue**, **per-role concurrency pools**, **timeouts**, **retries with exponential backoff**, and a **dead-letter queue** against the existing agent `POST /v1/stream` API.

## Modes

| Mode | Behavior |
|------|-----------|
| **`monolith`** (default) | One queued message per story → one HTTP call. The **orchestrator** runs reporter → fact-checker → editor internally. Pool cap: `--max-pipeline`. |
| **`staged`** | Four logical pools (`reporter`, `fact-checker`, `editor`, `newsletter-publisher`). Each stage is a separate HTTP call on the **same** `thread_id` (RAG **Story-ID**). Messages use **`STORY_DISPATCH_SINGLE_AGENT:`** (see `system-prompt.md`) so the main agent performs **exactly one** `task` per request. |

## Run

From `agent/` (agent service must be up; same env as batch eval):

```bash
uv run python -m scripts.story_dispatch \
  --manifest scripts/batch_journalism_eval/manifest_100.json \
  --out results/dispatch_run.jsonl \
  --mode monolith \
  --workers 2 \
  --max-pipeline 2 \
  --dlq results/dispatch_dlq.jsonl
```

Environment:

- `AGENT_URL` — default `http://127.0.0.1:5002`
- `AGENT_X_TOKEN` — optional
- `DISPATCH_USER_ID` — optional `user_id` field (default `story-dispatch-worker`)

## Manifest fields

- **`id`** — unique story key (required for completion tracking).
- **`prompt`** — topic / user instruction.
- **`priority`** — optional: `high` | `normal` | `low` (queue order).
- **`timeout_seconds`** — optional per-story HTTP read timeout (default `900`).
- **`recipient_email`** / **`email`** — if set with `send_newsletter` / `newsletter` intent, **staged** mode enqueues **newsletter-publisher** after editor.

## Output

- **`--out`**: JSONL — first line `{"meta": ...}`, then one JSON object per **stage** (HTTP call) with `story_id`, `target_agent`, `ok`, `elapsed_seconds`, `retries`, errors, `response_chars`.
- **`--dlq`**: append-only JSONL of failed messages after **3** failed attempts (Algorithm 1: increment `retries` while `< 3`, else DLQ).

## Mapping to the paper algorithm

- **`Q.Dequeue`** → `asyncio.PriorityQueue` (FIFO within same priority via monotonic sequence).
- **`P[agent_type]`** → `PoolSet` with asyncio semaphores (`--max-*`).
- **`SpawnInstance` / cap** → fixed max concurrency per pool (no OS process pool).
- **`Process(m) with timeout`** → `httpx` stream read timeout per message.
- **`CreateNextStageMessage`** → `next_messages()` in `pipeline.py` (**staged** only).
- **Retries / backoff** → `http_client.backoff_seconds` before re-queue.
- **`Dead-Letter-Queue`** → optional `--dlq` file.

## Limitations

- **Not** Redis/Kafka — in-process queue only; single Python process.
- **Staged** mode depends on the model obeying **`STORY_DISPATCH_SINGLE_AGENT`**; if it chains extra subagents, behavior diverges from strict one-stage semantics.
- Large handoffs (full reporter output in fact-checker) can be **token-heavy**; trim in manifest or use **monolith** for long articles.

# Template Agent

[![Python 3.12+](https://img.shields.io/badge/python-3.12,3.13-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/redhat-data-and-ai/template-agent/actions/workflows/test.yml/badge.svg)](https://github.com/redhat-data-and-ai/template-mcp-server/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A template for building AI agents with SSE streaming, conversation management, and Langfuse tracing.

## Quick Start

**Prerequisites:** Python 3.12+, PostgreSQL, Google AI API credentials

```bash
git clone https://github.com/redhat-data-and-ai/template-agent.git
cd template-agent
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env          # edit with your config
uv run python -m template_agent.src.main
```

The [template-mcp-server](https://github.com/redhat-data-and-ai/template-mcp-server) must be running before starting the agent.

## API

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/v1/stream` | POST | Stream chat (SSE) |
| `/v1/history/{thread_id}` | GET | Conversation history |
| `/v1/threads/{user_id}` | GET | List user threads |
| `/v1/feedback` | POST | Record feedback |

```bash
curl -X POST http://localhost:8081/v1/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "thread_id": "t1", "user_id": "u1", "stream_tokens": true}'
```

Client examples (Streamlit, Python async) are in [`examples/`](./examples/).

## Configuration

| Variable | Default | Required |
|---|---|---|
| `AGENT_HOST` | `0.0.0.0` | No |
| `AGENT_PORT` | `5002` | No |
| `PYTHON_LOG_LEVEL` | `INFO` | No |
| `POSTGRES_USER` | `pgvector` | Yes |
| `POSTGRES_PASSWORD` | `pgvector` | Yes |
| `POSTGRES_DB` | `pgvector` | Yes |
| `POSTGRES_HOST` | `pgvector` | Yes |
| `POSTGRES_PORT` | `5432` | Yes |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | — | Yes |
| `LANGFUSE_PUBLIC_KEY` | — | No |
| `LANGFUSE_SECRET_KEY` | — | No |
| `LANGFUSE_BASE_URL` | — | No |
| `AGENT_SSL_KEYFILE` | — | No |
| `AGENT_SSL_CERTFILE` | — | No |

## Project Structure

```
template_agent/
├── src/
│   ├── core/
│   │   ├── agent.py          # Agent initialisation + subagent loading
│   │   ├── manager.py        # AgentManager, SSE streaming
│   │   ├── prompt.py         # System prompt loader
│   │   └── backend.py        # Shell backend (isolated venv)
│   ├── routes/
│   │   ├── stream.py         # POST /v1/stream
│   │   ├── history.py        # GET  /v1/history
│   │   ├── threads.py        # GET  /v1/threads
│   │   ├── health.py         # GET  /health
│   │   └── feedback.py       # POST /v1/feedback
│   ├── api.py                # FastAPI app + lifespan
│   ├── main.py               # Uvicorn entry point
│   ├── schema.py             # Pydantic models
│   └── settings.py           # Env config
├── agent_config/
│   ├── system-prompt.md      # Orchestrator prompt
│   ├── agents/               # Subagent definitions (YAML + MD)
│   └── skills/               # Skill documents per agent
└── tests/
```

## Testing & Quality

```bash
pytest                                           # all tests
pytest --cov=template_agent.src --cov-report=html  # with coverage
ruff check . && ruff format .                    # lint + format
pre-commit run --all-files                       # all hooks
```

## Deployment

```bash
podman-compose up -d --build
```

For production: configure SSL certs (`AGENT_SSL_KEYFILE`, `AGENT_SSL_CERTFILE`), use managed PostgreSQL, and enable Langfuse tracing.

## Links

- [Issues](https://github.com/redhat-data-and-ai/template-agent/issues)
- [template-mcp-server](https://github.com/redhat-data-and-ai/template-mcp-server)

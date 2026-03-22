# Wellness Bot Quick Start Guide

This guide helps you get the Red Hat Wellness Bot running with deep agents, MCP tools, skills, and subagents.

## Prerequisites

- Python 3.12.2
- MCP server running at `http://0.0.0.0:5001/mcp`
- Google Cloud credentials OR OpenAI API key

## Setup Steps

### 1. Install Dependencies

```bash
cd /path/to/template-agent
uv pip install -e ".[dev]"
```

This installs:
- `deepagents>=0.3.5`
- `langchain`, `langgraph`, `langchain-mcp-adapters`
- All existing template-agent dependencies

### 2. Start MCP Server

In a separate terminal, start your MCP server:

```bash
cd /path/to/template-mcp-server
python -m template_mcp_server.src.main
```

Verify it's running at `http://0.0.0.0:5001/mcp` and exposes these 4 tools:
- `bmi_tool`
- `multiply_tool`
- `web_search_tool`
- `email_tool`

### 3. Configure Environment

Create or update `.env` file:

```bash
# Option 1: Google AI (recommended)
GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/google-credentials.json"

# Option 2: OpenAI
OPENAI_API_KEY="sk-..."

# MCP Server (already configured in settings.py)
MCP_SERVER_URL="http://0.0.0.0:5001/mcp"
MCP_SERVER_NAME="template-mcp-server"
MCP_TRANSPORT_PROTOCOL="streamable_http"

# Optional: Use in-memory storage for testing
USE_INMEMORY_SAVER=true
```

### 4. Run the Demo

```bash
python demo.py
```

Expected output:

```
================================================================================
Red Hat Wellness Bot Demo (Deep Agents + MCP Tools)
================================================================================

✓ Deep agent initialized with MCP tools, skills, and subagents

================================================================================
SCENARIO 1: Full Wellness Analysis
================================================================================

👤 User: I'm 178cm and 82kg, email is tuhin@redhat.com

🤖 Bot: [Agent calculates BMI, water, calories, and emails report]

================================================================================
SCENARIO 2: Memory Recall
================================================================================

👤 User: What was my BMI again?

🤖 Bot: Your BMI is 25.9 (Overweight category).

================================================================================
SCENARIO 3: Update Weight (Memory Recall)
================================================================================

👤 User: I'm now 79kg

🤖 Bot: Great progress! You went from 25.9 to 24.9 — normal range now!
```

## How It Works

### Files Structure

```
template-agent/
├── AGENTS.md                    # Memory: Agent identity & routing rules
├── subagents.yaml               # Subagent definitions
├── skills/
│   └── wellness-report/
│       └── SKILL.md            # Report formatting skill
├── demo.py                      # Demo script
└── template_agent/
    └── src/
        └── core/
            └── agent.py         # Deep agent implementation
```

### Deep Agent Flow

1. **User Input** → Deep Agent (supervisor)
2. **Supervisor** (using AGENTS.md) → Routes to **Wellness Analyst** subagent
3. **Wellness Analyst** (using MCP tools):
   - Calls `bmi_tool(height_cm, weight_kg)` → BMI
   - Calls `multiply_tool(weight, 0.033)` → Water intake
   - Calls `multiply_tool(weight, 24)` → Calories
   - Calls `web_search_tool("health tips BMI category")` → Tips
4. **Wellness Analyst** → Returns analysis to **Supervisor**
5. **Supervisor** → Routes to **Report Dispatcher** subagent
6. **Report Dispatcher** (using wellness-report skill + MCP email tool):
   - Formats report using `skills/wellness-report/SKILL.md`
   - Calls `email_tool(recipient, subject, body)` → Sends email
7. **Report Dispatcher** → Returns to **Supervisor**
8. **Supervisor** → Final response to user

### Memory Persistence

The agent uses `AGENTS.md` as memory and a checkpointer (MemorySaver or PostgreSQL) to remember:
- User's height
- User's weight
- Last calculated BMI

On subsequent turns, the agent recalls this information without calling tools.

## Troubleshooting

### Error: "Failed to connect to MCP server"

**Solution**: Make sure MCP server is running:
```bash
cd /path/to/template-mcp-server
python -m template_mcp_server.src.main
```

### Error: "ModuleNotFoundError: No module named 'deepagents'"

**Solution**: Install dependencies:
```bash
uv pip install -e ".[dev]"
```

### Error: "No module named 'google.generativeai'"

**Solution**: Either:
1. Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable
2. OR switch to OpenAI by setting `OPENAI_API_KEY` and updating model in `agent.py`

### Error: "Subagents file not found"

**Solution**: Make sure `subagents.yaml` exists at repo root:
```bash
ls -la subagents.yaml
```

### Error: "Skills directory not found"

**Solution**: Make sure `skills/wellness-report/SKILL.md` exists:
```bash
ls -la skills/wellness-report/SKILL.md
```

## Using with Existing API

The wellness bot integrates seamlessly with the existing template-agent API:

```bash
# Start the API server
python -m template_agent.src.main
```

Then call the `/v1/stream` endpoint:

```bash
curl -X POST "http://localhost:8081/v1/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I am 178cm and 82kg, email is tuhin@redhat.com",
    "thread_id": "user-123",
    "stream_tokens": true
  }'
```

The deep agent will:
1. Route to Wellness Analyst
2. Calculate metrics using MCP tools
3. Route to Report Dispatcher
4. Format and email the report
5. Stream the response back

## Next Steps

- Customize `AGENTS.md` for different use cases
- Add more subagents to `subagents.yaml`
- Create additional skills in `skills/` directory
- Extend MCP server with more tools

## References

- [Deep Agents Examples](https://github.com/langchain-ai/deepagents/tree/main/examples)
- [WELLNESS_BOT.md](./WELLNESS_BOT.md) - Full architecture documentation
- [Template MCP Server](https://github.com/redhat-data-and-ai/template-mcp-server)

## Support

For issues:
- [GitHub Issues](https://github.com/redhat-data-and-ai/template-agent/issues)

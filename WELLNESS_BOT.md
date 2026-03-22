# Red Hat Wellness Bot - Deep Agents Implementation

This document describes the wellness bot built using **deepagents** (>=0.3.5) with MCP tools, skills, subagents, and memory.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│            Deep Agent (create_deep_agent)                    │
│  - Memory: AGENTS.md                                         │
│  - Skills: skills/wellness-report/                           │
│  - Backend: FilesystemBackend                                │
│  - Checkpointer: MemorySaver or PostgreSQL                   │
└──────────────┬──────────────────────────────────────────────┘
               │
               ├──► Wellness Analyst Subagent
               │    - Tools: bmi_tool, multiply_tool, web_search_tool (MCP)
               │    - Calculates BMI, water, calories, health tips
               │
               └──► Report Dispatcher Subagent
                    - Tools: email_tool (MCP)
                    - Formats & emails wellness reports using skills
```

## Files Added/Modified

### New Files

1. **`AGENTS.md`** (repo root)
   - Defines agent identity, routing rules, and memory instructions
   - Loaded as memory by `create_deep_agent()`

2. **`subagents.yaml`** (repo root)
   - Defines two subagents: `wellness_analyst` and `report_dispatcher`
   - Loaded by `load_subagents()` from deepagents library

3. **`skills/wellness-report/SKILL.md`**
   - Skill for formatting wellness reports
   - YAML frontmatter + markdown body (Agent Skills standard)
   - Guides Report Dispatcher on report structure

4. **`demo.py`** (repo root)
   - Demo script showing 3 scenarios:
     - Turn 1: Full wellness analysis with email
     - Turn 2: Memory recall (no tool calls)
     - Turn 3: Update weight with memory

### Modified Files

1. **`template_agent/src/core/agent.py`**
   - Replaced `create_react_agent()` with `create_deep_agent()`
   - Added memory (AGENTS.md), skills, subagents loading
   - Added FilesystemBackend
   - Preserved all MCP connection logic, error handling, checkpointing

2. **`pyproject.toml`**
   - Added `deepagents>=0.3.5` to dependencies

## Deep Agents Pattern

The implementation uses `create_deep_agent()` from the deepagents library:

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from deepagents.subagents import load_subagents

agent = create_deep_agent(
    model=model,
    memory=[str(REPO_ROOT / "AGENTS.md")],
    skills=[str(REPO_ROOT / "skills/")],
    tools=mcp_tools,
    subagents=load_subagents(REPO_ROOT / "subagents.yaml"),
    backend=FilesystemBackend(root_dir=str(REPO_ROOT)),
    checkpointer=checkpoint,
)
```

## MCP Tools Integration

All tools are served via MCP server at `http://0.0.0.0:5001/mcp`:

- **bmi_tool** - Calculate BMI from height and weight
- **multiply_tool** - Multiply numbers (for water/calorie calculations)
- **web_search_tool** - Search web for health tips
- **email_tool** - Send emails

No local tool implementations - all tools from MCP server via `langchain-mcp-adapters`.

## Subagents (from subagents.yaml)

### 1. Wellness Analyst

- **Tools**: bmi_tool, multiply_tool, web_search_tool
- **Responsibilities**:
  - Calculate BMI
  - Calculate water intake (weight × 0.033 liters)
  - Calculate base calories (weight × 24 calories)
  - Search for 3 health tips matching BMI category

### 2. Report Dispatcher

- **Tools**: email_tool
- **Responsibilities**:
  - Format wellness analysis using wellness-report skill
  - Send formatted report via email
  - No confirmation - sends directly

## Skills (Agent Skills Standard)

**wellness-report** (`skills/wellness-report/SKILL.md`):

```yaml
---
name: wellness-report
description: Formats BMI results, health tips, and hydration/calorie targets
---

# Wellness Report Formatting

## BMI Categories
- Under 18.5: Underweight
- 18.5–24.9: Normal
- 25–29.9: Overweight
- 30+: Obese

## Report Structure
1. BMI Result: Value + category + interpretation
2. Daily Targets: Water + calories
3. Health Tips: 3 actionable tips
4. Disclaimer: "This is not medical advice..."
```

## Memory (AGENTS.md)

The agent uses `AGENTS.md` as memory to:

- Define identity: "Friendly wellness assistant for Red Hat employees"
- Routing rules: Health metrics → Wellness Analyst → Report Dispatcher
- Memory persistence: Remember height, weight, BMI across sessions

## Running the Demo

### Prerequisites

1. **MCP Server Running**:
   ```bash
   # In template-mcp-server directory
   python -m template_mcp_server.src.main
   ```
   Server should be at `http://0.0.0.0:5001/mcp`

2. **Install Dependencies**:
   ```bash
   uv pip install -e ".[dev]"
   ```

3. **Set Environment Variables**:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
   # OR
   export OPENAI_API_KEY="sk-..."
   ```

### Run Demo

```bash
python demo.py
```

### Expected Output

```
================================================================================
Red Hat Wellness Bot Demo (Deep Agents + MCP Tools)
================================================================================

================================================================================
SCENARIO 1: Full Wellness Analysis
================================================================================

👤 User: I'm 178cm and 82kg, email is tuhin@redhat.com

🤖 Bot: I've calculated your wellness metrics and sent a report to tuhin@redhat.com!

📊 Expected: Wellness Analyst → calculates BMI (25.9), water (2.7L), calories (1968)
🔍 Expected: Wellness Analyst → searches for health tips for overweight BMI
📧 Expected: Report Dispatcher → formats and emails report to tuhin@redhat.com

================================================================================
SCENARIO 2: Memory Recall
================================================================================

👤 User: What was my BMI again?

🤖 Bot: Your BMI is 25.9 (Overweight category).

💭 Expected: Bot recalls BMI (25.9) from memory without calling MCP tools

================================================================================
SCENARIO 3: Update Weight (Memory Recall)
================================================================================

👤 User: I'm now 79kg

🤖 Bot: Great progress! You went from 25.9 to 24.9 — you're in the normal range now!

💭 Expected: Remembers height (178cm) from memory
🧮 Expected: Calculates new BMI using bmi_tool(178, 79) → 24.9
📈 Expected: 'You went from 25.9 to 24.9 — you're in the normal range now!'
```

## Key Differences from Previous Implementation

### Before (Raw LangGraph)

- Manual StateGraph construction
- Subagents defined in Python code
- No skills system
- Manual prompt management

### After (Deep Agents)

- `create_deep_agent()` - high-level abstraction
- `load_subagents()` from YAML file
- Skills system with SKILL.md files
- Memory from AGENTS.md
- FilesystemBackend for storage

## Integration with Existing Template Agent

The wellness bot **replaces** the existing simple agent in `template_agent/src/core/agent.py` while preserving:

✅ MCP connection logic with timeout handling
✅ SSO token authentication support
✅ PostgreSQL and in-memory checkpointing
✅ Error handling and logging
✅ Settings configuration
✅ Database initialization

The existing API routes in `template_agent/src/routes/` continue to work with the new deep agent through the `get_template_agent()` function.

## References

- [Deep Agents Examples](https://github.com/langchain-ai/deepagents/tree/main/examples)
- [Agent Skills Documentation](https://docs.langchain.com/oss/python/deepagents/skills)
- [MCP Adapters](https://python.langchain.com/docs/integrations/tools/mcp/)
- [Template MCP Server](https://github.com/redhat-data-and-ai/template-mcp-server)

## License

Apache 2.0 - Built by Red Hat Data & AI team

"""System prompts and prompt utilities for the template agent.

This module provides the base behavioral prompt for the agent.
Domain-specific identity, routing, and memory live in AGENTS.md
(loaded separately as memory context).
"""

from datetime import datetime


def get_current_date() -> str:
    """Get the current date in a formatted string.

    Returns:
        The current date formatted as "Month Day, Year" (e.g., "December 25, 2024").
    """
    return datetime.now().strftime("%B %d, %Y")


def get_system_prompt() -> str:
    """Get the base system prompt for the agent.

    Covers general behavior, tool usage, and output formatting.
    Does NOT include identity or routing — those come from AGENTS.md.

    Returns:
        The base system prompt string.
    """
    current_date = get_current_date()

    return (
        f"Today's date is {current_date}.\n\n"
        "## General Behavior\n"
        "- Always respond in the same language as the user.\n"
        "- Ensure all string values in function call arguments are properly JSON-escaped.\n"
        "- Only use the tools you are given. Do not answer from internal knowledge when a tool can provide the answer.\n"
        "- Every final answer must be grounded in tool observations.\n\n"
        "## Delegation (CRITICAL)\n"
        "- You are an orchestrator. When a user request matches a subagent's domain, "
        "immediately call the `task` tool to delegate. Do NOT describe what you plan to do "
        "— just do it.\n"
        "- WRONG: 'I'll start the wellness analysis for you...'\n"
        "- RIGHT: Call the `task` tool with `subagent_type: wellness_analyst`.\n"
        "- You may send a brief message AFTER the subagent returns, summarizing the results.\n\n"
        "## Output Format\n"
        "- Always respond using proper Markdown formatting.\n"
        "- Use headers, lists, code blocks, bold, and tables when they improve readability.\n"
        "- Keep intermediate responses concise; make the final response well-structured.\n"
    )

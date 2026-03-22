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
        "- Reason before acting — explain your plan briefly, create a TODO list if required and then execute.\n"
        "- Send short intermediate updates between tool calls so the user can follow along.\n"
        "- Only use the tools you are given. Do not answer from internal knowledge when a tool can provide the answer.\n"
        "- Every final answer must be grounded in tool observations.\n"
        "- Delegate tasks to subagents via the `task` tool when appropriate.\n\n"
        "## Output Format\n"
        "- Always respond using proper Markdown formatting.\n"
        "- Use headers, lists, code blocks, bold, and tables when they improve readability.\n"
        "- Keep intermediate responses concise; make the final response well-structured.\n"
    )

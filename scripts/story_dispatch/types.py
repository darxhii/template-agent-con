"""Types for event-driven story dispatch (Algorithm 1 mapping)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from typing import Any


class AgentType(StrEnum):
    """Maps to pools PReporter, PFact-Checker, PEditor, PPublisher (+ monolith)."""

    REPORTER = "reporter"
    FACT_CHECKER = "fact-checker"
    EDITOR = "editor"
    NEWSLETTER_PUBLISHER = "newsletter-publisher"
    # One HTTP call; orchestrator runs full verified pipeline internally.
    PIPELINE_MONOLITH = "pipeline-monolith"


class Priority(IntEnum):
    """Queue ordering: lower value = dequeued first (high priority)."""

    HIGH = 0
    NORMAL = 1
    LOW = 2


@dataclass
class StoryMessage:
    """Work item dequeued by the dispatch engine."""

    story_id: str
    thread_id: str
    target_agent: AgentType
    priority: Priority
    user_id: str
    session_id: str
    # User-facing topic / original prompt
    topic: str
    retries: int = 0
    # Carried outputs for staged handoffs (same thread_id / Story-ID for RAG).
    reporter_output: str = ""
    fact_check_output: str = ""
    editor_output: str = ""
    recipient_email: str | None = None
    send_newsletter: bool = False
    timeout_seconds: float = 900.0
    extra: dict[str, Any] = field(default_factory=dict)

    def pool_key(self) -> str:
        if self.target_agent == AgentType.PIPELINE_MONOLITH:
            return "pipeline_monolith"
        return str(self.target_agent)

"""Stage transitions (CreateNextStageMessage) and dispatch body builders."""

from __future__ import annotations

import json
from typing import Literal

from .types import AgentType, Priority, StoryMessage

DispatchMode = Literal["staged", "monolith"]


def build_user_message(msg: StoryMessage) -> str:
    """HTTP `message` field: strict single-agent JSON or full user prompt."""
    if msg.target_agent == AgentType.PIPELINE_MONOLITH:
        sid = msg.thread_id
        body = (
            f"Story-ID: {sid}\n\n"
            f"{msg.topic}\n\n"
            "Run the default verified topic pipeline (reporter → fact-checker → "
            "editor) per system routing. Create TODO first, then delegate in order."
        )
        return body

    desc = _handoff_description(msg)
    payload = {"subagent_type": str(msg.target_agent), "description": desc}
    return "STORY_DISPATCH_SINGLE_AGENT:\n" + json.dumps(payload, ensure_ascii=False)


def _handoff_description(msg: StoryMessage) -> str:
    sid = msg.thread_id
    if msg.target_agent == AgentType.REPORTER:
        return (
            f"Story-ID: {sid}\n\n"
            f"{msg.topic}\n\n"
            "Produce the reporter briefing and RAG ingest per the research skill. "
            "This is stage 1/3 of an external queue; do not fact-check or edit here."
        )
    if msg.target_agent == AgentType.FACT_CHECKER:
        return (
            f"Story-ID: {sid}\n\n"
            "Original topic:\n"
            f"{msg.topic}\n\n"
            "Draft from reporter (verify this):\n\n"
            f"{msg.reporter_output}\n"
        )
    if msg.target_agent == AgentType.EDITOR:
        return (
            f"Story-ID: {sid}\n\n"
            "Original topic:\n"
            f"{msg.topic}\n\n"
            "Reporter draft:\n\n"
            f"{msg.reporter_output}\n\n"
            "Fact-check audit (apply recommended edits):\n\n"
            f"{msg.fact_check_output}\n"
        )
    if msg.target_agent == AgentType.NEWSLETTER_PUBLISHER:
        rec = msg.recipient_email or ""
        return (
            f"Story-ID: {sid}\n\n"
            f"Recipient email: {rec}\n\n"
            "Send the newsletter using the following final article (editor output):\n\n"
            f"{msg.editor_output}\n"
        )
    raise ValueError(f"Unsupported target_agent for handoff: {msg.target_agent}")


def next_messages(
    mode: DispatchMode,
    completed: StoryMessage,
    response_text: str,
) -> list[StoryMessage]:
    """Algorithm 1 line 11: enqueue follow-up stage messages after success."""
    if mode == "monolith":
        return []

    nxt: list[StoryMessage] = []
    if completed.target_agent == AgentType.REPORTER:
        nxt.append(
            StoryMessage(
                story_id=completed.story_id,
                thread_id=completed.thread_id,
                target_agent=AgentType.FACT_CHECKER,
                priority=completed.priority,
                user_id=completed.user_id,
                session_id=completed.session_id,
                topic=completed.topic,
                timeout_seconds=completed.timeout_seconds,
                reporter_output=response_text,
                recipient_email=completed.recipient_email,
                send_newsletter=completed.send_newsletter,
                extra=dict(completed.extra),
            )
        )
    elif completed.target_agent == AgentType.FACT_CHECKER:
        nxt.append(
            StoryMessage(
                story_id=completed.story_id,
                thread_id=completed.thread_id,
                target_agent=AgentType.EDITOR,
                priority=completed.priority,
                user_id=completed.user_id,
                session_id=completed.session_id,
                topic=completed.topic,
                timeout_seconds=completed.timeout_seconds,
                reporter_output=completed.reporter_output,
                fact_check_output=response_text,
                recipient_email=completed.recipient_email,
                send_newsletter=completed.send_newsletter,
                extra=dict(completed.extra),
            )
        )
    elif completed.target_agent == AgentType.EDITOR:
        if completed.send_newsletter and completed.recipient_email:
            nxt.append(
                StoryMessage(
                    story_id=completed.story_id,
                    thread_id=completed.thread_id,
                    target_agent=AgentType.NEWSLETTER_PUBLISHER,
                    priority=completed.priority,
                    user_id=completed.user_id,
                    session_id=completed.session_id,
                    topic=completed.topic,
                    timeout_seconds=completed.timeout_seconds,
                    reporter_output=completed.reporter_output,
                    fact_check_output=completed.fact_check_output,
                    editor_output=response_text,
                    recipient_email=completed.recipient_email,
                    send_newsletter=True,
                    extra=dict(completed.extra),
                )
            )
    return nxt


def initial_message_for_story(
    story: dict,
    *,
    mode: DispatchMode,
    thread_id: str,
    user_id: str,
    timeout_seconds: float,
) -> StoryMessage:
    """Build the first queued message from a manifest row."""
    story_id = str(story.get("id", thread_id))
    topic = str(story.get("prompt", ""))
    recipient = story.get("recipient_email") or story.get("email")
    send_nl = bool(story.get("send_newsletter") or story.get("newsletter") or recipient)
    priority = priority_from_manifest(story)

    target = (
        AgentType.PIPELINE_MONOLITH
        if mode == "monolith"
        else AgentType.REPORTER
    )
    return StoryMessage(
        story_id=story_id,
        thread_id=thread_id,
        target_agent=target,
        priority=priority,
        user_id=user_id,
        session_id=thread_id,
        topic=topic,
        timeout_seconds=timeout_seconds,
        recipient_email=str(recipient) if recipient else None,
        send_newsletter=bool(send_nl and recipient),
        extra={"category": story.get("category", "")},
    )


def priority_from_manifest(story: dict, default: Priority = Priority.NORMAL) -> Priority:
    raw = story.get("priority", "normal")
    if isinstance(raw, int):
        return Priority.HIGH if raw <= 0 else Priority.LOW if raw >= 2 else Priority.NORMAL
    s = str(raw).lower()
    if s == "high":
        return Priority.HIGH
    if s == "low":
        return Priority.LOW
    return default

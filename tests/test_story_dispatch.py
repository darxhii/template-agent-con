"""Unit tests for story_dispatch (no live agent)."""

from __future__ import annotations

import json

import pytest

from scripts.story_dispatch.http_client import backoff_seconds
from scripts.story_dispatch.pipeline import (
    build_user_message,
    initial_message_for_story,
    next_messages,
    priority_from_manifest,
)
from scripts.story_dispatch.types import AgentType, Priority, StoryMessage


def test_backoff_seconds_monotonic_cap() -> None:
    assert backoff_seconds(1) == 2.0
    assert backoff_seconds(2) == 4.0
    assert backoff_seconds(10) == 120.0


def test_priority_from_manifest() -> None:
    assert priority_from_manifest({"priority": "high"}) == Priority.HIGH
    assert priority_from_manifest({"priority": "low"}) == Priority.LOW
    assert priority_from_manifest({}) == Priority.NORMAL


def test_build_user_message_monolith() -> None:
    m = StoryMessage(
        story_id="s1",
        thread_id="tid",
        target_agent=AgentType.PIPELINE_MONOLITH,
        priority=Priority.NORMAL,
        user_id="u",
        session_id="tid",
        topic="Hello topic",
    )
    text = build_user_message(m)
    assert "Story-ID: tid" in text
    assert "Hello topic" in text
    assert "STORY_DISPATCH_SINGLE_AGENT" not in text


def test_build_user_message_staged_reporter() -> None:
    m = StoryMessage(
        story_id="s1",
        thread_id="tid",
        target_agent=AgentType.REPORTER,
        priority=Priority.NORMAL,
        user_id="u",
        session_id="tid",
        topic="Topic",
    )
    text = build_user_message(m)
    assert text.startswith("STORY_DISPATCH_SINGLE_AGENT:\n")
    payload = json.loads(text.split("\n", 1)[1])
    assert payload["subagent_type"] == "reporter"
    assert "Story-ID: tid" in payload["description"]


def test_next_messages_staged_chain() -> None:
    base = StoryMessage(
        story_id="s1",
        thread_id="tid",
        target_agent=AgentType.REPORTER,
        priority=Priority.HIGH,
        user_id="u",
        session_id="tid",
        topic="T",
        reporter_output="",
    )
    n1 = next_messages("staged", base, "reporter out")
    assert len(n1) == 1
    assert n1[0].target_agent == AgentType.FACT_CHECKER
    assert n1[0].reporter_output == "reporter out"

    n2 = next_messages("staged", n1[0], "fc out")
    assert n2[0].target_agent == AgentType.EDITOR
    assert n2[0].fact_check_output == "fc out"

    n3 = next_messages("staged", n2[0], "ed out")
    assert n3 == []


def test_next_messages_editor_then_newsletter() -> None:
    ed = StoryMessage(
        story_id="s1",
        thread_id="tid",
        target_agent=AgentType.EDITOR,
        priority=Priority.NORMAL,
        user_id="u",
        session_id="tid",
        topic="T",
        reporter_output="r",
        fact_check_output="f",
        recipient_email="a@b.com",
        send_newsletter=True,
    )
    n = next_messages("staged", ed, "article")
    assert len(n) == 1
    assert n[0].target_agent == AgentType.NEWSLETTER_PUBLISHER
    assert n[0].editor_output == "article"


def test_initial_message_for_story() -> None:
    row = {"id": "x1", "prompt": "Do something", "priority": "high"}
    m = initial_message_for_story(
        row,
        mode="staged",
        thread_id="thr",
        user_id="u",
        timeout_seconds=60.0,
    )
    assert m.story_id == "x1"
    assert m.target_agent == AgentType.REPORTER
    assert m.priority == Priority.HIGH

    m2 = initial_message_for_story(
        row,
        mode="monolith",
        thread_id="thr2",
        user_id="u",
        timeout_seconds=60.0,
    )
    assert m2.target_agent == AgentType.PIPELINE_MONOLITH


@pytest.mark.asyncio
async def test_priority_queue_ordering() -> None:
    import asyncio

    q: asyncio.PriorityQueue[tuple[int, int, StoryMessage]] = asyncio.PriorityQueue()
    seq = iter(range(100))

    def put(p: Priority, sid: str) -> None:
        m = StoryMessage(
            story_id=sid,
            thread_id=sid,
            target_agent=AgentType.REPORTER,
            priority=p,
            user_id="u",
            session_id=sid,
            topic="t",
        )
        q.put_nowait((m.priority.value, next(seq), m))

    put(Priority.LOW, "low")
    put(Priority.HIGH, "high")
    put(Priority.NORMAL, "mid")
    _, _, a = await q.get()
    _, _, b = await q.get()
    _, _, c = await q.get()
    assert a.story_id == "high"
    assert b.story_id == "mid"
    assert c.story_id == "low"

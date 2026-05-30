"""HTTP/SSE client for POST /v1/stream."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class StreamResult:
    ok: bool
    text: str
    http_status: int | None
    stream_errors: list[str]
    http_error: str | None


def accumulate_stream(response: httpx.Response) -> StreamResult:
    """Parse agent SSE (same shape as batch_journalism_eval/run_batch.py)."""
    parts: list[str] = []
    stream_errors: list[str] = []
    buffer = ""
    for chunk in response.iter_bytes():
        buffer += chunk.decode("utf-8", errors="replace")
        blocks = buffer.split("\n\n")
        buffer = blocks.pop() if blocks else ""
        for block in blocks:
            line = block.strip()
            if not line or line in ("[DONE]", "DONE", "data: [DONE]"):
                continue
            if line.startswith("data: "):
                line = line[6:].strip()
            try:
                obj: dict[str, Any] = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = obj.get("type")
            c = obj.get("content")
            if t == "token" and isinstance(c, str):
                parts.append(c)
            elif t == "message":
                if isinstance(c, dict):
                    inner = c.get("content")
                    if isinstance(inner, str):
                        parts.append(inner)
                elif isinstance(c, str):
                    parts.append(c)
            elif t == "error":
                stream_errors.append(json.dumps(c, ensure_ascii=False))
    text = "".join(parts)
    ok = response.status_code == 200 and not stream_errors
    return StreamResult(
        ok=ok,
        text=text,
        http_status=response.status_code,
        stream_errors=stream_errors,
        http_error=None,
    )


async def stream_one_message(
    client: httpx.AsyncClient,
    base_url: str,
    headers: dict[str, str],
    *,
    message: str,
    thread_id: str,
    session_id: str,
    user_id: str,
    timeout: float,
) -> StreamResult:
    body = {
        "message": message,
        "thread_id": thread_id,
        "session_id": session_id,
        "user_id": user_id,
        "stream_tokens": True,
    }
    try:
        async with client.stream(
            "POST",
            f"{base_url.rstrip('/')}/v1/stream",
            json=body,
            headers=headers,
            timeout=httpx.Timeout(connect=30.0, read=timeout, write=30.0, pool=30.0),
        ) as resp:
            content = await resp.aread()
            raw = httpx.Response(resp.status_code, headers=resp.headers, content=content)
            out = accumulate_stream(raw)
            if resp.status_code != 200:
                out.ok = False
                out.http_error = f"HTTP {resp.status_code}"
            return out
    except Exception as e:  # noqa: BLE001
        return StreamResult(
            ok=False,
            text="",
            http_status=None,
            stream_errors=[],
            http_error=f"{type(e).__name__}: {e}",
        )


def backoff_seconds(after_retry_count: int) -> float:
    """Exponential backoff before re-queue (capped). after_retry_count >= 1."""
    return min(120.0, float(2**min(after_retry_count, 10)))

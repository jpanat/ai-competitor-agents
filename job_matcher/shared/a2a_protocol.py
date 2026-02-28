"""
A2A (Agent-to-Agent) Protocol Implementation.

Based on Google's A2A open protocol spec:
  https://google.github.io/A2A/

Each agent:
  1. Serves  GET  /.well-known/agent.json   → AgentCard
  2. Serves  POST /tasks/send               → submit a task
  3. Serves  GET  /tasks/{id}               → poll task status
  4. Serves  GET  /tasks/{id}/stream        → SSE streaming (optional)

This module provides:
  - A2ARouter   : FastAPI APIRouter with the standard endpoints
  - A2AClient   : async HTTP client for calling other agents
  - run_a2a_server : convenience wrapper to start a uvicorn server
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Optional

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from .models import (
    A2AMessage,
    A2ATask,
    AgentCard,
    Artifact,
    TaskState,
    TaskStatus,
)

logger = logging.getLogger(__name__)


# ─── In-process task store (swap for Redis in production) ────────────────────

_task_store: dict[str, A2ATask] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── A2A Router Factory ───────────────────────────────────────────────────────

def make_a2a_router(
    agent_card: AgentCard,
    handler: Callable[[A2ATask], Coroutine[Any, Any, A2ATask]],
) -> APIRouter:
    """
    Build a FastAPI APIRouter that implements the A2A protocol endpoints.

    Parameters
    ----------
    agent_card : AgentCard
        Metadata about this agent (name, skills, URL, …)
    handler : async callable
        Receives an A2ATask whose status is WORKING and must return the
        updated task (status COMPLETED or FAILED) with populated artifacts.
    """
    router = APIRouter()

    @router.get("/.well-known/agent.json", response_model=AgentCard, tags=["A2A"])
    async def get_agent_card() -> AgentCard:
        """Agent discovery endpoint (A2A spec §3.1)."""
        return agent_card

    @router.post("/tasks/send", response_model=A2ATask, tags=["A2A"])
    async def send_task(message: A2AMessage) -> A2ATask:
        """Submit a new task to this agent (A2A spec §3.2)."""
        task = A2ATask(
            id=str(uuid.uuid4()),
            message=message,
            status=TaskStatus(state=TaskState.SUBMITTED, timestamp=_now()),
        )
        _task_store[task.id] = task

        # Mark as working
        task.status = TaskStatus(state=TaskState.WORKING, timestamp=_now())
        _task_store[task.id] = task

        # Run handler in background so the POST returns immediately
        asyncio.create_task(_run_handler(task, handler))

        return task

    @router.get("/tasks/{task_id}", response_model=A2ATask, tags=["A2A"])
    async def get_task(task_id: str) -> A2ATask:
        """Poll task status (A2A spec §3.3)."""
        task = _task_store.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return task

    @router.get("/tasks/{task_id}/stream", tags=["A2A"])
    async def stream_task(task_id: str) -> StreamingResponse:
        """SSE stream of task updates (A2A spec §3.4)."""

        async def event_gen():
            while True:
                task = _task_store.get(task_id)
                if task is None:
                    yield f"data: {json.dumps({'error': 'not found'})}\n\n"
                    break
                yield f"data: {task.model_dump_json()}\n\n"
                if task.status.state in (TaskState.COMPLETED, TaskState.FAILED):
                    break
                await asyncio.sleep(0.5)

        return StreamingResponse(event_gen(), media_type="text/event-stream")

    return router


async def _run_handler(
    task: A2ATask,
    handler: Callable[[A2ATask], Coroutine[Any, Any, A2ATask]],
) -> None:
    try:
        result = await handler(task)
        _task_store[task.id] = result
    except Exception as exc:
        logger.exception("Task %s failed: %s", task.id, exc)
        task.status = TaskStatus(
            state=TaskState.FAILED,
            message=str(exc),
            timestamp=_now(),
        )
        _task_store[task.id] = task


# ─── A2A Client ───────────────────────────────────────────────────────────────

class A2AClient:
    """
    Async client for calling other A2A-compliant agents.

    Usage
    -----
    async with A2AClient("http://job-discovery-agent:8002") as client:
        result = await client.send_and_wait(
            text="Find Python jobs in Berlin",
            data={"profile": profile.model_dump()},
        )
    """

    def __init__(self, base_url: str, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._http: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> A2AClient:
        self._http = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, *_) -> None:
        if self._http:
            await self._http.aclose()

    # ── low-level ────────────────────────────────────────────────────────────

    async def get_agent_card(self) -> dict[str, Any]:
        resp = await self._http.get(f"{self.base_url}/.well-known/agent.json")
        resp.raise_for_status()
        return resp.json()

    async def submit_task(
        self,
        text: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
        role: str = "user",
    ) -> str:
        """Submit a task; returns the task ID."""
        parts: list[dict[str, Any]] = []
        if text:
            parts.append({"type": "text", "text": text})
        if data:
            parts.append({"type": "data", "data": data})

        payload = A2AMessage(role=role, parts=parts)
        resp = await self._http.post(
            f"{self.base_url}/tasks/send",
            content=payload.model_dump_json(),
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()["id"]

    async def poll_task(self, task_id: str) -> A2ATask:
        resp = await self._http.get(f"{self.base_url}/tasks/{task_id}")
        resp.raise_for_status()
        return A2ATask.model_validate(resp.json())

    # ── high-level ───────────────────────────────────────────────────────────

    async def send_and_wait(
        self,
        text: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
        poll_interval: float = 1.0,
    ) -> A2ATask:
        """Submit a task and block until it completes (or fails)."""
        task_id = await self.submit_task(text=text, data=data)
        while True:
            task = await self.poll_task(task_id)
            if task.status.state in (TaskState.COMPLETED, TaskState.FAILED):
                return task
            await asyncio.sleep(poll_interval)

    async def call(
        self,
        text: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Convenience wrapper: send task, wait, return first artifact data.
        Raises RuntimeError if task failed.
        """
        task = await self.send_and_wait(text=text, data=data)
        if task.status.state == TaskState.FAILED:
            raise RuntimeError(
                f"Agent at {self.base_url} failed: {task.status.message}"
            )
        # Extract first data part from first artifact
        for artifact in task.artifacts:
            for part in artifact.parts:
                if part.get("type") == "data":
                    return part["data"]
                if part.get("type") == "text":
                    return {"text": part["text"]}
        return {}


# ─── Server helper ────────────────────────────────────────────────────────────

def run_a2a_server(app, host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start a uvicorn server (blocking)."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


# ─── Helper: build a text artifact ───────────────────────────────────────────

def text_artifact(text: str, name: Optional[str] = None) -> Artifact:
    return Artifact(name=name, parts=[{"type": "text", "text": text}])


def data_artifact(data: dict[str, Any], name: Optional[str] = None) -> Artifact:
    return Artifact(name=name, parts=[{"type": "data", "data": data}])

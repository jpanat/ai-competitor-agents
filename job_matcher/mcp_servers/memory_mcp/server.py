"""
Memory MCP Server
=================
Provides session-scoped key-value storage so all agents can share state
without coupling directly. In production, back this with Redis or a DB.

Tools exposed:
  • store          – store any JSON-serialisable value under a namespaced key
  • retrieve       – get a stored value (returns null if missing)
  • list_keys      – list all keys for a session
  • delete         – remove a key
  • store_jobs     – convenience: store a list of job postings for a session
  • retrieve_jobs  – convenience: get stored job postings

Runs over SSE on MEMORY_MCP_PORT (default 9004).
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from fastapi import FastAPI, Request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from job_matcher.shared.config import MEMORY_MCP_PORT

server = Server("memory-mcp")

# ─── In-process store (swap with Redis in production) ─────────────────────────
_store: dict[str, Any] = {}


def _key(session_id: str, namespace: str) -> str:
    return f"{session_id}::{namespace}"


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="store",
            description="Store any JSON value under a session-scoped key.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "namespace":  {"type": "string", "description": "Logical key name, e.g. 'profile'"},
                    "value":      {"description": "Any JSON-serialisable value"},
                },
                "required": ["session_id", "namespace", "value"],
            },
        ),
        Tool(
            name="retrieve",
            description="Retrieve a value stored under a session-scoped key. Returns null if not found.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "namespace":  {"type": "string"},
                },
                "required": ["session_id", "namespace"],
            },
        ),
        Tool(
            name="list_keys",
            description="List all namespace keys stored for a session.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"}
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="delete",
            description="Delete a stored key for a session.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "namespace":  {"type": "string"},
                },
                "required": ["session_id", "namespace"],
            },
        ),
        Tool(
            name="store_jobs",
            description="Convenience: store a list of job postings for a session.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "jobs":       {"type": "array", "description": "List of JobPosting objects"},
                },
                "required": ["session_id", "jobs"],
            },
        ),
        Tool(
            name="retrieve_jobs",
            description="Convenience: retrieve stored job postings for a session.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"}
                },
                "required": ["session_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    session_id = arguments.get("session_id", "")

    if name == "store":
        k = _key(session_id, arguments["namespace"])
        _store[k] = arguments["value"]
        return [TextContent(type="text", text=json.dumps({"stored": True, "key": k}))]

    elif name == "retrieve":
        k = _key(session_id, arguments["namespace"])
        value = _store.get(k)
        return [TextContent(type="text", text=json.dumps({"value": value}))]

    elif name == "list_keys":
        prefix = f"{session_id}::"
        keys = [k.replace(prefix, "") for k in _store if k.startswith(prefix)]
        return [TextContent(type="text", text=json.dumps({"keys": keys}))]

    elif name == "delete":
        k = _key(session_id, arguments["namespace"])
        existed = _store.pop(k, None) is not None
        return [TextContent(type="text", text=json.dumps({"deleted": existed}))]

    elif name == "store_jobs":
        k = _key(session_id, "jobs")
        existing = _store.get(k, [])
        # Deduplicate by apply_url
        urls = {j.get("apply_url") for j in existing}
        new_jobs = [j for j in arguments["jobs"] if j.get("apply_url") not in urls]
        _store[k] = existing + new_jobs
        return [TextContent(type="text", text=json.dumps({"total_jobs": len(_store[k])}))]

    elif name == "retrieve_jobs":
        k = _key(session_id, "jobs")
        return [TextContent(type="text", text=json.dumps({"jobs": _store.get(k, [])}))]

    return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


# ─── FastAPI + SSE ────────────────────────────────────────────────────────────

app = FastAPI(title="Memory MCP Server")
sse_transport = SseServerTransport("/messages/")


@app.get("/sse")
async def sse_endpoint(request: Request):
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


@app.post("/messages/")
async def handle_messages(request: Request):
    await sse_transport.handle_post_message(request.scope, request.receive, request._send)


@app.get("/health")
async def health():
    return {"status": "ok", "server": "memory-mcp", "keys_stored": len(_store)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=MEMORY_MCP_PORT)

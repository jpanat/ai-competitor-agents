"""
Cover Letter Agent
==================
Generates a personalised cover letter for a specific job application.

A2A input:
  • data.profile    – UserProfile JSON
  • data.job        – JobPosting JSON
  • data.tone       – "professional" | "enthusiastic" | "concise"
  • data.session_id

A2A output:
  • data.cover_letter – CoverLetter JSON
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Annotated, Any, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from job_matcher.shared.config import ANTHROPIC_API_KEY, MODEL_NAME, MCP_URLS
from job_matcher.shared.models import A2ATask, TaskState, TaskStatus
from job_matcher.shared.a2a_protocol import data_artifact


class CoverLetterState(TypedDict):
    messages:     Annotated[list[BaseMessage], add_messages]
    profile:      dict[str, Any]
    job:          dict[str, Any]
    tone:         str
    session_id:   str
    cover_letter: dict[str, Any]


async def build_graph() -> Any:
    mcp_client = MultiServerMCPClient(
        {
            "document": {"url": MCP_URLS["document"], "transport": "sse"},
            "memory":   {"url": MCP_URLS["memory"],   "transport": "sse"},
        }
    )
    tools = await mcp_client.get_tools()

    llm = ChatAnthropic(
        model=MODEL_NAME,
        anthropic_api_key=ANTHROPIC_API_KEY,
        max_tokens=4096,
    ).bind_tools(tools)

    def agent_node(state: CoverLetterState) -> dict:
        return {"messages": [llm.invoke(state["messages"])]}

    def extract_letter(state: CoverLetterState) -> dict:
        for msg in state["messages"]:
            if hasattr(msg, "content") and isinstance(msg.content, str):
                try:
                    data = json.loads(msg.content)
                    if isinstance(data, dict) and "content" in data and "word_count" in data:
                        return {"cover_letter": data}
                except Exception:
                    pass
        return {"cover_letter": {}}

    graph = StateGraph(CoverLetterState)
    graph.add_node("agent",         agent_node)
    graph.add_node("tools",         ToolNode(tools))
    graph.add_node("extract_letter", extract_letter)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: "extract_letter"})
    graph.add_edge("tools", "agent")
    graph.add_edge("extract_letter", END)

    return graph.compile()


async def handle_task(task: A2ATask) -> A2ATask:
    profile    = {}
    job        = {}
    tone       = "professional"
    session_id = ""

    for part in task.message.parts:
        if part.get("type") == "data":
            d          = part["data"]
            profile    = d.get("profile", {})
            job        = d.get("job", {})
            tone       = d.get("tone", "professional")
            session_id = d.get("session_id", "")

    if not profile or not job:
        task.status = TaskStatus(state=TaskState.FAILED, message="Requires profile and job")
        return task

    prompt = f"""You are a Cover Letter Agent. Write a compelling cover letter for this application.

CANDIDATE: {profile.get('name')}
TARGET JOB: {job.get('title')} at {job.get('company')} ({job.get('location')})
TONE: {tone}
SESSION ID: {session_id}

STEPS:
1. Call generate_cover_letter with:
   - profile = full profile JSON
   - job = full job JSON
   - tone = "{tone}"
   - word_limit = 350
2. Store the result: store(session_id="{session_id}", namespace="cover_letter", value=<result>)

Profile: {json.dumps(profile)}
Job: {json.dumps(job)}

Write the cover letter now."""

    graph = await build_graph()
    final_state = await graph.ainvoke({
        "messages":     [HumanMessage(content=prompt)],
        "profile":      profile,
        "job":          job,
        "tone":         tone,
        "session_id":   session_id,
        "cover_letter": {},
    })

    cover_letter = final_state.get("cover_letter", {})

    task.status    = TaskStatus(state=TaskState.COMPLETED)
    task.artifacts = [data_artifact({
        "cover_letter": cover_letter,
        "session_id":   session_id,
        "job_id":       job.get("id", ""),
    }, name="cover_letter")]
    return task

"""
Profile Parser Agent
====================
LangGraph ReAct agent that parses a LinkedIn URL and/or resume text into
a canonical UserProfile using the Profile MCP Server tools.

Graph flow:
  parse_input → [tool calls] → synthesise_profile → END

A2A input (message.parts):
  • data.linkedin_url  (optional)
  • data.resume_text   (optional)
  • data.session_id    (required)

A2A output artifact:
  • data: UserProfile JSON + session_id
"""

from __future__ import annotations

import json
import os
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
from job_matcher.shared.models import A2ATask, Artifact, TaskState, TaskStatus, UserProfile
from job_matcher.shared.a2a_protocol import data_artifact

# ─── LangGraph State ──────────────────────────────────────────────────────────

class ProfileParserState(TypedDict):
    messages:     Annotated[list[BaseMessage], add_messages]
    linkedin_url: str
    resume_text:  str
    session_id:   str
    profile:      dict[str, Any]   # final UserProfile JSON


# ─── Graph builder ────────────────────────────────────────────────────────────

async def build_graph() -> Any:
    """
    Build the LangGraph profile parser graph, connected to MCP tools.
    Must be called inside an async context.
    """
    mcp_client = MultiServerMCPClient(
        {
            "profile": {"url": MCP_URLS["profile"], "transport": "sse"},
            "memory":  {"url": MCP_URLS["memory"],  "transport": "sse"},
        }
    )
    tools = await mcp_client.get_tools()

    llm = ChatAnthropic(
        model=MODEL_NAME,
        anthropic_api_key=ANTHROPIC_API_KEY,
        max_tokens=4096,
    ).bind_tools(tools)

    # ── Nodes ─────────────────────────────────────────────────────────────────

    def agent_node(state: ProfileParserState) -> dict:
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    def extract_profile(state: ProfileParserState) -> dict:
        """Extract the final profile JSON from the last AI message."""
        for msg in reversed(state["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                try:
                    import re
                    match = re.search(r"\{.*\}", msg.content, re.DOTALL)
                    if match:
                        profile = json.loads(match.group())
                        return {"profile": profile}
                except Exception:
                    pass
        return {"profile": {}}

    # ── Graph ─────────────────────────────────────────────────────────────────

    graph = StateGraph(ProfileParserState)
    graph.add_node("agent",           agent_node)
    graph.add_node("tools",           ToolNode(tools))
    graph.add_node("extract_profile", extract_profile)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: "extract_profile"})
    graph.add_edge("tools", "agent")
    graph.add_edge("extract_profile", END)

    return graph.compile()


# ─── A2A Task handler ─────────────────────────────────────────────────────────

async def handle_task(task: A2ATask) -> A2ATask:
    # Extract inputs from message parts
    linkedin_url = ""
    resume_text  = ""
    session_id   = ""

    for part in task.message.parts:
        if part.get("type") == "data":
            d = part["data"]
            linkedin_url = d.get("linkedin_url", "")
            resume_text  = d.get("resume_text", "")
            session_id   = d.get("session_id", "")
        elif part.get("type") == "text":
            linkedin_url = part.get("text", "")

    if not linkedin_url and not resume_text:
        task.status = TaskStatus(state=TaskState.FAILED, message="No linkedin_url or resume_text provided")
        return task

    # Build the initial prompt
    parts_desc = []
    if linkedin_url:
        parts_desc.append(f"LinkedIn URL: {linkedin_url}")
    if resume_text:
        parts_desc.append(f"Resume text provided ({len(resume_text)} chars)")

    system_prompt = f"""You are a Profile Parser Agent. Your job is to extract a complete,
structured user profile from the available sources.

You have access to these tools:
- parse_linkedin_profile: scrape and parse a LinkedIn profile
- parse_resume_text: parse raw resume text
- extract_skills: extract skills from any text
- merge_profile_sources: merge multiple profile sources into one
- store: store the final profile in memory

Available data:
{chr(10).join(parts_desc)}

Session ID: {session_id}

Steps:
1. Parse the LinkedIn profile if URL provided
2. Parse the resume text if provided
3. Merge sources if both available
4. Store the final profile with namespace="profile" and the given session_id
5. Return the complete UserProfile JSON

After all tool calls, output the final profile JSON."""

    initial_messages = [HumanMessage(content=system_prompt)]

    if linkedin_url and resume_text:
        initial_messages.append(HumanMessage(content=f"Parse linkedin_url='{linkedin_url}' and the provided resume."))
    elif linkedin_url:
        initial_messages.append(HumanMessage(content=f"Parse the LinkedIn profile at: {linkedin_url}"))
    else:
        initial_messages.append(HumanMessage(content=f"Parse this resume:\n\n{resume_text[:4000]}"))

    graph = await build_graph()

    final_state = await graph.ainvoke({
        "messages":     initial_messages,
        "linkedin_url": linkedin_url,
        "resume_text":  resume_text,
        "session_id":   session_id,
        "profile":      {},
    })

    profile = final_state.get("profile", {})

    task.status    = TaskStatus(state=TaskState.COMPLETED)
    task.artifacts = [data_artifact({"profile": profile, "session_id": session_id}, name="user_profile")]
    return task

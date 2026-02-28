"""
Job Discovery Agent
===================
LangGraph ReAct agent that fans out across LinkedIn, Indeed, and Glassdoor
to discover relevant job openings based on a user profile.

A2A input:
  • data.profile    – UserProfile JSON
  • data.session_id – session ID

A2A output:
  • data.jobs       – list of JobPosting dicts
  • data.session_id
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


class JobDiscoveryState(TypedDict):
    messages:   Annotated[list[BaseMessage], add_messages]
    profile:    dict[str, Any]
    session_id: str
    jobs:       list[dict[str, Any]]


async def build_graph() -> Any:
    mcp_client = MultiServerMCPClient(
        {
            "job_board": {"url": MCP_URLS["job_board"], "transport": "sse"},
            "memory":    {"url": MCP_URLS["memory"],    "transport": "sse"},
        }
    )
    tools = await mcp_client.get_tools()

    llm = ChatAnthropic(
        model=MODEL_NAME,
        anthropic_api_key=ANTHROPIC_API_KEY,
        max_tokens=4096,
    ).bind_tools(tools)

    def agent_node(state: JobDiscoveryState) -> dict:
        return {"messages": [llm.invoke(state["messages"])]}

    def extract_jobs(state: JobDiscoveryState) -> dict:
        """Pull job list from tool results in the conversation."""
        jobs: list[dict] = []
        for msg in state["messages"]:
            # Tool messages contain JSON arrays of job objects
            if hasattr(msg, "content") and isinstance(msg.content, str):
                try:
                    parsed = json.loads(msg.content)
                    if isinstance(parsed, list):
                        jobs.extend(parsed)
                    elif isinstance(parsed, dict) and "jobs" in parsed:
                        jobs.extend(parsed["jobs"])
                except Exception:
                    pass
        # Deduplicate by apply_url
        seen: set[str] = set()
        unique: list[dict] = []
        for j in jobs:
            url = j.get("apply_url", "")
            if url and url not in seen:
                seen.add(url)
                unique.append(j)
        return {"jobs": unique}

    graph = StateGraph(JobDiscoveryState)
    graph.add_node("agent",        agent_node)
    graph.add_node("tools",        ToolNode(tools))
    graph.add_node("extract_jobs", extract_jobs)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: "extract_jobs"})
    graph.add_edge("tools", "agent")
    graph.add_edge("extract_jobs", END)

    return graph.compile()


async def handle_task(task: A2ATask) -> A2ATask:
    profile    = {}
    session_id = ""

    for part in task.message.parts:
        if part.get("type") == "data":
            profile    = part["data"].get("profile", {})
            session_id = part["data"].get("session_id", "")

    if not profile:
        task.status = TaskStatus(state=TaskState.FAILED, message="No profile provided")
        return task

    # Build search parameters from profile
    roles     = profile.get("desired_roles", []) or [profile.get("headline", "Software Engineer")]
    locations = profile.get("desired_locations", []) or [profile.get("location", "")]
    skills    = (profile.get("skills", []) or [])[:8]
    work_type = profile.get("work_type", "")

    primary_role     = roles[0] if roles else "Software Engineer"
    primary_location = locations[0] if locations else ""

    prompt = f"""You are a Job Discovery Agent. Find relevant job openings for this candidate.

CANDIDATE:
- Role target: {', '.join(roles)}
- Location preference: {', '.join(locations) if locations else 'any / remote'}
- Key skills: {', '.join(skills)}
- Work type: {work_type or 'any'}
- Total experience: {profile.get('total_years_exp', 'unknown')} years

INSTRUCTIONS:
1. Use search_all_boards to search for "{primary_role}" jobs in "{primary_location or 'remote'}"
2. Also search for variations:
   - Search LinkedIn for a related senior/mid role
   - Search Indeed with key skills as query
3. Use store_jobs to save all found jobs with session_id="{session_id}"
4. Aim to discover 15-25 unique, relevant job postings

Start searching now."""

    graph = await build_graph()
    final_state = await graph.ainvoke({
        "messages":   [HumanMessage(content=prompt)],
        "profile":    profile,
        "session_id": session_id,
        "jobs":       [],
    })

    jobs = final_state.get("jobs", [])

    task.status    = TaskStatus(state=TaskState.COMPLETED)
    task.artifacts = [data_artifact({"jobs": jobs, "session_id": session_id, "count": len(jobs)}, name="discovered_jobs")]
    return task

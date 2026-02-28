"""
Resume Tailor Agent
===================
Uses the Document MCP Server to rewrite the user's resume for a target job.
Also runs ATS scoring and suggests improvements.

A2A input:
  • data.profile            – UserProfile JSON
  • data.job                – JobPosting JSON (the target job)
  • data.original_resume    – raw original resume text (optional)
  • data.session_id

A2A output:
  • data.tailored_resume    – TailoredResume JSON
  • data.session_id
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
from job_matcher.shared.models import A2ATask, TaskState, TaskStatus
from job_matcher.shared.a2a_protocol import data_artifact


class ResumeTailorState(TypedDict):
    messages:         Annotated[list[BaseMessage], add_messages]
    profile:          dict[str, Any]
    job:              dict[str, Any]
    original_resume:  str
    session_id:       str
    tailored_resume:  dict[str, Any]


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

    def agent_node(state: ResumeTailorState) -> dict:
        return {"messages": [llm.invoke(state["messages"])]}

    def extract_resume(state: ResumeTailorState) -> dict:
        import re
        for msg in reversed(state["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                try:
                    match = re.search(r"\{.*\}", msg.content, re.DOTALL)
                    if match:
                        return {"tailored_resume": json.loads(match.group())}
                except Exception:
                    pass
            if hasattr(msg, "content") and isinstance(msg.content, str):
                try:
                    data = json.loads(msg.content)
                    if isinstance(data, dict) and "content" in data:
                        return {"tailored_resume": data}
                except Exception:
                    pass
        return {"tailored_resume": {}}

    graph = StateGraph(ResumeTailorState)
    graph.add_node("agent",          agent_node)
    graph.add_node("tools",          ToolNode(tools))
    graph.add_node("extract_resume", extract_resume)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: "extract_resume"})
    graph.add_edge("tools", "agent")
    graph.add_edge("extract_resume", END)

    return graph.compile()


async def handle_task(task: A2ATask) -> A2ATask:
    profile         = {}
    job             = {}
    original_resume = ""
    session_id      = ""

    for part in task.message.parts:
        if part.get("type") == "data":
            d               = part["data"]
            profile         = d.get("profile", {})
            job             = d.get("job", {})
            original_resume = d.get("original_resume", "")
            session_id      = d.get("session_id", "")

    if not profile or not job:
        task.status = TaskStatus(state=TaskState.FAILED, message="Requires profile and job")
        return task

    prompt = f"""You are a Resume Tailor Agent. Rewrite this candidate's resume to best match the target job.

TARGET JOB:
- Title: {job.get('title')} at {job.get('company')}
- Location: {job.get('location')}
- Required skills: {', '.join(job.get('skills_required', []))}
- Key requirements: {', '.join((job.get('requirements') or [])[:5])}

SESSION ID: {session_id}

STEPS:
1. Call generate_tailored_resume with:
   - profile = {json.dumps(profile)[:500]}... (use the full profile)
   - job = the full job object
   - original_resume_text = "{original_resume[:200]}..." if provided

2. Call score_resume_ats with the generated resume content and the job
3. Store the tailored resume using: store(session_id="{session_id}", namespace="tailored_resume", value=<result>)

Profile: {json.dumps(profile)}
Job: {json.dumps(job)}
Original resume: {original_resume[:2000] if original_resume else "Not provided"}

Generate the tailored resume now."""

    graph = await build_graph()
    final_state = await graph.ainvoke({
        "messages":        [HumanMessage(content=prompt)],
        "profile":         profile,
        "job":             job,
        "original_resume": original_resume,
        "session_id":      session_id,
        "tailored_resume": {},
    })

    tailored = final_state.get("tailored_resume", {})

    task.status    = TaskStatus(state=TaskState.COMPLETED)
    task.artifacts = [data_artifact({
        "tailored_resume": tailored,
        "session_id":      session_id,
        "job_id":          job.get("id", ""),
    }, name="tailored_resume")]
    return task

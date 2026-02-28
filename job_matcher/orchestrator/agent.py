"""
Orchestrator Agent
==================
The master LangGraph agent that coordinates the full job-matching pipeline.
It talks to all 7 specialised agents via the A2A protocol.

Pipeline stages (conditional – steps run only if enabled in the request):
  1. Profile Parser   → parse LinkedIn + resume
  2. Job Discovery    → search all job boards
  3. Job Matcher      → score & rank jobs
  4. (User selects target job)
  5. Resume Tailor    → customise resume for chosen job
  6. Cover Letter     → generate cover letter
  7. Gap Analysis     → identify skill gaps + action plan
  8. Interview Prep   → company research + Q&A

All stages run sequentially; stages 5-8 can also be run on any top-match
without user selection by defaulting to the #1 match.

State:
  session_id, request, profile, jobs, matches,
  selected_job, tailored_resume, cover_letter, gap_analysis, interview_prep,
  errors, next_stage
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from typing import Annotated, Any, Literal, Optional, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from job_matcher.shared.a2a_protocol import A2AClient
from job_matcher.shared.config import AGENT_URLS, ANTHROPIC_API_KEY, MODEL_NAME
from job_matcher.shared.models import (
    A2ATask,
    PipelineRequest,
    PipelineResult,
    TaskState,
    TaskStatus,
)
from job_matcher.shared.a2a_protocol import data_artifact


# ─── Orchestrator State ───────────────────────────────────────────────────────

class OrchestratorState(TypedDict):
    messages:       Annotated[list[BaseMessage], add_messages]
    session_id:     str
    request:        dict[str, Any]         # PipelineRequest JSON
    profile:        Optional[dict]
    jobs:           list[dict]
    matches:        list[dict]
    selected_job:   Optional[dict]         # Target job for docs + prep
    tailored_resume: Optional[dict]
    cover_letter:   Optional[dict]
    gap_analysis:   Optional[dict]
    interview_prep: Optional[dict]
    errors:         list[str]
    next_stage:     str


# ─── Stage runner helpers ─────────────────────────────────────────────────────

async def _call_agent(agent_name: str, data: dict[str, Any]) -> dict[str, Any]:
    """Call an A2A agent and return the first data artifact."""
    url = AGENT_URLS[agent_name]
    async with A2AClient(url) as client:
        return await client.call(data=data)


# ─── Graph Nodes ──────────────────────────────────────────────────────────────

async def stage_parse_profile(state: OrchestratorState) -> dict:
    req        = state["request"]
    session_id = state["session_id"]
    try:
        result = await _call_agent("profile_parser", {
            "linkedin_url": req.get("linkedin_url", ""),
            "resume_text":  req.get("resume_text", ""),
            "session_id":   session_id,
        })
        profile = result.get("profile", {})
        # Merge desired_roles / desired_locations from request into profile
        if req.get("desired_roles"):
            profile["desired_roles"] = req["desired_roles"]
        if req.get("locations"):
            profile["desired_locations"] = req["locations"]
        return {"profile": profile, "next_stage": "job_discovery"}
    except Exception as e:
        return {"errors": [f"Profile parsing failed: {e}"], "next_stage": END}


async def stage_job_discovery(state: OrchestratorState) -> dict:
    if not state["request"].get("run_job_search", True):
        return {"next_stage": "job_match"}
    try:
        result = await _call_agent("job_discovery", {
            "profile":    state["profile"],
            "session_id": state["session_id"],
        })
        return {"jobs": result.get("jobs", []), "next_stage": "job_match"}
    except Exception as e:
        return {"errors": state["errors"] + [f"Job discovery failed: {e}"], "next_stage": "job_match"}


async def stage_job_match(state: OrchestratorState) -> dict:
    jobs = state.get("jobs", [])
    if not jobs:
        return {"matches": [], "next_stage": "select_job"}
    try:
        result = await _call_agent("job_matcher", {
            "profile":    state["profile"],
            "jobs":       jobs,
            "session_id": state["session_id"],
        })
        return {"matches": result.get("matches", []), "next_stage": "select_job"}
    except Exception as e:
        return {"errors": state["errors"] + [f"Job matching failed: {e}"], "next_stage": "select_job"}


def stage_select_job(state: OrchestratorState) -> dict:
    """
    Auto-select the top job match for downstream document generation.
    In a real UI, this step would wait for user input.
    """
    req            = state["request"]
    specified_id   = req.get("target_job_id")
    matches        = state.get("matches", [])

    if specified_id:
        for m in matches:
            if m.get("job", {}).get("id") == specified_id:
                return {"selected_job": m["job"], "next_stage": "parallel_docs"}
        # Try raw jobs list
        for j in state.get("jobs", []):
            if j.get("id") == specified_id:
                return {"selected_job": j, "next_stage": "parallel_docs"}

    if matches:
        return {"selected_job": matches[0]["job"], "next_stage": "parallel_docs"}

    return {"selected_job": None, "next_stage": END}


async def stage_resume_tailor(state: OrchestratorState) -> dict:
    if not state["request"].get("run_resume_tailor", True) or not state["selected_job"]:
        return {"tailored_resume": None}
    try:
        result = await _call_agent("resume_tailor", {
            "profile":         state["profile"],
            "job":             state["selected_job"],
            "original_resume": state["request"].get("resume_text", ""),
            "session_id":      state["session_id"],
        })
        return {"tailored_resume": result.get("tailored_resume", {})}
    except Exception as e:
        return {"errors": state["errors"] + [f"Resume tailoring failed: {e}"], "tailored_resume": None}


async def stage_cover_letter(state: OrchestratorState) -> dict:
    if not state["request"].get("run_cover_letter", True) or not state["selected_job"]:
        return {"cover_letter": None}
    try:
        result = await _call_agent("cover_letter", {
            "profile":    state["profile"],
            "job":        state["selected_job"],
            "tone":       "professional",
            "session_id": state["session_id"],
        })
        return {"cover_letter": result.get("cover_letter", {})}
    except Exception as e:
        return {"errors": state["errors"] + [f"Cover letter failed: {e}"], "cover_letter": None}


async def stage_gap_analysis(state: OrchestratorState) -> dict:
    if not state["request"].get("run_gap_analysis", True) or not state["selected_job"]:
        return {"gap_analysis": None}
    try:
        result = await _call_agent("gap_analysis", {
            "profile":    state["profile"],
            "job":        state["selected_job"],
            "session_id": state["session_id"],
        })
        return {"gap_analysis": result.get("gap_analysis", {})}
    except Exception as e:
        return {"errors": state["errors"] + [f"Gap analysis failed: {e}"], "gap_analysis": None}


async def stage_interview_prep(state: OrchestratorState) -> dict:
    if not state["request"].get("run_interview_prep", True) or not state["selected_job"]:
        return {"interview_prep": None}
    try:
        result = await _call_agent("interview_prep", {
            "profile":    state["profile"],
            "job":        state["selected_job"],
            "session_id": state["session_id"],
        })
        return {"interview_prep": result.get("interview_prep", {})}
    except Exception as e:
        return {"errors": state["errors"] + [f"Interview prep failed: {e}"], "interview_prep": None}


def stage_finalise(state: OrchestratorState) -> dict:
    """Compile the final PipelineResult."""
    result = PipelineResult(
        session_id      = state["session_id"],
        profile         = state.get("profile"),
        job_matches     = state.get("matches", []),
        tailored_resume = state.get("tailored_resume"),
        cover_letter    = state.get("cover_letter"),
        gap_analysis    = state.get("gap_analysis"),
        interview_prep  = state.get("interview_prep"),
        errors          = state.get("errors", []),
    )
    return {
        "messages": [HumanMessage(content=f"Pipeline complete. session_id={state['session_id']}")],
    }


# ─── Routing logic ────────────────────────────────────────────────────────────

def route_after_select(state: OrchestratorState) -> Literal["resume_tailor", "__end__"]:
    return "resume_tailor" if state.get("selected_job") else END


# ─── Graph builder ────────────────────────────────────────────────────────────

def build_graph() -> Any:
    graph = StateGraph(OrchestratorState)

    graph.add_node("parse_profile",  stage_parse_profile)
    graph.add_node("job_discovery",  stage_job_discovery)
    graph.add_node("job_match",      stage_job_match)
    graph.add_node("select_job",     stage_select_job)
    graph.add_node("resume_tailor",  stage_resume_tailor)
    graph.add_node("cover_letter",   stage_cover_letter)
    graph.add_node("gap_analysis",   stage_gap_analysis)
    graph.add_node("interview_prep", stage_interview_prep)
    graph.add_node("finalise",       stage_finalise)

    # Sequential pipeline
    graph.set_entry_point("parse_profile")
    graph.add_edge("parse_profile",  "job_discovery")
    graph.add_edge("job_discovery",  "job_match")
    graph.add_edge("job_match",      "select_job")

    # After job selection, run docs in sequence (could be parallelised with Send API)
    graph.add_conditional_edges("select_job", route_after_select,
                                {"resume_tailor": "resume_tailor", END: "finalise"})
    graph.add_edge("resume_tailor",  "cover_letter")
    graph.add_edge("cover_letter",   "gap_analysis")
    graph.add_edge("gap_analysis",   "interview_prep")
    graph.add_edge("interview_prep", "finalise")
    graph.add_edge("finalise",       END)

    return graph.compile()


# ─── A2A Task handler ─────────────────────────────────────────────────────────

async def handle_task(task: A2ATask) -> A2ATask:
    request_data = {}
    for part in task.message.parts:
        if part.get("type") == "data":
            request_data = part["data"]
        elif part.get("type") == "text":
            # Try to parse text as JSON
            try:
                request_data = json.loads(part["text"])
            except Exception:
                request_data = {"linkedin_url": part["text"]}

    session_id = request_data.get("session_id") or str(uuid.uuid4())

    graph = build_graph()

    initial_state: OrchestratorState = {
        "messages":        [HumanMessage(content="Starting job matching pipeline")],
        "session_id":      session_id,
        "request":         request_data,
        "profile":         None,
        "jobs":            [],
        "matches":         [],
        "selected_job":    None,
        "tailored_resume": None,
        "cover_letter":    None,
        "gap_analysis":    None,
        "interview_prep":  None,
        "errors":          [],
        "next_stage":      "parse_profile",
    }

    final_state = await graph.ainvoke(initial_state)

    result = {
        "session_id":      session_id,
        "profile":         final_state.get("profile"),
        "job_matches":     final_state.get("matches", []),
        "tailored_resume": final_state.get("tailored_resume"),
        "cover_letter":    final_state.get("cover_letter"),
        "gap_analysis":    final_state.get("gap_analysis"),
        "interview_prep":  final_state.get("interview_prep"),
        "errors":          final_state.get("errors", []),
    }

    task.status    = TaskStatus(state=TaskState.COMPLETED)
    task.artifacts = [data_artifact(result, name="pipeline_result")]
    return task

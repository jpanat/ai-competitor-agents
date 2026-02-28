"""
Job Matcher Agent
=================
LangGraph agent that scores and ranks job postings against a user profile,
producing a list of JobMatch objects sorted by match_score.

Scoring dimensions:
  • skill_match_pct      – % of required skills the candidate has
  • experience_match_pct – does seniority / years align?
  • culture_match_pct    – location, work type, salary alignment

A2A input:
  • data.profile    – UserProfile JSON
  • data.jobs       – list of JobPosting dicts
  • data.session_id

A2A output:
  • data.matches    – list of JobMatch dicts (top 10, sorted by match_score)
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
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from job_matcher.shared.config import ANTHROPIC_API_KEY, MODEL_NAME
from job_matcher.shared.models import A2ATask, TaskState, TaskStatus
from job_matcher.shared.a2a_protocol import data_artifact


class JobMatcherState(TypedDict):
    messages:   Annotated[list[BaseMessage], add_messages]
    profile:    dict[str, Any]
    jobs:       list[dict[str, Any]]
    session_id: str
    matches:    list[dict[str, Any]]


# ─── Local scoring tools (no MCP needed) ─────────────────────────────────────

@tool
def score_job_match(profile_json: str, job_json: str) -> str:
    """
    Score a single job against a candidate profile.
    Returns a JobMatch JSON with skill/experience/culture scores.

    profile_json: JSON string of UserProfile
    job_json: JSON string of JobPosting
    """
    import math

    profile = json.loads(profile_json)
    job     = json.loads(job_json)

    candidate_skills = set(s.lower() for s in profile.get("skills", []))
    required_skills  = set(s.lower() for s in job.get("skills_required", []))

    # Skill match
    if required_skills:
        skill_match = len(candidate_skills & required_skills) / len(required_skills) * 100
    else:
        skill_match = 70.0  # neutral if no skills listed

    # Experience match
    years_exp = profile.get("total_years_exp") or len(profile.get("experience", [])) * 1.5
    level     = job.get("experience_level", "mid")
    level_map = {"entry": (0, 2), "mid": (2, 6), "senior": (6, 12), "executive": (10, 50)}
    lo, hi    = level_map.get(level, (0, 50))
    if lo <= years_exp <= hi:
        exp_match = 100.0
    elif years_exp < lo:
        exp_match = max(0.0, 100 - (lo - years_exp) * 20)
    else:
        exp_match = max(50.0, 100 - (years_exp - hi) * 5)

    # Culture / logistics match
    culture_score = 70.0
    desired_locs = [l.lower() for l in profile.get("desired_locations", [])]
    job_location = (job.get("location") or "").lower()
    if job.get("remote_ok") and profile.get("work_type") in ("remote", None, ""):
        culture_score += 15
    elif any(loc in job_location for loc in desired_locs) or any(job_location in loc for loc in desired_locs):
        culture_score += 10

    sal_range     = job.get("salary_range") or {}
    desired_range = profile.get("salary_range") or {}
    if sal_range and desired_range:
        job_max   = sal_range.get("max", 0)
        my_min    = desired_range.get("min", 0)
        if job_max >= my_min:
            culture_score += 15
        else:
            culture_score -= 20

    culture_score = max(0.0, min(100.0, culture_score))

    composite = skill_match * 0.45 + exp_match * 0.35 + culture_score * 0.20

    match = {
        "job":                  job,
        "match_score":          round(composite, 1),
        "skill_match_pct":      round(skill_match, 1),
        "experience_match_pct": round(exp_match, 1),
        "culture_match_pct":    round(culture_score, 1),
        "match_reasons":        [],
        "concerns":             [],
    }
    return json.dumps(match)


@tool
def rank_matches(matches_json: str, top_n: int = 10) -> str:
    """
    Sort a list of JobMatch dicts by match_score descending and return top N.
    matches_json: JSON array of JobMatch objects.
    """
    matches = json.loads(matches_json)
    ranked  = sorted(matches, key=lambda m: m.get("match_score", 0), reverse=True)
    return json.dumps(ranked[:top_n])


TOOLS = [score_job_match, rank_matches]


async def build_graph() -> Any:
    llm = ChatAnthropic(
        model=MODEL_NAME,
        anthropic_api_key=ANTHROPIC_API_KEY,
        max_tokens=4096,
    ).bind_tools(TOOLS)

    def agent_node(state: JobMatcherState) -> dict:
        return {"messages": [llm.invoke(state["messages"])]}

    def extract_matches(state: JobMatcherState) -> dict:
        matches: list[dict] = []
        for msg in state["messages"]:
            if hasattr(msg, "content") and isinstance(msg.content, str):
                try:
                    parsed = json.loads(msg.content)
                    if isinstance(parsed, list) and parsed and "match_score" in parsed[0]:
                        matches = parsed
                except Exception:
                    pass
        return {"matches": matches}

    graph = StateGraph(JobMatcherState)
    graph.add_node("agent",           agent_node)
    graph.add_node("tools",           ToolNode(TOOLS))
    graph.add_node("extract_matches", extract_matches)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: "extract_matches"})
    graph.add_edge("tools", "agent")
    graph.add_edge("extract_matches", END)

    return graph.compile()


async def handle_task(task: A2ATask) -> A2ATask:
    profile    = {}
    jobs       = []
    session_id = ""

    for part in task.message.parts:
        if part.get("type") == "data":
            profile    = part["data"].get("profile", {})
            jobs       = part["data"].get("jobs", [])
            session_id = part["data"].get("session_id", "")

    if not profile or not jobs:
        task.status = TaskStatus(state=TaskState.FAILED, message="Requires profile and jobs")
        return task

    profile_json = json.dumps(profile)

    prompt = f"""You are a Job Matching Agent. Score and rank {len(jobs)} job postings against the candidate's profile.

CANDIDATE SUMMARY:
- Name: {profile.get('name')}
- Skills: {', '.join((profile.get('skills') or [])[:10])}
- Experience: {profile.get('total_years_exp')} years
- Desired roles: {', '.join(profile.get('desired_roles', []))}
- Desired locations: {', '.join(profile.get('desired_locations', []))}

INSTRUCTIONS:
1. Call score_job_match for EACH of the {len(jobs)} jobs. Pass the full profile JSON and job JSON.
2. Collect all match objects into a list.
3. Call rank_matches with the full list to get the top 10.
4. Return the ranked list.

Profile JSON (pass this to each score_job_match call):
{profile_json}

Jobs to score (pass each individually to score_job_match):
{json.dumps(jobs[:20])}

Start scoring now."""

    graph = await build_graph()
    final_state = await graph.ainvoke({
        "messages":   [HumanMessage(content=prompt)],
        "profile":    profile,
        "jobs":       jobs,
        "session_id": session_id,
        "matches":    [],
    })

    matches = final_state.get("matches", [])

    task.status    = TaskStatus(state=TaskState.COMPLETED)
    task.artifacts = [data_artifact({
        "matches":    matches,
        "session_id": session_id,
        "count":      len(matches),
    }, name="job_matches")]
    return task

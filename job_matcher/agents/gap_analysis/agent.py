"""
Gap Analysis Agent
==================
Identifies skill, experience, and education gaps between the candidate and
a target job. Provides a prioritised action plan with learning resources.

A2A input:
  • data.profile    – UserProfile JSON
  • data.job        – JobPosting JSON
  • data.session_id

A2A output:
  • data.gap_analysis – GapAnalysis JSON
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
from job_matcher.shared.config import ANTHROPIC_API_KEY, MODEL_NAME, TAVILY_API_KEY
from job_matcher.shared.models import A2ATask, TaskState, TaskStatus
from job_matcher.shared.a2a_protocol import data_artifact


class GapAnalysisState(TypedDict):
    messages:     Annotated[list[BaseMessage], add_messages]
    profile:      dict[str, Any]
    job:          dict[str, Any]
    session_id:   str
    gap_analysis: dict[str, Any]


@tool
def identify_skill_gaps(profile_skills_json: str, required_skills_json: str) -> str:
    """
    Compare candidate skills to job requirements and return a list of skill gaps.

    profile_skills_json: JSON array of candidate skills
    required_skills_json: JSON array of required job skills
    """
    candidate = set(s.lower() for s in json.loads(profile_skills_json))
    required  = json.loads(required_skills_json)

    gaps = []
    for skill in required:
        if skill.lower() not in candidate:
            # Heuristic severity based on position in requirements list
            idx = required.index(skill)
            severity = "critical" if idx < 3 else ("important" if idx < 7 else "nice_to_have")
            gaps.append({
                "skill":         skill,
                "severity":      severity,
                "current_level": "none",
                "target_level":  "proficient",
                "resources":     [],
            })
    return json.dumps(gaps)


@tool
def search_learning_resources(skill: str) -> str:
    """
    Find online learning resources for a given skill using web search.
    Returns a list of course/resource URLs and descriptions.

    skill: The skill to find learning resources for
    """
    import asyncio
    import httpx

    async def _search():
        if not TAVILY_API_KEY:
            return [
                f"Coursera: https://coursera.org/search?query={skill.replace(' ', '+')}",
                f"Udemy: https://udemy.com/courses/search/?q={skill.replace(' ', '+')}",
                f"LinkedIn Learning: https://linkedin.com/learning/search?keywords={skill.replace(' ', '+')}",
            ]
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": TAVILY_API_KEY,
                    "query":   f"best online course learn {skill} 2024 2025",
                    "max_results": 5,
                },
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            return [f"{r['title']}: {r['url']}" for r in results]

    resources = asyncio.get_event_loop().run_until_complete(_search())
    return json.dumps(resources)


TOOLS = [identify_skill_gaps, search_learning_resources]


async def build_graph() -> Any:
    llm = ChatAnthropic(
        model=MODEL_NAME,
        anthropic_api_key=ANTHROPIC_API_KEY,
        max_tokens=4096,
    ).bind_tools(TOOLS)

    def agent_node(state: GapAnalysisState) -> dict:
        return {"messages": [llm.invoke(state["messages"])]}

    def extract_analysis(state: GapAnalysisState) -> dict:
        for msg in reversed(state["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                try:
                    match = re.search(r"\{.*\}", msg.content, re.DOTALL)
                    if match:
                        data = json.loads(match.group())
                        if "skill_gaps" in data or "overall_readiness" in data:
                            return {"gap_analysis": data}
                except Exception:
                    pass
        return {"gap_analysis": {}}

    graph = StateGraph(GapAnalysisState)
    graph.add_node("agent",           agent_node)
    graph.add_node("tools",           ToolNode(TOOLS))
    graph.add_node("extract_analysis", extract_analysis)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: "extract_analysis"})
    graph.add_edge("tools", "agent")
    graph.add_edge("extract_analysis", END)

    return graph.compile()


async def handle_task(task: A2ATask) -> A2ATask:
    profile    = {}
    job        = {}
    session_id = ""

    for part in task.message.parts:
        if part.get("type") == "data":
            d          = part["data"]
            profile    = d.get("profile", {})
            job        = d.get("job", {})
            session_id = d.get("session_id", "")

    if not profile or not job:
        task.status = TaskStatus(state=TaskState.FAILED, message="Requires profile and job")
        return task

    candidate_skills = json.dumps(profile.get("skills", []))
    required_skills  = json.dumps(job.get("skills_required", []) + (job.get("requirements") or [])[:5])
    years_exp        = profile.get("total_years_exp") or len(profile.get("experience", [])) * 1.5

    prompt = f"""You are a Gap Analysis Agent. Identify and analyse all gaps between this candidate and the target job.

CANDIDATE: {profile.get('name')} | {years_exp} years experience
TARGET JOB: {job.get('title')} at {job.get('company')}
Required skills: {', '.join(job.get('skills_required', [])[:10])}

STEPS:
1. Call identify_skill_gaps with:
   - profile_skills_json = {candidate_skills}
   - required_skills_json = {required_skills}

2. For the top 3 CRITICAL gaps, call search_learning_resources to find courses.

3. After all tool calls, synthesise everything into a comprehensive GapAnalysis and output ONLY this JSON:
{{
  "job_id": "{job.get('id', '')}",
  "skill_gaps": [
    {{
      "skill": "Kubernetes",
      "severity": "critical",
      "current_level": "none",
      "target_level": "proficient",
      "resources": ["Course URL 1", "Course URL 2"]
    }}
  ],
  "experience_gaps": ["Need 2 more years in team leadership"],
  "education_gaps": [],
  "strengths": ["Strong Python background", "Relevant domain experience"],
  "overall_readiness": 72.5,
  "action_plan": [
    "Complete Kubernetes CKA certification (3 months)",
    "Build a side project using required tech stack"
  ]
}}

Start the analysis now."""

    graph = await build_graph()
    final_state = await graph.ainvoke({
        "messages":     [HumanMessage(content=prompt)],
        "profile":      profile,
        "job":          job,
        "session_id":   session_id,
        "gap_analysis": {},
    })

    gap_analysis = final_state.get("gap_analysis", {})

    task.status    = TaskStatus(state=TaskState.COMPLETED)
    task.artifacts = [data_artifact({
        "gap_analysis": gap_analysis,
        "session_id":   session_id,
        "job_id":       job.get("id", ""),
    }, name="gap_analysis")]
    return task

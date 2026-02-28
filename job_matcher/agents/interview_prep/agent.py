"""
Interview Prep Agent
====================
Prepares the candidate for a job interview by:
  - Researching the company (culture, recent news, products)
  - Generating role-specific technical questions + model answers
  - Generating STAR-format behavioural questions
  - Suggesting questions the candidate should ask the interviewer
  - Flagging potential red flags / salary negotiation tips

A2A input:
  • data.profile    – UserProfile JSON
  • data.job        – JobPosting JSON
  • data.session_id

A2A output:
  • data.interview_prep – InterviewPrep JSON
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


class InterviewPrepState(TypedDict):
    messages:       Annotated[list[BaseMessage], add_messages]
    profile:        dict[str, Any]
    job:            dict[str, Any]
    session_id:     str
    interview_prep: dict[str, Any]


@tool
def research_company(company_name: str, job_title: str) -> str:
    """
    Research a company to prepare for an interview: culture, recent news,
    products, mission, tech stack, interview style.

    company_name: Name of the hiring company
    job_title: The role being applied for
    """
    import asyncio
    import httpx

    async def _search():
        if not TAVILY_API_KEY:
            return {"company": company_name, "summary": "Research not available - TAVILY_API_KEY not set"}

        async with httpx.AsyncClient(timeout=20) as client:
            queries = [
                f"{company_name} company culture glassdoor review 2024 2025",
                f"{company_name} recent news funding products 2024 2025",
                f"{company_name} {job_title} interview questions process",
            ]
            all_results = []
            for q in queries:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={"api_key": TAVILY_API_KEY, "query": q, "max_results": 3},
                )
                if resp.status_code == 200:
                    all_results.extend(resp.json().get("results", []))

            return {
                "company":  company_name,
                "snippets": [{"title": r["title"], "content": r["content"][:300]} for r in all_results[:9]],
            }

    result = asyncio.get_event_loop().run_until_complete(_search())
    return json.dumps(result)


@tool
def generate_technical_questions(job_title: str, skills_json: str, difficulty: str = "mixed") -> str:
    """
    Generate technical interview questions for the role.

    job_title: The job title
    skills_json: JSON array of required technical skills
    difficulty: "easy" | "medium" | "hard" | "mixed"
    """
    import asyncio
    import anthropic

    async def _generate():
        client  = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        skills  = json.loads(skills_json)
        prompt  = f"""Generate 8 technical interview questions for a {job_title} role.
Required skills: {', '.join(skills[:10])}
Difficulty: {difficulty}

Return ONLY a JSON array:
[
  {{
    "question": "Explain the difference between X and Y",
    "category": "technical",
    "difficulty": "medium",
    "suggested_answer": "Detailed model answer...",
    "tips": ["Draw a diagram", "Mention trade-offs"]
  }}
]"""
        msg = await client.messages.create(
            model=MODEL_NAME, max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw   = msg.content[0].text
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        return json.loads(match.group()) if match else []

    return json.dumps(asyncio.get_event_loop().run_until_complete(_generate()))


@tool
def generate_behavioral_questions(job_title: str, company_values_json: str) -> str:
    """
    Generate STAR-format behavioural interview questions relevant to the role.

    job_title: The job title
    company_values_json: JSON array of company values or culture keywords
    """
    import asyncio
    import anthropic

    async def _generate():
        client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        values = json.loads(company_values_json) if company_values_json else []
        prompt = f"""Generate 6 behavioural interview questions for a {job_title} role.
Company values/themes: {', '.join(values) if values else 'teamwork, innovation, ownership'}

Use the STAR format. Return ONLY a JSON array:
[
  {{
    "question": "Tell me about a time you had to handle a difficult stakeholder",
    "category": "behavioral",
    "difficulty": "medium",
    "suggested_answer": "STAR format answer template: Situation - ..., Task - ..., Action - ..., Result - ...",
    "tips": ["Be specific", "Focus on your actions not the team's"]
  }}
]"""
        msg = await client.messages.create(
            model=MODEL_NAME, max_tokens=2500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw   = msg.content[0].text
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        return json.loads(match.group()) if match else []

    return json.dumps(asyncio.get_event_loop().run_until_complete(_generate()))


TOOLS = [research_company, generate_technical_questions, generate_behavioral_questions]


async def build_graph() -> Any:
    llm = ChatAnthropic(
        model=MODEL_NAME,
        anthropic_api_key=ANTHROPIC_API_KEY,
        max_tokens=4096,
    ).bind_tools(TOOLS)

    def agent_node(state: InterviewPrepState) -> dict:
        return {"messages": [llm.invoke(state["messages"])]}

    def extract_prep(state: InterviewPrepState) -> dict:
        for msg in reversed(state["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                try:
                    match = re.search(r"\{.*\}", msg.content, re.DOTALL)
                    if match:
                        data = json.loads(match.group())
                        if "technical_questions" in data or "behavioral_questions" in data:
                            return {"interview_prep": data}
                except Exception:
                    pass
        return {"interview_prep": {}}

    graph = StateGraph(InterviewPrepState)
    graph.add_node("agent",        agent_node)
    graph.add_node("tools",        ToolNode(TOOLS))
    graph.add_node("extract_prep", extract_prep)

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: "extract_prep"})
    graph.add_edge("tools", "agent")
    graph.add_edge("extract_prep", END)

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

    skills_json = json.dumps(job.get("skills_required", []))

    prompt = f"""You are an Interview Prep Agent. Prepare this candidate thoroughly for their interview.

CANDIDATE: {profile.get('name')}
JOB: {job.get('title')} at {job.get('company')} ({job.get('location')})
SESSION ID: {session_id}

STEPS:
1. research_company("{job.get('company')}", "{job.get('title')}")
2. generate_technical_questions("{job.get('title')}", {skills_json}, "mixed")
3. generate_behavioral_questions("{job.get('title')}", "[]")

After all tool calls, synthesise into a comprehensive InterviewPrep and output ONLY this JSON:
{{
  "job_id": "{job.get('id', '')}",
  "company_insights": "2-3 paragraph company research summary",
  "technical_questions": [... from tool output ...],
  "behavioral_questions": [... from tool output ...],
  "questions_to_ask": [
    "What does success look like in the first 90 days?",
    "What are the biggest challenges the team is facing?",
    "How is performance reviewed?",
    "What is the team composition and collaboration style?",
    "What growth opportunities exist for this role?"
  ],
  "red_flags": ["High turnover mentioned in Glassdoor reviews"],
  "salary_negotiation": "Research shows market rate is $X-$Y. Wait for their first offer..."
}}

Start the preparation now."""

    graph = await build_graph()
    final_state = await graph.ainvoke({
        "messages":       [HumanMessage(content=prompt)],
        "profile":        profile,
        "job":            job,
        "session_id":     session_id,
        "interview_prep": {},
    })

    interview_prep = final_state.get("interview_prep", {})

    task.status    = TaskStatus(state=TaskState.COMPLETED)
    task.artifacts = [data_artifact({
        "interview_prep": interview_prep,
        "session_id":     session_id,
        "job_id":         job.get("id", ""),
    }, name="interview_prep")]
    return task

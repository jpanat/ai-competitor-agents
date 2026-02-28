"""
Orchestrator – A2A HTTP Server + REST API
==========================================
This is the primary user-facing entry point.

Endpoints:
  POST /run          – Start the full job-matching pipeline (REST convenience)
  POST /tasks/send   – A2A protocol task submission
  GET  /tasks/{id}   – A2A protocol task polling
  GET  /.well-known/agent.json – Agent discovery card

Example request to /run:
  {
    "linkedin_url": "https://linkedin.com/in/johndoe",
    "resume_text": "...",
    "desired_roles": ["Software Engineer", "Backend Engineer"],
    "locations": ["San Francisco", "remote"],
    "run_job_search": true,
    "run_resume_tailor": true,
    "run_cover_letter": true,
    "run_gap_analysis": true,
    "run_interview_prep": true
  }
"""

from __future__ import annotations

import os
import sys
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from job_matcher.shared.a2a_protocol import make_a2a_router, A2AClient
from job_matcher.shared.config import ORCHESTRATOR_PORT, AGENT_URLS
from job_matcher.shared.models import AgentCard, AgentSkill, PipelineRequest
from .agent import handle_task, build_graph


AGENT_CARD = AgentCard(
    name="Job Matcher Orchestrator",
    description=(
        "Master orchestrator for the AI Job Matching Pipeline. "
        "Coordinates profile parsing, job discovery, matching, resume tailoring, "
        "cover letter generation, gap analysis, and interview preparation."
    ),
    url=f"http://localhost:{ORCHESTRATOR_PORT}",
    version="1.0.0",
    capabilities={"streaming": False, "async": True, "pipeline": True},
    skills=[
        AgentSkill(id="full_pipeline",   name="Full Job Matching Pipeline",
                   description="End-to-end: profile → jobs → match → resume → cover letter → gaps → interview"),
        AgentSkill(id="job_search_only", name="Job Search Only",
                   description="Parse profile and search for matching jobs"),
        AgentSkill(id="docs_only",       name="Document Generation Only",
                   description="Generate tailored resume, cover letter for a specific job"),
    ],
)


app = FastAPI(
    title="AI Job Matcher – Orchestrator",
    description="Multi-agent job matching pipeline powered by LangGraph + A2A + MCP",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach A2A endpoints
app.include_router(make_a2a_router(AGENT_CARD, handle_task))


# ─── REST convenience endpoint ────────────────────────────────────────────────

@app.post("/run", summary="Run the full job-matching pipeline")
async def run_pipeline(request: PipelineRequest):
    """
    Convenience REST endpoint. Submits a pipeline request and waits for
    completion (synchronous for simplicity; use /tasks/send for async).
    """
    session_id = str(uuid.uuid4())
    request_data = request.model_dump()
    request_data["session_id"] = session_id

    from job_matcher.shared.models import A2AMessage, A2ATask
    from job_matcher.shared.a2a_protocol import data_artifact

    task = A2ATask(
        message=A2AMessage(
            role="user",
            parts=[{"type": "data", "data": request_data}],
        )
    )
    result_task = await handle_task(task)

    # Extract result from first artifact
    for artifact in result_task.artifacts:
        for part in artifact.parts:
            if part.get("type") == "data":
                return part["data"]

    return {"session_id": session_id, "status": result_task.status.state, "errors": []}


@app.get("/health")
async def health():
    """Health check for all downstream agents."""
    statuses: dict[str, str] = {}
    import httpx
    async with httpx.AsyncClient(timeout=3) as client:
        for name, url in AGENT_URLS.items():
            try:
                resp = await client.get(f"{url}/health")
                statuses[name] = "ok" if resp.status_code == 200 else "degraded"
            except Exception:
                statuses[name] = "unavailable"
    return {"status": "ok", "agents": statuses}


@app.get("/agents", summary="List all registered agents and their capabilities")
async def list_agents():
    """Fetch agent cards from all downstream agents."""
    cards: dict[str, dict] = {}
    import httpx
    async with httpx.AsyncClient(timeout=5) as client:
        for name, url in AGENT_URLS.items():
            try:
                resp = await client.get(f"{url}/.well-known/agent.json")
                cards[name] = resp.json()
            except Exception:
                cards[name] = {"error": "unreachable"}
    return cards


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=ORCHESTRATOR_PORT)

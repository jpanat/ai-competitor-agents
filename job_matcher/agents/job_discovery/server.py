"""Job Discovery Agent – A2A HTTP Server"""

from __future__ import annotations

import os
import sys

from fastapi import FastAPI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from job_matcher.shared.a2a_protocol import make_a2a_router
from job_matcher.shared.config import JOB_DISCOVERY_PORT
from job_matcher.shared.models import AgentCard, AgentSkill
from .agent import handle_task

AGENT_CARD = AgentCard(
    name="Job Discovery Agent",
    description=(
        "Searches LinkedIn Jobs, Indeed, and Glassdoor to find relevant open "
        "positions based on a candidate's profile and preferences."
    ),
    url=f"http://localhost:{JOB_DISCOVERY_PORT}",
    skills=[
        AgentSkill(id="search_all_boards", name="Multi-board Job Search",
                   description="Search LinkedIn, Indeed, and Glassdoor simultaneously"),
        AgentSkill(id="filter_jobs", name="Job Filtering",
                   description="Filter and deduplicate job results by relevance"),
    ],
)

app = FastAPI(title="Job Discovery Agent (A2A)")
app.include_router(make_a2a_router(AGENT_CARD, handle_task))


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "job-discovery"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=JOB_DISCOVERY_PORT)

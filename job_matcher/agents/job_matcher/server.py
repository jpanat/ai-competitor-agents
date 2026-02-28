"""Job Matcher Agent – A2A HTTP Server"""

from __future__ import annotations

import os
import sys

from fastapi import FastAPI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from job_matcher.shared.a2a_protocol import make_a2a_router
from job_matcher.shared.config import JOB_MATCHER_PORT
from job_matcher.shared.models import AgentCard, AgentSkill
from .agent import handle_task

AGENT_CARD = AgentCard(
    name="Job Matcher Agent",
    description=(
        "Scores and ranks job postings against a candidate profile across "
        "skill, experience, and culture dimensions. Returns top 10 matches."
    ),
    url=f"http://localhost:{JOB_MATCHER_PORT}",
    skills=[
        AgentSkill(id="score_jobs",  name="Job Scoring",  description="Multi-dimensional job-profile scoring"),
        AgentSkill(id="rank_jobs",   name="Job Ranking",  description="Rank and filter job matches"),
    ],
)

app = FastAPI(title="Job Matcher Agent (A2A)")
app.include_router(make_a2a_router(AGENT_CARD, handle_task))


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "job-matcher"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=JOB_MATCHER_PORT)

"""Gap Analysis Agent – A2A HTTP Server"""

from __future__ import annotations

import os
import sys

from fastapi import FastAPI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from job_matcher.shared.a2a_protocol import make_a2a_router
from job_matcher.shared.config import GAP_ANALYSIS_PORT
from job_matcher.shared.models import AgentCard, AgentSkill
from .agent import handle_task

AGENT_CARD = AgentCard(
    name="Gap Analysis Agent",
    description=(
        "Identifies skill, experience, and education gaps between a candidate "
        "and a job posting. Provides prioritised action plans with learning resources."
    ),
    url=f"http://localhost:{GAP_ANALYSIS_PORT}",
    skills=[
        AgentSkill(id="skill_gap",    name="Skill Gap Analysis",    description="Identify missing skills"),
        AgentSkill(id="learn_resources", name="Learning Resources", description="Find courses for skill gaps"),
        AgentSkill(id="action_plan",  name="Action Plan",           description="Build prioritised improvement plan"),
    ],
)

app = FastAPI(title="Gap Analysis Agent (A2A)")
app.include_router(make_a2a_router(AGENT_CARD, handle_task))


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "gap-analysis"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=GAP_ANALYSIS_PORT)

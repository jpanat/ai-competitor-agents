"""Resume Tailor Agent – A2A HTTP Server"""

from __future__ import annotations

import os
import sys

from fastapi import FastAPI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from job_matcher.shared.a2a_protocol import make_a2a_router
from job_matcher.shared.config import RESUME_TAILOR_PORT
from job_matcher.shared.models import AgentCard, AgentSkill
from .agent import handle_task

AGENT_CARD = AgentCard(
    name="Resume Tailor Agent",
    description="Rewrites a resume to maximally target a specific job posting, adding ATS keywords.",
    url=f"http://localhost:{RESUME_TAILOR_PORT}",
    skills=[
        AgentSkill(id="tailor_resume",    name="Resume Tailoring",    description="Rewrite resume for a specific job"),
        AgentSkill(id="ats_score",        name="ATS Scoring",         description="Estimate ATS pass-rate"),
    ],
)

app = FastAPI(title="Resume Tailor Agent (A2A)")
app.include_router(make_a2a_router(AGENT_CARD, handle_task))


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "resume-tailor"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=RESUME_TAILOR_PORT)

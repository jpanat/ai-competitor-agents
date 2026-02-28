"""Interview Prep Agent – A2A HTTP Server"""

from __future__ import annotations

import os
import sys

from fastapi import FastAPI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from job_matcher.shared.a2a_protocol import make_a2a_router
from job_matcher.shared.config import INTERVIEW_PREP_PORT
from job_matcher.shared.models import AgentCard, AgentSkill
from .agent import handle_task

AGENT_CARD = AgentCard(
    name="Interview Prep Agent",
    description=(
        "Prepares candidates for job interviews: company research, technical & "
        "behavioural questions with model answers, questions to ask, and salary tips."
    ),
    url=f"http://localhost:{INTERVIEW_PREP_PORT}",
    skills=[
        AgentSkill(id="company_research",    name="Company Research",          description="Research culture, news, and interview style"),
        AgentSkill(id="technical_questions", name="Technical Q&A Generation",  description="Role-specific technical questions"),
        AgentSkill(id="behavioral_questions", name="Behavioural Q&A (STAR)",   description="STAR-format behavioural questions"),
        AgentSkill(id="salary_negotiation",  name="Salary Negotiation Tips",   description="Market rate and negotiation strategy"),
    ],
)

app = FastAPI(title="Interview Prep Agent (A2A)")
app.include_router(make_a2a_router(AGENT_CARD, handle_task))


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "interview-prep"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=INTERVIEW_PREP_PORT)

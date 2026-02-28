"""
Profile Parser Agent – A2A HTTP Server
Exposes the LangGraph profile parser agent via the A2A protocol.
"""

from __future__ import annotations

import os
import sys

from fastapi import FastAPI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from job_matcher.shared.a2a_protocol import make_a2a_router
from job_matcher.shared.config import PROFILE_PARSER_PORT
from job_matcher.shared.models import AgentCard, AgentSkill
from .agent import handle_task

AGENT_CARD = AgentCard(
    name="Profile Parser Agent",
    description=(
        "Parses a LinkedIn profile URL and/or resume text into a structured "
        "UserProfile. Uses AI to extract skills, experience, and education."
    ),
    url=f"http://localhost:{PROFILE_PARSER_PORT}",
    version="1.0.0",
    capabilities={"streaming": False, "async": True},
    skills=[
        AgentSkill(
            id="parse_linkedin",
            name="Parse LinkedIn Profile",
            description="Scrape and structure a LinkedIn profile",
        ),
        AgentSkill(
            id="parse_resume",
            name="Parse Resume",
            description="Extract structured data from resume text",
        ),
        AgentSkill(
            id="merge_sources",
            name="Merge Profile Sources",
            description="Merge LinkedIn + resume into unified profile",
        ),
    ],
)

app = FastAPI(title="Profile Parser Agent (A2A)")
app.include_router(make_a2a_router(AGENT_CARD, handle_task))


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "profile-parser"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PROFILE_PARSER_PORT)

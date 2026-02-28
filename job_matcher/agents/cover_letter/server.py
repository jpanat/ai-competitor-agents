"""Cover Letter Agent – A2A HTTP Server"""

from __future__ import annotations

import os
import sys

from fastapi import FastAPI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from job_matcher.shared.a2a_protocol import make_a2a_router
from job_matcher.shared.config import COVER_LETTER_PORT
from job_matcher.shared.models import AgentCard, AgentSkill
from .agent import handle_task

AGENT_CARD = AgentCard(
    name="Cover Letter Agent",
    description="Generates a personalised, compelling cover letter tailored to a specific job posting.",
    url=f"http://localhost:{COVER_LETTER_PORT}",
    skills=[
        AgentSkill(id="write_cover_letter", name="Cover Letter Writing",
                   description="Generate a tone-appropriate cover letter"),
    ],
)

app = FastAPI(title="Cover Letter Agent (A2A)")
app.include_router(make_a2a_router(AGENT_CARD, handle_task))


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "cover-letter"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=COVER_LETTER_PORT)

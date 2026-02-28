"""
Document MCP Server
===================
Tools exposed:
  • generate_tailored_resume   – rewrite a resume targeting a specific job
  • generate_cover_letter      – draft a personalised cover letter
  • score_resume_ats           – estimate ATS pass-rate against a job description
  • format_markdown_to_text    – clean markdown → plain text (for ATS systems)

Runs over SSE on DOCUMENT_MCP_PORT (default 9003).
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from fastapi import FastAPI, Request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from job_matcher.shared.config import ANTHROPIC_API_KEY, MODEL_NAME, DOCUMENT_MCP_PORT

server = Server("document-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="generate_tailored_resume",
            description=(
                "Rewrite a user's resume to optimally target a specific job posting. "
                "Emphasises relevant skills, adjusts wording for ATS keywords, and "
                "prioritises the most impactful experience."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "profile":    {"type": "object", "description": "UserProfile JSON"},
                    "job":        {"type": "object", "description": "JobPosting JSON"},
                    "original_resume_text": {
                        "type": "string",
                        "description": "Raw original resume text (optional, for tone matching)",
                    },
                },
                "required": ["profile", "job"],
            },
        ),
        Tool(
            name="generate_cover_letter",
            description="Write a compelling, personalised cover letter for a job application.",
            inputSchema={
                "type": "object",
                "properties": {
                    "profile":    {"type": "object", "description": "UserProfile JSON"},
                    "job":        {"type": "object", "description": "JobPosting JSON"},
                    "tone":       {
                        "type": "string",
                        "enum": ["professional", "enthusiastic", "concise"],
                        "default": "professional",
                    },
                    "word_limit": {"type": "integer", "default": 350},
                },
                "required": ["profile", "job"],
            },
        ),
        Tool(
            name="score_resume_ats",
            description=(
                "Estimate what percentage of ATS (Applicant Tracking System) requirements "
                "the resume satisfies for a given job. Returns a 0-100 score and missing keywords."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "resume_text": {"type": "string", "description": "Resume content"},
                    "job":         {"type": "object", "description": "JobPosting JSON"},
                },
                "required": ["resume_text", "job"],
            },
        ),
        Tool(
            name="format_markdown_to_text",
            description="Strip markdown formatting and return clean plain text suitable for ATS.",
            inputSchema={
                "type": "object",
                "properties": {
                    "markdown": {"type": "string"}
                },
                "required": ["markdown"],
            },
        ),
    ]


async def _llm(prompt: str, max_tokens: int = 3000) -> str:
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    msg = await client.messages.create(
        model=MODEL_NAME,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:

    if name == "generate_tailored_resume":
        profile = arguments["profile"]
        job     = arguments["job"]
        original = arguments.get("original_resume_text", "")

        prompt = f"""You are an expert resume writer and career coach.
Rewrite the following candidate's resume to maximally target the job posting below.

== CANDIDATE PROFILE ==
{json.dumps(profile, indent=2)}

== ORIGINAL RESUME TEXT (for tone reference) ==
{original[:3000] if original else "Not provided"}

== TARGET JOB POSTING ==
{json.dumps(job, indent=2)}

Instructions:
1. Use the EXACT keywords from the job description (for ATS systems)
2. Lead with a strong professional summary tailored to this role
3. Quantify achievements wherever possible
4. Reorder bullets to prioritise relevance to this job
5. Keep it to 1-2 pages worth of content
6. Use clean markdown formatting (##, **bold**, bullet points)

Return a JSON object:
{{
  "content": "Full resume in clean markdown",
  "key_changes": ["Change 1", "Change 2"],
  "keywords_added": ["keyword1", "keyword2"]
}}"""

        raw = await _llm(prompt, max_tokens=4096)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(match.group()) if match else {"content": raw, "key_changes": [], "keywords_added": []}
        result["job_id"] = job.get("id", "")
        return [TextContent(type="text", text=json.dumps(result))]

    elif name == "generate_cover_letter":
        profile  = arguments["profile"]
        job      = arguments["job"]
        tone     = arguments.get("tone", "professional")
        limit    = arguments.get("word_limit", 350)

        prompt = f"""You are a professional cover letter writer.
Write a compelling cover letter for the candidate below applying to this job.

== CANDIDATE PROFILE ==
{json.dumps(profile, indent=2)}

== JOB POSTING ==
{json.dumps(job, indent=2)}

Tone: {tone}
Word limit: ~{limit} words

Structure:
1. Opening hook – show excitement and fit (2-3 sentences)
2. Why you're a strong match – 2-3 specific skill/achievement examples
3. Why this company – show research, genuine interest
4. Call to action closing

Return a JSON object:
{{
  "content": "Full cover letter as plain text (no markdown headers)",
  "tone": "{tone}",
  "word_count": <number>
}}"""

        raw = await _llm(prompt)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(match.group()) if match else {"content": raw, "tone": tone, "word_count": 0}
        result["job_id"] = job.get("id", "")
        if not result.get("word_count"):
            result["word_count"] = len(result.get("content", "").split())
        return [TextContent(type="text", text=json.dumps(result))]

    elif name == "score_resume_ats":
        resume_text = arguments["resume_text"]
        job         = arguments["job"]

        prompt = f"""You are an ATS (Applicant Tracking System) expert.
Score how well the resume below matches the job posting.

== RESUME ==
{resume_text[:4000]}

== JOB POSTING ==
{json.dumps(job, indent=2)[:2000]}

Return a JSON object:
{{
  "ats_score": 78.5,
  "matched_keywords": ["Python", "AWS"],
  "missing_keywords": ["Kubernetes", "Terraform"],
  "score_breakdown": {{
    "keyword_match": 80,
    "experience_match": 75,
    "education_match": 90,
    "skills_match": 70
  }},
  "recommendations": ["Add Kubernetes to skills section", "Mention CI/CD experience"]
}}"""

        raw = await _llm(prompt)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(match.group()) if match else {"ats_score": 0}
        return [TextContent(type="text", text=json.dumps(result))]

    elif name == "format_markdown_to_text":
        md = arguments["markdown"]
        # Strip common markdown
        text = re.sub(r"#{1,6}\s+", "", md)
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*",   r"\1", text)
        text = re.sub(r"`(.+?)`",     r"\1", text)
        text = re.sub(r"^\s*[-*]\s+", "• ", text, flags=re.MULTILINE)
        return [TextContent(type="text", text=json.dumps({"text": text}))]

    return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


# ─── FastAPI + SSE ────────────────────────────────────────────────────────────

app = FastAPI(title="Document MCP Server")
sse_transport = SseServerTransport("/messages/")


@app.get("/sse")
async def sse_endpoint(request: Request):
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


@app.post("/messages/")
async def handle_messages(request: Request):
    await sse_transport.handle_post_message(request.scope, request.receive, request._send)


@app.get("/health")
async def health():
    return {"status": "ok", "server": "document-mcp"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=DOCUMENT_MCP_PORT)

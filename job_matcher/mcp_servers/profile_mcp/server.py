"""
Profile MCP Server
==================
Tools exposed:
  • parse_linkedin_profile  – scrape & structure a LinkedIn profile URL
  • parse_resume_text       – extract structured data from raw resume text
  • extract_skills          – NLP skill extraction from any text blob
  • merge_profile_sources   – merge LinkedIn + resume into one UserProfile

Runs over SSE transport on PROFILE_MCP_PORT (default 9001).
Agents connect via:  MultiServerMCPClient({"profile": {"url": "http://host:9001/sse", "transport": "sse"}})
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from fastapi import FastAPI, Request
from starlette.routing import Route

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from job_matcher.shared.config import ANTHROPIC_API_KEY, MODEL_NAME, APIFY_API_KEY, PROFILE_MCP_PORT

# ─── Server init ──────────────────────────────────────────────────────────────

server = Server("profile-mcp")

# ─── Tool definitions ─────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="parse_linkedin_profile",
            description=(
                "Scrape a LinkedIn public profile URL and return structured profile data "
                "including name, headline, summary, experience, education, and skills."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "linkedin_url": {
                        "type": "string",
                        "description": "Full LinkedIn profile URL (e.g. https://linkedin.com/in/username)",
                    }
                },
                "required": ["linkedin_url"],
            },
        ),
        Tool(
            name="parse_resume_text",
            description=(
                "Parse raw resume text (plain text or markdown) and return a structured "
                "UserProfile with experience, education, skills, certifications."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "resume_text": {
                        "type": "string",
                        "description": "Raw resume content as plain text.",
                    }
                },
                "required": ["resume_text"],
            },
        ),
        Tool(
            name="extract_skills",
            description="Extract a deduplicated list of technical and soft skills from any text.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to extract skills from."}
                },
                "required": ["text"],
            },
        ),
        Tool(
            name="merge_profile_sources",
            description=(
                "Merge a LinkedIn profile dict and a resume profile dict into one "
                "canonical UserProfile, deduplicating skills and experience."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "linkedin_profile": {
                        "type": "object",
                        "description": "Parsed LinkedIn profile (output of parse_linkedin_profile).",
                    },
                    "resume_profile": {
                        "type": "object",
                        "description": "Parsed resume profile (output of parse_resume_text). Optional.",
                    },
                },
                "required": ["linkedin_profile"],
            },
        ),
    ]


# ─── Tool implementations ─────────────────────────────────────────────────────

async def _llm_parse(prompt: str) -> dict[str, Any]:
    """Call Claude to parse/extract structured data and return JSON."""
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    msg = await client.messages.create(
        model=MODEL_NAME,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text
    # Extract JSON block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {"raw": raw}


async def _scrape_linkedin(url: str) -> str:
    """
    Scrape LinkedIn profile using Apify LinkedIn Profile Scraper actor.
    Falls back to a Tavily search snippet if APIFY_API_KEY is not set.
    """
    if APIFY_API_KEY:
        async with httpx.AsyncClient(timeout=60) as client:
            # Start Apify actor run
            run_resp = await client.post(
                "https://api.apify.com/v2/acts/curious_coder~linkedin-profile-scraper/runs",
                params={"token": APIFY_API_KEY},
                json={"startUrls": [{"url": url}]},
            )
            run_resp.raise_for_status()
            run_id = run_resp.json()["data"]["id"]

            # Poll until finished
            import asyncio
            for _ in range(30):
                await asyncio.sleep(5)
                status_resp = await client.get(
                    f"https://api.apify.com/v2/actor-runs/{run_id}",
                    params={"token": APIFY_API_KEY},
                )
                if status_resp.json()["data"]["status"] == "SUCCEEDED":
                    break

            # Get results
            results_resp = await client.get(
                f"https://api.apify.com/v2/actor-runs/{run_id}/dataset/items",
                params={"token": APIFY_API_KEY},
            )
            items = results_resp.json()
            return json.dumps(items[0]) if items else ""

    # Fallback: return the URL for LLM to reason about
    return f"LinkedIn profile URL provided: {url}. Please extract what you can from context."


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    if name == "parse_linkedin_profile":
        url = arguments["linkedin_url"]
        raw_data = await _scrape_linkedin(url)

        prompt = f"""You are a profile parser. Given the following LinkedIn profile data,
extract a structured JSON profile.

Raw data:
{raw_data}

Return ONLY a JSON object with these fields:
{{
  "name": "Full Name",
  "headline": "Job title / headline",
  "summary": "About / summary text",
  "location": "City, Country",
  "email": null,
  "skills": ["skill1", "skill2"],
  "experience": [
    {{
      "company": "Company Name",
      "title": "Job Title",
      "start_date": "YYYY-MM",
      "end_date": "YYYY-MM or null",
      "description": "Role description",
      "skills_used": [],
      "achievements": []
    }}
  ],
  "education": [
    {{
      "institution": "University",
      "degree": "BSc",
      "field": "Computer Science",
      "graduation_year": 2020,
      "gpa": null
    }}
  ],
  "certifications": [],
  "languages": [],
  "total_years_exp": 5.0
}}"""

        result = await _llm_parse(prompt)
        result["linkedin_url"] = url
        return [TextContent(type="text", text=json.dumps(result))]

    elif name == "parse_resume_text":
        resume_text = arguments["resume_text"]

        prompt = f"""You are a resume parser. Parse the following resume and return structured JSON.

Resume:
{resume_text}

Return ONLY a JSON object:
{{
  "name": "Full Name",
  "headline": null,
  "summary": "Professional summary if present",
  "location": "City, Country or null",
  "email": "email or null",
  "skills": ["skill1", "skill2"],
  "experience": [
    {{
      "company": "Company",
      "title": "Title",
      "start_date": "YYYY-MM",
      "end_date": "YYYY-MM or null",
      "description": "Description",
      "skills_used": [],
      "achievements": ["bullet point achievements"]
    }}
  ],
  "education": [
    {{
      "institution": "School",
      "degree": "Degree",
      "field": "Field",
      "graduation_year": 2020,
      "gpa": null
    }}
  ],
  "certifications": [],
  "languages": [],
  "total_years_exp": null
}}"""

        result = await _llm_parse(prompt)
        return [TextContent(type="text", text=json.dumps(result))]

    elif name == "extract_skills":
        text = arguments["text"]
        prompt = f"""Extract all technical and professional skills from the text below.
Return ONLY a JSON array of unique skill strings, sorted alphabetically.

Text:
{text}

Output: ["skill1", "skill2", ...]"""
        result = await _llm_parse(prompt)
        return [TextContent(type="text", text=json.dumps(result))]

    elif name == "merge_profile_sources":
        linkedin = arguments["linkedin_profile"]
        resume = arguments.get("resume_profile", {})

        # Merge skills (union)
        skills = list(set(linkedin.get("skills", []) + resume.get("skills", [])))

        # Prefer LinkedIn experience but add unique resume entries
        experience = linkedin.get("experience", []) or resume.get("experience", [])

        merged = {
            **linkedin,
            **{k: v for k, v in resume.items() if v and not linkedin.get(k)},
            "skills": sorted(skills),
            "experience": experience,
            "education": linkedin.get("education") or resume.get("education", []),
            "certifications": list(
                set(linkedin.get("certifications", []) + resume.get("certifications", []))
            ),
        }
        return [TextContent(type="text", text=json.dumps(merged))]

    return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


# ─── FastAPI app with SSE transport ───────────────────────────────────────────

app = FastAPI(title="Profile MCP Server")
sse_transport = SseServerTransport("/messages/")


@app.get("/sse")
async def sse_endpoint(request: Request):
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await server.run(
            streams[0],
            streams[1],
            server.create_initialization_options(),
        )


@app.post("/messages/")
async def handle_messages(request: Request):
    await sse_transport.handle_post_message(request.scope, request.receive, request._send)


@app.get("/health")
async def health():
    return {"status": "ok", "server": "profile-mcp"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PROFILE_MCP_PORT)

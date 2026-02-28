"""
Job Board MCP Server
====================
Tools exposed:
  • search_linkedin_jobs   – search LinkedIn Jobs via Tavily / Apify
  • search_indeed_jobs     – search Indeed via Tavily web search
  • search_glassdoor_jobs  – search Glassdoor via Tavily web search
  • get_job_details        – fetch full job description for a URL
  • search_all_boards      – fan-out search across all three boards

Runs over SSE transport on JOB_BOARD_MCP_PORT (default 9002).
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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from job_matcher.shared.config import (
    ANTHROPIC_API_KEY,
    MODEL_NAME,
    TAVILY_API_KEY,
    APIFY_API_KEY,
    JOB_BOARD_MCP_PORT,
)

server = Server("job-board-mcp")


# ─── Tool definitions ─────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[Tool]:
    search_schema = {
        "type": "object",
        "properties": {
            "query":    {"type": "string", "description": "Job title or keywords"},
            "location": {"type": "string", "description": "City, state, or 'remote'"},
            "max_results": {"type": "integer", "default": 10},
            "experience_level": {
                "type": "string",
                "enum": ["entry", "mid", "senior", "executive"],
                "description": "Filter by seniority",
            },
            "job_type": {
                "type": "string",
                "enum": ["full-time", "part-time", "contract", "internship"],
            },
        },
        "required": ["query"],
    }

    return [
        Tool(name="search_linkedin_jobs",  description="Search LinkedIn Jobs.",  inputSchema=search_schema),
        Tool(name="search_indeed_jobs",    description="Search Indeed Jobs.",    inputSchema=search_schema),
        Tool(name="search_glassdoor_jobs", description="Search Glassdoor Jobs.", inputSchema=search_schema),
        Tool(
            name="get_job_details",
            description="Fetch full job description and requirements from a job posting URL.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Job posting URL"},
                    "source": {
                        "type": "string",
                        "enum": ["linkedin", "indeed", "glassdoor", "other"],
                    },
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="search_all_boards",
            description="Fan-out search across LinkedIn, Indeed, and Glassdoor simultaneously.",
            inputSchema=search_schema,
        ),
    ]


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _tavily_search(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    """Use Tavily to perform a web search and return results."""
    if not TAVILY_API_KEY:
        return []
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "max_results": max_results,
                "search_depth": "advanced",
            },
        )
        resp.raise_for_status()
        return resp.json().get("results", [])


async def _llm_extract_jobs(raw_results: list[dict], source: str) -> list[dict[str, Any]]:
    """Use Claude to extract structured job postings from raw search results."""
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"""You are a job data extractor. Given raw search results from {source},
extract structured job postings.

Raw results:
{json.dumps(raw_results, indent=2)[:8000]}

Return ONLY a JSON array:
[
  {{
    "title": "Job Title",
    "company": "Company Name",
    "location": "City, State / Remote",
    "description": "Summary of the role (2-3 sentences)",
    "requirements": ["req1", "req2"],
    "skills_required": ["Python", "AWS"],
    "salary_range": {{"min": 100000, "max": 150000}} or null,
    "experience_level": "mid",
    "job_type": "full-time",
    "remote_ok": true,
    "apply_url": "https://...",
    "posted_date": "YYYY-MM-DD or null",
    "source": "{source}",
    "company_size": "startup/mid/enterprise or null",
    "industry": "Technology"
  }}
]

Extract up to 10 unique, real job postings. If data is missing use null."""

    msg = await client.messages.create(
        model=MODEL_NAME,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return []


async def _search_board(query: str, location: str, source: str, max_results: int) -> list[dict]:
    site_map = {
        "linkedin":  "site:linkedin.com/jobs",
        "indeed":    "site:indeed.com",
        "glassdoor": "site:glassdoor.com/job-listing",
    }
    site_filter = site_map.get(source, "")
    full_query = f"{query} {location} {site_filter}".strip()

    raw = await _tavily_search(full_query, max_results)
    jobs = await _llm_extract_jobs(raw, source)
    # Ensure source field is set
    for job in jobs:
        job["source"] = source
    return jobs


# ─── Tool handler ─────────────────────────────────────────────────────────────

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    query    = arguments.get("query", "")
    location = arguments.get("location", "")
    max_res  = arguments.get("max_results", 10)

    if name == "search_linkedin_jobs":
        jobs = await _search_board(query, location, "linkedin", max_res)
        return [TextContent(type="text", text=json.dumps(jobs))]

    elif name == "search_indeed_jobs":
        jobs = await _search_board(query, location, "indeed", max_res)
        return [TextContent(type="text", text=json.dumps(jobs))]

    elif name == "search_glassdoor_jobs":
        jobs = await _search_board(query, location, "glassdoor", max_res)
        return [TextContent(type="text", text=json.dumps(jobs))]

    elif name == "search_all_boards":
        import asyncio
        results = await asyncio.gather(
            _search_board(query, location, "linkedin",  max_res),
            _search_board(query, location, "indeed",    max_res),
            _search_board(query, location, "glassdoor", max_res),
        )
        all_jobs: list[dict] = []
        for board_results in results:
            all_jobs.extend(board_results)
        return [TextContent(type="text", text=json.dumps(all_jobs))]

    elif name == "get_job_details":
        url = arguments["url"]
        raw = await _tavily_search(f"job description {url}", max_results=3)
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        prompt = f"""Fetch and summarize the job posting at URL: {url}

Search context:
{json.dumps(raw, indent=2)[:4000]}

Return a JSON object with:
{{
  "title": "...",
  "company": "...",
  "location": "...",
  "description": "Full description",
  "requirements": ["..."],
  "skills_required": ["..."],
  "salary_range": null,
  "benefits": ["..."],
  "apply_url": "{url}"
}}"""
        msg = await client.messages.create(
            model=MODEL_NAME, max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = msg.content[0].text
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        result = json.loads(match.group()) if match else {"raw": raw_text}
        return [TextContent(type="text", text=json.dumps(result))]

    return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


# ─── FastAPI + SSE ────────────────────────────────────────────────────────────

app = FastAPI(title="Job Board MCP Server")
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
    return {"status": "ok", "server": "job-board-mcp"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=JOB_BOARD_MCP_PORT)

"""
Central configuration for all agents and MCP servers.
All ports, URLs, and environment variables are defined here.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── LLM ─────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "claude-sonnet-4-6")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))

# ─── Search APIs ─────────────────────────────────────────────────────────────
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")          # alternative search
APIFY_API_KEY = os.getenv("APIFY_API_KEY", "")            # for LinkedIn scraping

# ─── A2A Agent Ports ──────────────────────────────────────────────────────────
ORCHESTRATOR_PORT    = int(os.getenv("ORCHESTRATOR_PORT",    "8000"))
PROFILE_PARSER_PORT  = int(os.getenv("PROFILE_PARSER_PORT",  "8001"))
JOB_DISCOVERY_PORT   = int(os.getenv("JOB_DISCOVERY_PORT",   "8002"))
JOB_MATCHER_PORT     = int(os.getenv("JOB_MATCHER_PORT",     "8003"))
RESUME_TAILOR_PORT   = int(os.getenv("RESUME_TAILOR_PORT",   "8004"))
COVER_LETTER_PORT    = int(os.getenv("COVER_LETTER_PORT",    "8005"))
GAP_ANALYSIS_PORT    = int(os.getenv("GAP_ANALYSIS_PORT",    "8006"))
INTERVIEW_PREP_PORT  = int(os.getenv("INTERVIEW_PREP_PORT",  "8007"))

# ─── MCP Server Ports ─────────────────────────────────────────────────────────
PROFILE_MCP_PORT   = int(os.getenv("PROFILE_MCP_PORT",   "9001"))
JOB_BOARD_MCP_PORT = int(os.getenv("JOB_BOARD_MCP_PORT", "9002"))
DOCUMENT_MCP_PORT  = int(os.getenv("DOCUMENT_MCP_PORT",  "9003"))
MEMORY_MCP_PORT    = int(os.getenv("MEMORY_MCP_PORT",    "9004"))

# ─── Agent URLs (service-name based for Docker Compose) ──────────────────────
_host = os.getenv("AGENT_HOST", "localhost")

AGENT_URLS: dict[str, str] = {
    "profile_parser": f"http://{_host}:{PROFILE_PARSER_PORT}",
    "job_discovery":  f"http://{_host}:{JOB_DISCOVERY_PORT}",
    "job_matcher":    f"http://{_host}:{JOB_MATCHER_PORT}",
    "resume_tailor":  f"http://{_host}:{RESUME_TAILOR_PORT}",
    "cover_letter":   f"http://{_host}:{COVER_LETTER_PORT}",
    "gap_analysis":   f"http://{_host}:{GAP_ANALYSIS_PORT}",
    "interview_prep": f"http://{_host}:{INTERVIEW_PREP_PORT}",
}

# ─── MCP Server URLs ──────────────────────────────────────────────────────────
MCP_URLS: dict[str, str] = {
    "profile":   f"http://{_host}:{PROFILE_MCP_PORT}/sse",
    "job_board": f"http://{_host}:{JOB_BOARD_MCP_PORT}/sse",
    "document":  f"http://{_host}:{DOCUMENT_MCP_PORT}/sse",
    "memory":    f"http://{_host}:{MEMORY_MCP_PORT}/sse",
}

# ─── Redis (optional, for shared session state) ───────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

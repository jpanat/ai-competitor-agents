# AI Job Matcher – Multi-Agent Architecture

> **LangGraph agents · A2A Protocol · MCP Servers · Claude claude-sonnet-4-6**

A production-grade multi-agent system that takes a LinkedIn profile and/or resume,
discovers matching jobs across LinkedIn, Indeed, and Glassdoor, then produces a
tailored resume, cover letter, gap analysis, and interview prep kit — all
automatically.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          USER / CLIENT                                       │
│              POST http://localhost:8000/run  (REST or A2A)                  │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │  A2A Protocol
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR AGENT  :8000                                │
│                       (LangGraph StateGraph)                                 │
│                                                                              │
│  parse_profile → job_discovery → job_match → select_job                     │
│      → resume_tailor → cover_letter → gap_analysis → interview_prep         │
└──┬──────────┬────────────┬──────────┬──────────┬──────────┬────────────┬───┘
   │ A2A      │ A2A        │ A2A      │ A2A      │ A2A      │ A2A        │ A2A
   ▼          ▼            ▼          ▼          ▼          ▼            ▼
┌──────┐ ┌─────────┐ ┌──────────┐ ┌────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐
│Profil│ │  Job    │ │  Job     │ │Resume  │ │ Cover  │ │   Gap    │ │Interview │
│Parser│ │Discovery│ │ Matcher  │ │Tailor  │ │ Letter │ │ Analysis │ │  Prep    │
│:8001 │ │ :8002   │ │  :8003   │ │ :8004  │ │ :8005  │ │  :8006   │ │  :8007   │
└──┬───┘ └────┬────┘ └──────────┘ └───┬────┘ └───┬────┘ └────┬─────┘ └────┬─────┘
   │ MCP      │ MCP                   │ MCP       │ MCP       │            │
   ▼          ▼                       ▼           ▼           │            │
┌──────────────────────────────────────────────────────────────────────────────┐
│                           MCP SERVERS (SSE transport)                        │
│                                                                              │
│  ┌─────────────┐  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐  │
│  │ Profile MCP │  │ Job Board MCP │  │ Document MCP  │  │  Memory MCP  │  │
│  │    :9001    │  │    :9002      │  │    :9003      │  │    :9004     │  │
│  │             │  │               │  │               │  │              │  │
│  │ • parse_    │  │ • search_     │  │ • generate_   │  │ • store      │  │
│  │   linkedin  │  │   linkedin_   │  │   tailored_   │  │ • retrieve   │  │
│  │ • parse_    │  │   jobs        │  │   resume      │  │ • store_jobs │  │
│  │   resume    │  │ • search_     │  │ • generate_   │  │ • list_keys  │  │
│  │ • extract_  │  │   indeed_jobs │  │   cover_      │  │              │  │
│  │   skills    │  │ • search_     │  │   letter      │  │              │  │
│  │ • merge_    │  │   glassdoor   │  │ • score_      │  │              │  │
│  │   sources   │  │ • search_all_ │  │   resume_ats  │  │              │  │
│  │             │  │   boards      │  │               │  │              │  │
│  └─────────────┘  └───────────────┘  └───────────────┘  └──────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Agents

| Agent | Port | LangGraph Pattern | MCP Servers Used | Purpose |
|-------|------|-------------------|-----------------|---------|
| **Orchestrator** | 8000 | Sequential StateGraph | — (calls agents via A2A) | Pipeline coordinator |
| **Profile Parser** | 8001 | ReAct | profile-mcp, memory-mcp | Parse LinkedIn + resume |
| **Job Discovery** | 8002 | ReAct | job-board-mcp, memory-mcp | Search LinkedIn, Indeed, Glassdoor |
| **Job Matcher** | 8003 | ReAct + local tools | — | Score & rank job-profile fit |
| **Resume Tailor** | 8004 | ReAct | document-mcp, memory-mcp | ATS-optimised resume rewrite |
| **Cover Letter** | 8005 | ReAct | document-mcp, memory-mcp | Personalised cover letter |
| **Gap Analysis** | 8006 | ReAct + local tools | — | Skill gaps + learning resources |
| **Interview Prep** | 8007 | ReAct + local tools | — | Company research + Q&A |

---

## MCP Servers

| Server | Port | Tools |
|--------|------|-------|
| **profile-mcp** | 9001 | `parse_linkedin_profile`, `parse_resume_text`, `extract_skills`, `merge_profile_sources` |
| **job-board-mcp** | 9002 | `search_linkedin_jobs`, `search_indeed_jobs`, `search_glassdoor_jobs`, `search_all_boards`, `get_job_details` |
| **document-mcp** | 9003 | `generate_tailored_resume`, `generate_cover_letter`, `score_resume_ats`, `format_markdown_to_text` |
| **memory-mcp** | 9004 | `store`, `retrieve`, `list_keys`, `delete`, `store_jobs`, `retrieve_jobs` |

---

## A2A Protocol

Each agent exposes the [Google A2A](https://google.github.io/A2A/) protocol:

```
GET  /.well-known/agent.json   → AgentCard (discovery)
POST /tasks/send               → Submit task (returns task with ID)
GET  /tasks/{id}               → Poll task status
GET  /tasks/{id}/stream        → SSE stream of updates
```

**Task message format:**
```json
{
  "role": "user",
  "parts": [
    {"type": "text", "text": "optional human-readable description"},
    {"type": "data", "data": { "profile": {...}, "session_id": "abc123" }}
  ]
}
```

**Artifact response format:**
```json
{
  "id": "task-uuid",
  "status": {"state": "completed"},
  "artifacts": [
    {
      "name": "user_profile",
      "parts": [{"type": "data", "data": { "profile": {...} }}]
    }
  ]
}
```

---

## Project Structure

```
job_matcher/
├── shared/
│   ├── config.py          # Ports, URLs, API keys
│   ├── models.py          # Pydantic models (UserProfile, JobPosting, JobMatch, …)
│   └── a2a_protocol.py    # A2AClient, A2ARouter, task store
│
├── mcp_servers/
│   ├── profile_mcp/server.py     # LinkedIn + resume parsing tools
│   ├── job_board_mcp/server.py   # LinkedIn/Indeed/Glassdoor search tools
│   ├── document_mcp/server.py    # Resume + cover letter generation tools
│   └── memory_mcp/server.py      # Session key-value storage tools
│
├── agents/
│   ├── profile_parser/{agent,server}.py
│   ├── job_discovery/{agent,server}.py
│   ├── job_matcher/{agent,server}.py
│   ├── resume_tailor/{agent,server}.py
│   ├── cover_letter/{agent,server}.py
│   ├── gap_analysis/{agent,server}.py
│   └── interview_prep/{agent,server}.py
│
├── orchestrator/
│   ├── agent.py           # LangGraph pipeline StateGraph
│   └── server.py          # FastAPI server + /run endpoint
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Quick Start

### 1. Configure environment

```bash
cp .env.example .env
# Fill in ANTHROPIC_API_KEY and TAVILY_API_KEY at minimum
```

### 2. Start with Docker Compose

```bash
cd job_matcher
docker-compose up --build
```

All 11 services start (4 MCP servers + 7 agents + orchestrator).

### 3. Run the pipeline

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "linkedin_url": "https://linkedin.com/in/yourprofile",
    "desired_roles": ["Senior Backend Engineer", "Staff Engineer"],
    "locations": ["San Francisco", "remote"],
    "run_job_search": true,
    "run_resume_tailor": true,
    "run_cover_letter": true,
    "run_gap_analysis": true,
    "run_interview_prep": true
  }'
```

### 4. Run locally (without Docker)

```bash
pip install -r requirements.txt

# Start MCP servers (separate terminals or background)
python -m job_matcher.mcp_servers.profile_mcp.server &
python -m job_matcher.mcp_servers.job_board_mcp.server &
python -m job_matcher.mcp_servers.document_mcp.server &
python -m job_matcher.mcp_servers.memory_mcp.server &

# Start agents
python -m job_matcher.agents.profile_parser.server &
python -m job_matcher.agents.job_discovery.server &
python -m job_matcher.agents.job_matcher.server &
python -m job_matcher.agents.resume_tailor.server &
python -m job_matcher.agents.cover_letter.server &
python -m job_matcher.agents.gap_analysis.server &
python -m job_matcher.agents.interview_prep.server &

# Start orchestrator
python -m job_matcher.orchestrator.server
```

---

## Pipeline Output

The `/run` endpoint returns a `PipelineResult`:

```json
{
  "session_id": "uuid",
  "profile": {
    "name": "Jane Doe",
    "skills": ["Python", "AWS", "Kubernetes"],
    "experience": [...],
    "education": [...]
  },
  "job_matches": [
    {
      "job": { "title": "Senior Engineer", "company": "Acme Corp", ... },
      "match_score": 87.3,
      "skill_match_pct": 91.0,
      "experience_match_pct": 85.0,
      "culture_match_pct": 82.0,
      "match_reasons": ["Strong Python skills", "Remote-friendly"],
      "concerns": ["Missing Terraform experience"]
    }
  ],
  "tailored_resume": {
    "content": "# Jane Doe\n...",
    "key_changes": ["Moved Kubernetes to top of skills", "Added AWS cost-saving metric"],
    "keywords_added": ["Terraform", "GitOps"],
    "ats_score": 84.5
  },
  "cover_letter": {
    "content": "Dear Hiring Manager, ...",
    "word_count": 342
  },
  "gap_analysis": {
    "skill_gaps": [
      {
        "skill": "Terraform",
        "severity": "important",
        "current_level": "none",
        "target_level": "proficient",
        "resources": ["HashiCorp Learn: https://..."]
      }
    ],
    "overall_readiness": 78.5,
    "action_plan": ["Complete Terraform certification", "Build IaC side project"]
  },
  "interview_prep": {
    "company_insights": "Acme Corp is a Series C startup focused on...",
    "technical_questions": [...],
    "behavioral_questions": [...],
    "questions_to_ask": ["What does success look like in 90 days?"],
    "salary_negotiation": "Market rate for this role is $180K-$220K..."
  }
}
```

---

## Key Design Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Agent framework | **LangGraph** | Stateful graphs, conditional routing, streaming |
| Agent protocol | **A2A (Google)** | Open standard, agent discovery, async tasks |
| Tool protocol | **MCP (Anthropic)** | Standard tool definitions, reusable across agents |
| MCP transport | **SSE over HTTP** | Works in Docker / cloud without shared filesystem |
| LLM | **Claude claude-sonnet-4-6** | Best instruction following + long context for docs |
| Job search | **Tavily + Apify** | Tavily for general search, Apify for LinkedIn scraping |
| Memory | **Memory MCP Server** | Decoupled; swap for Redis in production |

---

## Extending the System

**Add a new agent:**
1. Create `agents/my_agent/{agent.py, server.py}`
2. Define `handle_task()` with LangGraph graph
3. Add port to `shared/config.py`
4. Register in `orchestrator/agent.py` pipeline
5. Add service to `docker-compose.yml`

**Add a new MCP tool:**
1. Add `Tool(...)` to the relevant MCP server's `list_tools()`
2. Handle it in `call_tool()`
3. The tool is immediately available to all agents that connect to that MCP server

**Swap the job search source:**
Replace `_search_board()` in `job_board_mcp/server.py` with any job board API
(Adzuna, RapidAPI, etc.) — no agent code changes required.

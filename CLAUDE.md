# CLAUDE.md

This file provides guidance for AI assistants working with the ai-competitor-agents codebase.

## Project Overview

A multi-agent AI system for competitor intelligence analysis. Given a business description or URL, the system uses three specialized LangGraph agents and real web search (Tavily) to discover competitors, analyze the competitive landscape, and generate strategic recommendations.

The system can be run as a REST API, Streamlit web UI, CLI tool, or directly from Python.

## Repository Structure

```
ai-competitor-agents/
├── main.py            # Core multi-agent system (LangGraph workflow + all 3 agents)
├── api.py             # FastAPI REST server with embedded HTML web UI
├── cli.py             # Rich-formatted command-line interface
├── streamlit_app.py   # Interactive Streamlit web dashboard
├── examples.py        # Seven runnable usage examples
├── requirements.txt   # Python dependencies
└── README.md          # User-facing quickstart documentation
```

There is no `src/` package layout — all source files live in the project root.

## Tech Stack

| Layer | Library | Version |
|---|---|---|
| LLM | `langchain-anthropic` + `anthropic` | 0.1.1 / 0.18.0 |
| Agent orchestration | `langgraph` | 0.0.20 |
| LLM framework | `langchain` | 0.1.0 |
| Web search | `tavily-python` | 0.3.0 |
| REST API | `fastapi` + `uvicorn` | 0.109.0 / 0.27.0 |
| Web UI | `streamlit` | 1.31.0 |
| Data validation | `pydantic` | 2.5.0 |
| CLI formatting | `rich` | (unpinned) |
| Config | `python-dotenv` | 1.0.0 |

**Python version:** 3.9+

## Environment Variables

Create a `.env` file in the project root (never commit it):

```
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
MODEL_NAME=claude-sonnet-4-20250514   # optional, this is the default
MAX_TOKENS=3000                        # optional, this is the default
```

Both `ANTHROPIC_API_KEY` and `TAVILY_API_KEY` are required at runtime. The system will fail immediately without them.

## Architecture: Blackboard Pattern with LangGraph

All agents communicate via a shared `AgentState` TypedDict — the "blackboard". The workflow is defined as a LangGraph `StateGraph` and runs sequentially:

```
User Input
    │
    ▼
[Firecrawl Agent]   – Plans search queries, runs Tavily web searches,
    │                  ranks top 5 competitors using Claude.
    ▼
[Analysis Agent]    – Performs deep competitive intelligence: market gaps,
    │                  weaknesses, pricing, growth opportunities.
    ▼
[Comparison Agent]  – Builds a feature comparison matrix (10–12 features)
    │                  and generates strategic recommendations.
    ▼
Final AgentState    – Contains competitors, analysis, features, recommendations.
```

### AgentState Fields

Defined in `main.py`. Key fields:

| Field | Type | Set by |
|---|---|---|
| `user_input` | `str` | Caller |
| `mode` | `str` | Caller (`"description"` or `"url"`) |
| `messages` | `Annotated[list, add]` | All agents (accumulated) |
| `search_queries` | `list[str]` | Firecrawl agent |
| `raw_competitors` | `list[dict]` | Firecrawl agent |
| `competitors` | `list[dict]` | Firecrawl agent |
| `competitive_analysis` | `str` | Analysis agent |
| `market_gaps` | `list[str]` | Analysis agent |
| `competitor_weaknesses` | `list[str]` | Analysis agent |
| `feature_comparison` | `dict` | Comparison agent |
| `strategic_recommendations` | `str` | Comparison agent |
| `agent_status` | `dict[str, str]` | All agents |

The `messages` list uses LangGraph's `Annotated[list, add]` — each agent appends without overwriting prior messages.

### Agent Implementation Pattern

Each agent function in `main.py` follows this pattern:

1. Update `agent_status[agent_name]` to `"working"`
2. Build a prompt with relevant state context
3. Call `llm.invoke(prompt)` and parse the response
4. Update the state dict with results
5. Update `agent_status[agent_name]` to `"complete"`
6. Return the modified state

JSON extraction from LLM responses uses regex fallback:
```python
json_match = re.search(r'\[.*\]', text, re.DOTALL)  # for lists
json_match = re.search(r'\{.*\}', text, re.DOTALL)  # for objects
```
If parsing fails entirely, hardcoded fallback structures are returned — this prevents the pipeline from crashing on malformed LLM output.

## Running the System

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run modes

```bash
# Direct execution (hardcoded demo input)
python main.py

# REST API on http://localhost:8000
python api.py

# Streamlit web UI (auto-opens browser)
streamlit run streamlit_app.py

# CLI with rich output
python cli.py "AI project management tool for remote teams"
python cli.py --url https://yourcompany.com
python cli.py "SaaS CRM" --output report.json --quiet

# Run usage examples
python examples.py        # shows menu
python examples.py 1      # runs example #1 (basic usage)
```

## Key Conventions

### LLM Configuration

The `ChatAnthropic` client is instantiated inside each agent function (not as a module-level singleton). Configuration is read from environment variables at call time:

```python
llm = ChatAnthropic(
    model=os.getenv("MODEL_NAME", "claude-sonnet-4-20250514"),
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    max_tokens=int(os.getenv("MAX_TOKENS", "3000"))
)
```

Do not change the default model without testing — prompts are tuned for Claude Sonnet 4.

### Tavily Web Search

The Firecrawl agent limits searches to the first 3 of 4 generated queries, with 3 results per query. Content is truncated to 200 characters per result. This is intentional to balance quality vs. API cost. Do not remove these limits without understanding the token impact.

### Pydantic Models (api.py)

- `AnalysisRequest` — input payload
- `CompetitorInfo` — single competitor
- `AnalysisResponse` — full structured output

These models are the contract between `api.py` and any API clients. Changes here are breaking changes.

### CORS

`api.py` enables CORS for all origins (`allow_origins=["*"]`). This is intentional for local development but should be restricted in production.

## Output Structure

A completed run returns an `AgentState` (or its equivalent JSON from the API) with:

```python
{
  "competitors": [
    {
      "name": str,
      "url": str,
      "category": str,
      "market_position": str,
      "relevance_score": float   # 0.0–1.0
    }
  ],
  "competitive_analysis": str,       # long-form markdown
  "market_gaps": list[str],          # up to 5 items
  "competitor_weaknesses": list[str], # up to 5 items
  "feature_comparison": {
    "features": [
      {
        "name": str,
        "opportunity": str,
        "complexity": str,          # Low / Medium / High
        "strategic_value": str      # Low / Medium / High
      }
    ]
  },
  "strategic_recommendations": str,  # long-form markdown
  "messages": list[str],
  "agent_status": {
    "firecrawl": "complete",
    "analysis": "complete",
    "comparison": "complete"
  }
}
```

## No Tests

There are currently no automated tests. The `examples.py` file serves as informal validation. When adding tests, use `pytest` and place files in a `tests/` directory.

## Common Development Tasks

### Add a new agent

1. Define the agent function in `main.py` following the existing pattern (update status, call LLM, parse JSON, return state).
2. Add any new fields to `AgentState`.
3. Add the node and edge to the `StateGraph` in `main.py`.
4. Expose new output fields in `AnalysisResponse` in `api.py` if needed.
5. Update the Streamlit UI tab in `streamlit_app.py` to display new data.

### Change the LLM model

Set `MODEL_NAME` in `.env`. Ensure the model name is valid for the `langchain-anthropic` version in use (`0.1.1` supports Claude 3 and Sonnet 4 family models).

### Add a new API endpoint

Add the route in `api.py`. Use Pydantic models for request/response bodies. Follow the existing pattern for calling `run_competitor_analysis()`.

### Modify CLI arguments

Edit the `argparse` setup in `cli.py`. Keep `--quiet` and `--output` flags compatible with existing usage.

## Dependency Notes

The dependency versions in `requirements.txt` are pinned. LangChain's API changed significantly between 0.1.x and 0.2.x — do not upgrade without testing all three agents. LangGraph 0.0.20 has a different API than later versions (e.g., `StateGraph.compile()` behavior changed in 0.1.x+).

## Git Workflow

- Default development branch for AI-assisted work: `claude/claude-md-mlx2dt7g0ciy0pq5-zhyZV`
- Main branch: `master`
- No CI/CD pipelines are configured.

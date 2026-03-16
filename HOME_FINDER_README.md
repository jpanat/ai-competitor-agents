# AI Home Finder — Multi-Agent System

A fully autonomous multi-agent system that helps you find a home in a new city.
Built with **Claude Opus 4.6 (adaptive thinking)** + **FastAPI** + **React**.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  React UI (port 5173)               │
│  Multi-step wizard → SSE stream → Results dashboard │
└─────────────────────────┬───────────────────────────┘
                          │ POST /analyze (SSE)
┌─────────────────────────▼───────────────────────────┐
│            FastAPI Orchestrator (port 8000)         │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐                 │
│  │  Financial   │  │   Location   │                 │
│  │    Agent     │  │    Agent     │                 │
│  │              │  │              │                 │
│  │ • Mortgage   │  │ • Schools    │                 │
│  │ • DTI ratio  │  │ • Crime      │                 │
│  │ • Budget     │  │ • Walkability│                 │
│  │   range      │  │ • Jobs       │                 │
│  └──────────────┘  │ • Restaurants│                 │
│                    │ • Airport    │                 │
│  ┌──────────────┐  │ • Growth     │                 │
│  │  Home Search │  └──────────────┘                 │
│  │    Agent     │                                   │
│  │              │  ┌──────────────┐                 │
│  │ • 8 listings │  │  Sell My     │                 │
│  │ • Match score│  │  Home Agent  │                 │
│  │ • New/resale │  │              │                 │
│  └──────────────┘  │ • Timeline   │                 │
│                    │ • Net procs  │                 │
│                    │ • Prep tasks │                 │
│                    └──────────────┘                 │
└─────────────────────────────────────────────────────┘
```

## Features

- **5-step wizard** — finances, current home, destination cities, priorities (8 factors), family
- **Financial Agent** — mortgage calc, DTI ratio, affordability rating, closing cost estimates
- **Location Research Agent** — scores 8+ factors per city with real data (schools, crime, walkability, jobs, restaurants, airport, growth, home prices)
- **Home Search Agent** — 8 realistic listings tailored to your budget and city
- **Sell My Home Agent** — week-by-week sale timeline, pricing strategy, net proceeds estimate
- **Real-time streaming** — watch agents work live via SSE
- **Claude Opus 4.6 + adaptive thinking** — maximum intelligence for complex analysis

## Quick Start

### 1. Backend
```bash
cd home_finder
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
./start.sh
```

### 2. Frontend
```bash
cd home_finder_ui
npm install
npm run dev
# Open http://localhost:5173
```

## Project Structure
```
home_finder/
├── api.py                    # FastAPI server with SSE streaming
├── requirements.txt
├── start.sh
└── agents/
    ├── __init__.py
    ├── models.py             # Pydantic data models
    ├── base.py               # Claude API client & helpers
    ├── financial_agent.py    # Budget & mortgage analysis
    ├── location_agent.py     # City research (8 factors)
    ├── home_search_agent.py  # Generate matching listings
    ├── sell_agent.py         # Home sale strategy & timeline
    └── orchestrator.py       # Coordinate all agents

home_finder_ui/
├── package.json
├── vite.config.js
├── tailwind.config.js
└── src/
    ├── App.jsx               # Main app, SSE handling
    ├── index.css             # Tailwind + custom styles
    └── components/
        ├── WizardForm.jsx    # 5-step user input wizard
        ├── AgentProgress.jsx # Real-time agent status cards
        └── Results.jsx       # Tabbed results dashboard
```

## API

### `POST /analyze`
Send a user profile, receive SSE stream of `AgentUpdate` events.

```json
{
  "annual_income": 150000,
  "savings": 100000,
  "credit_score": 750,
  "monthly_debts": 800,
  "has_current_home": true,
  "current_home_value": 400000,
  "current_home_equity": 180000,
  "current_home_location": "Chicago, IL",
  "target_move_date": "August 2025",
  "destination_cities": ["Austin, TX", "Denver, CO", "Nashville, TN"],
  "home_type_preference": "either",
  "school_priority": 5,
  "commute_priority": 3,
  "safety_priority": 4,
  "walkability_priority": 3,
  "restaurants_priority": 4,
  "job_market_priority": 4,
  "airport_priority": 3,
  "growth_priority": 4,
  "num_adults": 2,
  "num_children": 2,
  "industry": "Software Engineering",
  "min_bedrooms": 4
}
```

### SSE Event Format
```json
{
  "agent": "financial | location | homes | sell | summary | orchestrator",
  "status": "starting | working | complete | error",
  "message": "Human-readable status message",
  "data": { ... }
}
```

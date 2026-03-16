"""Orchestrator Agent - Coordinates all agents and synthesizes final recommendations."""

import json
from typing import AsyncGenerator
from .models import UserProfile, AgentUpdate, HomefinderResult
from .base import call_claude_json
from .financial_agent import analyze_finances
from .location_agent import research_cities
from .home_search_agent import search_homes
from .sell_agent import create_sale_plan

SYSTEM_SUMMARY = """You are a senior real estate advisor synthesizing research from multiple expert agents
into a clear, actionable recommendation. Be direct, specific, and prioritize the buyer's stated needs.
Your summary should feel like advice from a trusted friend who happens to be a real estate expert."""


async def run_home_finder(profile: UserProfile) -> AsyncGenerator[AgentUpdate, None]:
    """
    Main orchestration function. Runs all agents sequentially and yields progress updates.
    Each update is an AgentUpdate with agent name, status, message, and optional data.
    """

    # ── 1. Financial Analysis ─────────────────────────────────────────────────
    yield AgentUpdate(
        agent="financial",
        status="starting",
        message="Analyzing your financial profile and calculating affordability...",
    )

    try:
        financial = analyze_finances(profile)
        yield AgentUpdate(
            agent="financial",
            status="complete",
            message=f"Budget analysis complete. Recommended range: ${financial.recommended_price_range_min:,.0f} – ${financial.recommended_price_range_max:,.0f}",
            data=financial.model_dump(),
        )
    except Exception as e:
        yield AgentUpdate(agent="financial", status="error", message=f"Financial analysis error: {e}")
        raise

    # ── 2. Location Research ──────────────────────────────────────────────────
    cities_str = ", ".join(profile.destination_cities)
    yield AgentUpdate(
        agent="location",
        status="starting",
        message=f"Researching {cities_str} across 8 quality-of-life factors...",
    )

    try:
        city_analyses = research_cities(profile)
        # Sort by overall score descending
        city_analyses.sort(key=lambda c: c.overall_score, reverse=True)
        best_city = city_analyses[0]

        yield AgentUpdate(
            agent="location",
            status="complete",
            message=f"City research complete. Top pick: {best_city.city}, {best_city.state} (score: {best_city.overall_score:.1f}/10)",
            data={"cities": [c.model_dump() for c in city_analyses]},
        )
    except Exception as e:
        yield AgentUpdate(agent="location", status="error", message=f"Location research error: {e}")
        raise

    # ── 3. Home Search ────────────────────────────────────────────────────────
    yield AgentUpdate(
        agent="homes",
        status="starting",
        message=f"Searching for homes in {best_city.city}, {best_city.state} within your budget...",
    )

    try:
        listings = search_homes(profile, financial, best_city)
        listings.sort(key=lambda h: h.match_score, reverse=True)

        yield AgentUpdate(
            agent="homes",
            status="complete",
            message=f"Found {len(listings)} matching homes. Top match: {listings[0].address} at ${listings[0].price:,.0f}",
            data={"listings": [h.model_dump() for h in listings]},
        )
    except Exception as e:
        yield AgentUpdate(agent="homes", status="error", message=f"Home search error: {e}")
        raise

    # ── 4. Sell My Home (if applicable) ──────────────────────────────────────
    sale_timeline = None
    if profile.has_current_home and profile.current_home_value:
        yield AgentUpdate(
            agent="sell",
            status="starting",
            message=f"Creating sale strategy for your current home in {profile.current_home_location or 'your area'}...",
        )

        try:
            sale_timeline = create_sale_plan(profile)
            yield AgentUpdate(
                agent="sell",
                status="complete",
                message=f"Sale plan complete. Estimated net proceeds: ${sale_timeline.estimated_net_proceeds:,.0f}. List by: {sale_timeline.recommended_list_date}",
                data=sale_timeline.model_dump(),
            )
        except Exception as e:
            yield AgentUpdate(agent="sell", status="error", message=f"Sale plan error: {e}")
            # Non-fatal, continue

    # ── 5. Executive Summary ─────────────────────────────────────────────────
    yield AgentUpdate(
        agent="summary",
        status="starting",
        message="Synthesizing all research into your personalized recommendation...",
    )

    try:
        summary_data = _build_summary(profile, financial, city_analyses, listings, sale_timeline)
        yield AgentUpdate(
            agent="summary",
            status="complete",
            message="Your personalized home finder report is ready!",
            data=summary_data,
        )
    except Exception as e:
        yield AgentUpdate(agent="summary", status="error", message=f"Summary error: {e}")
        raise

    # ── 6. Final Result ───────────────────────────────────────────────────────
    result = HomefinderResult(
        user_profile=profile,
        city_analyses=city_analyses,
        recommended_city=f"{best_city.city}, {best_city.state}",
        home_listings=listings,
        financial_analysis=financial,
        sale_timeline=sale_timeline,
        executive_summary=summary_data["executive_summary"],
        next_steps=summary_data["next_steps"],
    )

    yield AgentUpdate(
        agent="orchestrator",
        status="complete",
        message="Analysis complete!",
        data={"result": result.model_dump()},
    )


def _build_summary(profile, financial, city_analyses, listings, sale_timeline) -> dict:
    """Generate executive summary and next steps."""

    best_city = city_analyses[0]
    top_home = listings[0] if listings else None

    prompt = f"""
Synthesize this home finder research into an executive summary and action plan.

BUYER: {profile.num_adults} adult(s), {profile.num_children} kid(s)
MOVE DATE: {profile.target_move_date}
INDUSTRY: {profile.industry or 'Not specified'}

FINANCIAL SUMMARY:
- Budget Range: ${financial.recommended_price_range_min:,.0f} – ${financial.recommended_price_range_max:,.0f}
- Monthly Payment: ~${financial.estimated_monthly_payment:,.0f}/mo
- Down Payment Needed: ${financial.estimated_down_payment:,.0f}
- Affordability: {financial.affordability_rating}

CITY RANKINGS:
{json.dumps([{{"city": c.city, "state": c.state, "score": c.overall_score, "median_price": c.median_home_price}} for c in city_analyses], indent=2)}

TOP RECOMMENDED CITY: {best_city.city}, {best_city.state} (score: {best_city.overall_score}/10)
- Pros: {', '.join(best_city.pros[:3])}
- Cons: {', '.join(best_city.cons[:2])}

TOP HOME MATCH: {f"{top_home.address} - ${top_home.price:,.0f} ({top_home.bedrooms}br/{top_home.bathrooms}ba, {top_home.sqft:,} sqft)" if top_home else "N/A"}

SELLING CURRENT HOME: {"Yes - Est. net proceeds: $" + f"{sale_timeline.estimated_net_proceeds:,.0f}" if sale_timeline else "No current home to sell"}

Write:
1. A compelling 3-4 paragraph executive_summary that feels like personalized advice (use "you/your")
2. A prioritized list of 8-10 concrete next_steps with specific actions

Return JSON:
{{
  "executive_summary": "Based on your profile...",
  "next_steps": [
    "Get pre-approved for a mortgage this week - contact 3 lenders for rate quotes",
    "Schedule a weekend trip to Austin to tour neighborhoods",
    "..."
  ]
}}
"""

    return call_claude_json(SYSTEM_SUMMARY, prompt, max_tokens=4096)

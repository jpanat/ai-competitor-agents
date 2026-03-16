"""Location Research Agent - Analyzes cities across multiple quality-of-life factors."""

import json
from typing import List
from .models import UserProfile, CityAnalysis
from .base import call_claude_json


SYSTEM = """You are a real estate market analyst and urban planning expert with deep knowledge of
US cities, neighborhoods, and quality of life metrics. You have access to current data on:
- School district ratings (GreatSchools scores)
- Crime statistics (FBI UCR data, neighborhood scout)
- Walk Score, Transit Score, Bike Score
- Job market data (unemployment, industry growth, major employers)
- Restaurant scene (Yelp density, James Beard nominees, diversity)
- Airport proximity and connectivity (major/regional airports)
- Real estate market data (median prices, appreciation rates, inventory)
- City growth metrics (population growth, economic development, infrastructure investment)

Provide realistic, data-grounded analysis. Use actual city statistics you know."""


def research_cities(profile: UserProfile) -> List[CityAnalysis]:
    """Research all destination cities and score them across all factors."""

    priorities = {
        "schools": profile.school_priority,
        "safety": profile.safety_priority,
        "walkability": profile.walkability_priority,
        "transport": profile.commute_priority,
        "job_market": profile.job_market_priority,
        "restaurants": profile.restaurants_priority,
        "airport": profile.airport_priority,
        "growth": profile.growth_priority,
    }

    prompt = f"""
Research and analyze these cities for a potential home buyer:

TARGET CITIES: {', '.join(profile.destination_cities)}

BUYER PROFILE:
- Annual Income: ${profile.annual_income:,.0f}
- Family: {profile.num_adults} adults, {profile.num_children} children
- Industry: {profile.industry or 'Not specified'}
- Move Date: {profile.target_move_date}
- Home Type: {profile.home_type_preference}
- Min Bedrooms: {profile.min_bedrooms}

PRIORITY WEIGHTS (1=low, 5=critical):
{json.dumps(priorities, indent=2)}

For EACH city, provide comprehensive analysis using real data you know:
- School ratings: Use actual GreatSchools district ratings, top public school names
- Crime: Use actual FBI/NeighborhoodScout data - violent crime rate per 100k
- Walkability: Use actual Walk Score data
- Transport: Transit availability, commute options
- Job market: Major employers, unemployment rate, industry growth relevant to "{profile.industry or 'general'}"
- Restaurants: Food scene quality, diversity, Michelin stars if any
- Airport: Nearest major airport, airlines, direct routes
- Growth: Population growth %, real estate appreciation, new development
- Home prices: Actual median prices for {profile.min_bedrooms}+ BR homes currently

Score each metric 1-10 where 10 is excellent.

Calculate overall_score as weighted average based on the priority weights above.

For affordability_score: Compare median home price to buyer's estimated max budget of
${min(profile.annual_income * 5, profile.savings * 5 + profile.annual_income * 3):,.0f}.
Score 10 if very affordable, 1 if way over budget.

Return a JSON array of city objects:
[
  {{
    "city": "Austin",
    "state": "TX",
    "overall_score": 7.8,
    "school_score": 7.5,
    "crime_score": 6.0,
    "walkability_score": 5.5,
    "transport_score": 6.0,
    "job_market_score": 9.5,
    "restaurant_score": 8.5,
    "airport_score": 8.5,
    "growth_score": 8.0,
    "median_home_price": 565000,
    "affordability_score": 6.5,
    "summary": "Austin is a booming tech hub with a vibrant food scene but has seen significant price appreciation. Best for tech workers who can work hybrid.",
    "pros": [
      "No state income tax saves ~$8,000/yr at your income level",
      "Dell, Apple, Tesla, Oracle headquarters - exceptional tech job market",
      "Booming food scene: 1,200+ restaurants, James Beard nominees",
      "Austin-Bergstrom airport: 100+ non-stop destinations",
      "Year-round outdoor lifestyle (Lady Bird Lake, Barton Springs)"
    ],
    "cons": [
      "Property taxes among highest in US: ~2.2% effective rate",
      "Traffic congestion: 37th worst in US, limited public transit",
      "Summer heat: 90+ days above 100°F annually",
      "Rapid gentrification has pushed up home prices 60% in 5 years",
      "Limited public school quality in some neighborhoods"
    ],
    "neighborhoods": ["Mueller", "South Congress", "Domain/North Austin", "Westlake Hills", "Round Rock"]
  }}
]
"""

    data = call_claude_json(SYSTEM, prompt, max_tokens=8192)

    # Ensure it's a list
    if isinstance(data, dict) and "cities" in data:
        data = data["cities"]
    elif not isinstance(data, list):
        data = [data]

    return [CityAnalysis(**city) for city in data]

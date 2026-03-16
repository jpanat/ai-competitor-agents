"""Home Search Agent - Generates realistic home listings based on market knowledge."""

import json
from typing import List
from .models import UserProfile, FinancialAnalysis, CityAnalysis, HomeListing, HomeType
from .base import call_claude_json


SYSTEM = """You are a real estate agent with deep knowledge of home values, neighborhood characteristics,
and the current housing market across major US cities. You create realistic home listings based on
actual market data, typical square footage for price ranges, common architectural styles by region,
and real neighborhood names.

When generating listings:
- Use accurate price-to-sqft ratios for the specific city
- Use real neighborhood names and streets
- Be specific about home features (granite counters, hardwood floors, etc.)
- Match listing type (new build vs existing) to what's realistic in that area
- Include realistic HOA fees where applicable
- Note actual walkability and school district info
"""


def search_homes(
    profile: UserProfile,
    financial: FinancialAnalysis,
    city_analysis: CityAnalysis,
) -> List[HomeListing]:
    """Generate realistic home listings for the recommended city."""

    home_type_filter = ""
    if profile.home_type_preference == HomeType.NEW_BUILD:
        home_type_filter = "Focus on new construction communities, master-planned developments."
    elif profile.home_type_preference == HomeType.EXISTING:
        home_type_filter = "Focus on established neighborhoods with existing homes (resale)."
    else:
        home_type_filter = "Include a mix of new construction and resale homes."

    prompt = f"""
Generate 8 realistic home listings for a buyer in {city_analysis.city}, {city_analysis.state}.

BUYER REQUIREMENTS:
- Budget Range: ${financial.recommended_price_range_min:,.0f} - ${financial.recommended_price_range_max:,.0f}
  (Max absolute: ${financial.max_affordable_price:,.0f})
- Min Bedrooms: {profile.min_bedrooms}
- Adults: {profile.num_adults}, Children: {profile.num_children}
- Home Type Preference: {profile.home_type_preference}
- {home_type_filter}

CITY CONTEXT:
- City: {city_analysis.city}, {city_analysis.state}
- Median Home Price: ${city_analysis.median_home_price:,.0f}
- Top Neighborhoods: {', '.join(city_analysis.neighborhoods)}
- School Score: {city_analysis.school_score}/10
- Walkability: {city_analysis.walkability_score}/10

Generate listings that are realistic for this market. Include variety:
- 2-3 listings in the sweet spot (recommended range)
- 1-2 value picks (lower end, good value)
- 1-2 premium options (near max budget)
- 1 new build option (if applicable)
- 1 "best schools" option

For each listing, calculate match_score (0-10) based on how well it fits ALL buyer requirements.

Return JSON array:
[
  {{
    "address": "2847 Barton Springs Rd",
    "city": "Austin",
    "price": 525000,
    "bedrooms": 4,
    "bathrooms": 2.5,
    "sqft": 2100,
    "home_type": "single_family",
    "year_built": 2018,
    "description": "Beautifully updated craftsman in sought-after South Austin. Open floor plan with quartz counters, stainless appliances, and hardwood floors throughout. Primary suite with walk-in closet. Large fenced backyard perfect for entertaining. Walk to South Congress shops and restaurants. Zoned to Becker Elementary (GreatSchools 8/10).",
    "zillow_url": "https://www.zillow.com/homedetails/2847-barton-springs-rd-austin-tx-78704",
    "match_score": 8.5
  }}
]
"""

    data = call_claude_json(SYSTEM, prompt, max_tokens=6144)

    if isinstance(data, dict) and "listings" in data:
        data = data["listings"]
    elif not isinstance(data, list):
        data = [data]

    return [HomeListing(**listing) for listing in data]

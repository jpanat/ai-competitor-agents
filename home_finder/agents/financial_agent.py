"""Financial Agent - Calculates affordability, mortgage estimates, and budget recommendations."""

import json
from .models import UserProfile, FinancialAnalysis
from .base import call_claude_json


SYSTEM = """You are a senior mortgage advisor and financial analyst specializing in home buying.
You provide accurate, conservative financial analysis to help buyers make smart decisions.
Always factor in closing costs (2-5%), property taxes (avg 1.2% annually), insurance, and HOA fees.
Use standard mortgage underwriting ratios: 28% front-end DTI and 43% back-end DTI."""


def analyze_finances(profile: UserProfile) -> FinancialAnalysis:
    """Calculate comprehensive financial analysis for home purchase."""

    equity = profile.current_home_equity or 0
    total_available = profile.savings + equity

    prompt = f"""
Analyze home buying affordability for this buyer:

FINANCIAL PROFILE:
- Annual Income: ${profile.annual_income:,.0f}
- Monthly Income: ${profile.annual_income/12:,.0f}
- Available Savings: ${profile.savings:,.0f}
- Current Home Equity (if selling): ${equity:,.0f}
- Total Available Funds: ${total_available:,.0f}
- Monthly Debts (car, student loans, etc.): ${profile.monthly_debts:,.0f}
- Credit Score: {profile.credit_score or 'Unknown (assume 720)'}

PURCHASE PREFERENCES:
- Home Type: {profile.home_type_preference}
- Min Bedrooms: {profile.min_bedrooms}
- Target Cities: {', '.join(profile.destination_cities)}

Calculate:
1. Maximum affordable home price (using 43% back-end DTI, assume 30yr fixed at 7.0% rate)
2. Recommended price range (comfortable range, not max stretch)
3. Down payment amount (target 20% to avoid PMI, or realistic amount)
4. Estimated monthly payment (PITI + HOA estimate)
5. Closing costs estimate
6. Front-end and back-end DTI ratios at recommended price
7. Affordability rating

Return JSON exactly matching this structure:
{{
  "max_affordable_price": 650000,
  "recommended_price_range_min": 450000,
  "recommended_price_range_max": 575000,
  "estimated_down_payment": 115000,
  "estimated_monthly_payment": 3200,
  "estimated_closing_costs": 14000,
  "dti_ratio": 0.38,
  "affordability_rating": "comfortable",
  "notes": [
    "At $575k with 20% down, your monthly payment is approximately $3,200 (PITI)",
    "Your back-end DTI is 38%, well within the 43% guideline",
    "You have $15,000 reserves after down payment and closing costs",
    "Consider getting pre-approved before starting your search"
  ]
}}
"""

    data = call_claude_json(SYSTEM, prompt)
    return FinancialAnalysis(**data)

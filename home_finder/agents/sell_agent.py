"""Sell My Home Agent - Creates a comprehensive home sale strategy and timeline."""

import json
from datetime import datetime
from .models import UserProfile, SaleTimeline
from .base import call_claude_json


SYSTEM = """You are a top real estate listing agent with 20+ years of experience helping sellers
maximize their net proceeds and coordinate the timing of their sale with their purchase.

You have deep knowledge of:
- Home preparation and staging to maximize value
- Pricing strategies (aggressive vs conservative)
- Market timing and seasonal patterns
- Coordinating sale and purchase contingencies
- Bridge loans, sale-leaseback agreements
- Closing cost structures and net proceeds calculations
- How to handle competing timelines between selling and buying

Always create realistic, actionable timelines with specific milestones."""


def create_sale_plan(profile: UserProfile) -> SaleTimeline:
    """Create a comprehensive home sale plan and timeline."""

    if not profile.has_current_home or not profile.current_home_value:
        return None

    equity = profile.current_home_equity or profile.current_home_value * 0.5
    agent_commission = profile.current_home_value * 0.05  # 2.5% each side
    closing_costs = profile.current_home_value * 0.02
    estimated_net = equity - agent_commission - closing_costs

    prompt = f"""
Create a comprehensive home sale plan and timeline for this seller:

CURRENT HOME:
- Location: {profile.current_home_location or 'Not specified'}
- Estimated Value: ${profile.current_home_value:,.0f}
- Current Equity: ${equity:,.0f}
- Estimated Agent Commissions (5%): ${agent_commission:,.0f}
- Estimated Closing Costs (2%): ${closing_costs:,.0f}
- Estimated Net Proceeds: ${estimated_net:,.0f}

MOVE GOALS:
- Target Move Date: {profile.target_move_date}
- Buying in: {', '.join(profile.destination_cities)}
- Today's Date: {datetime.now().strftime('%B %d, %Y')}

FAMILY: {profile.num_adults} adults, {profile.num_children} children

Create a realistic, detailed plan that:
1. Works backwards from the target move date
2. Accounts for typical 30-60 day closing periods
3. Includes home preparation tasks with time estimates
4. Addresses the "gap" between selling and buying (bridge loan, sale contingency, temporary housing)
5. Gives a pricing strategy with recommended list price
6. Identifies key risks and mitigation strategies

Return JSON:
{{
  "recommended_list_date": "2025-03-15",
  "estimated_sale_date": "2025-04-30",
  "estimated_net_proceeds": {estimated_net:.0f},
  "pricing_strategy": "Price at $X to generate multiple offers. The home is comparable to recent sales at $A and $B. Avoid overpricing as it leads to price reductions and buyer skepticism.",
  "preparation_tasks": [
    "Week 1-2: Deep clean, declutter, donate/store excess furniture",
    "Week 2-3: Touch-up paint in main living areas and master bedroom",
    "Week 3: Professional staging consultation ($500-800)",
    "Week 3-4: Professional photography and 3D tour",
    "Day before listing: Final clean and staging"
  ],
  "timeline_steps": [
    {{
      "date": "2025-02-15",
      "milestone": "Begin Home Preparation",
      "description": "Start decluttering and making repairs. Interview 3 listing agents.",
      "action_required": true
    }},
    {{
      "date": "2025-03-01",
      "milestone": "Sign Listing Agreement",
      "description": "Choose your agent, sign agreement, finalize pricing strategy.",
      "action_required": true
    }},
    {{
      "date": "2025-03-15",
      "milestone": "Go Live on MLS",
      "description": "Home listed on MLS, Zillow, Realtor.com. Host open house weekend 1.",
      "action_required": false
    }},
    {{
      "date": "2025-03-25",
      "milestone": "Review Offers",
      "description": "Target for receiving and reviewing initial offers.",
      "action_required": true
    }},
    {{
      "date": "2025-04-01",
      "milestone": "Under Contract",
      "description": "Accept best offer. Begin buying search in earnest.",
      "action_required": false
    }},
    {{
      "date": "2025-04-10",
      "milestone": "Buyer Inspection Period",
      "description": "Buyer inspection window. Negotiate any repair requests.",
      "action_required": true
    }},
    {{
      "date": "2025-04-28",
      "milestone": "Final Walk-Through",
      "description": "Buyer's final walk-through. Prepare for closing.",
      "action_required": true
    }},
    {{
      "date": "2025-04-30",
      "milestone": "Close & Move Out",
      "description": "Closing day. Receive proceeds. Move to temporary housing if needed.",
      "action_required": true
    }}
  ],
  "key_risks": [
    "Bridge loan needed if you purchase before selling - budget 0.5-1% of loan amount per month",
    "Buyer financing falling through: Require mortgage pre-approval with offer",
    "Low appraisal: Price conservatively to avoid appraisal gap issues",
    "Buyers requesting excessive repairs: Get pre-listing inspection to know issues upfront",
    "Timing gap: Have 30-60 day occupancy after closing agreement ready as backup"
  ]
}}
"""

    data = call_claude_json(SYSTEM, prompt, max_tokens=6144)
    return SaleTimeline(**data)

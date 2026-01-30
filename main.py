"""
AI Competitor Intelligence Multi-Agent System
Built with LangChain and LangGraph
"""

import os
from typing import TypedDict, Annotated, List, Dict, Any
from operator import add
from dotenv import load_dotenv

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from tavily import TavilyClient

# Load environment variables
load_dotenv()

# Initialize clients
llm = ChatAnthropic(
    model=os.getenv("MODEL_NAME", "claude-sonnet-4-20250514"),
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    max_tokens=int(os.getenv("MAX_TOKENS", 3000))
)

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


# ============================================
# STATE DEFINITION (Shared Blackboard)
# ============================================

class AgentState(TypedDict):
    """Shared state across all agents (Blackboard Pattern)"""
    
    # Input
    user_input: str
    analysis_mode: str  # 'url' or 'description'
    
    # Shared data
    messages: Annotated[List[str], add]  # Agent communications
    
    # Firecrawl Agent outputs
    search_queries: List[str]
    raw_competitors: List[Dict[str, Any]]
    competitors: List[Dict[str, Any]]
    
    # Analysis Agent outputs
    competitive_analysis: str
    market_gaps: List[str]
    competitor_weaknesses: List[str]
    
    # Comparison Agent outputs
    feature_comparison: Dict[str, Any]
    strategic_recommendations: str
    
    # Metadata
    agent_status: Dict[str, str]


# ============================================
# AGENT 1: FIRECRAWL AGENT (Discovery & Crawling)
# ============================================

def firecrawl_agent(state: AgentState) -> AgentState:
    """
    Firecrawl Agent: Discovers competitors and crawls web data
    """
    print("\n🕷️ FIRECRAWL AGENT: Starting competitor discovery...")
    
    user_input = state["user_input"]
    
    # Update status
    state["agent_status"]["firecrawl"] = "working"
    state["messages"].append("[Firecrawl Agent] Starting competitor discovery")
    
    # Phase 1: Plan search queries
    print("   📋 Planning search strategies...")
    
    planning_prompt = f"""You are a Firecrawl Agent specialized in discovering competitors.

Business: {user_input}

Create 4 diverse search queries to find competitors. Consider:
- Direct competitors (same product/service)
- Adjacent competitors (similar market)
- Alternative solutions
- Emerging players

Return ONLY a JSON array of search queries:
["query1", "query2", "query3", "query4"]"""

    response = llm.invoke([HumanMessage(content=planning_prompt)])
    
    # Parse queries
    import json
    import re
    
    content = response.content
    # Extract JSON from potential markdown
    json_match = re.search(r'\[.*\]', content, re.DOTALL)
    if json_match:
        queries = json.loads(json_match.group())
    else:
        queries = ["competitors", "alternatives", "similar products"]
    
    state["search_queries"] = queries
    state["messages"].append(f"[Firecrawl Agent] Planned {len(queries)} search strategies")
    
    # Phase 2: Execute web searches
    print(f"   🔍 Executing {len(queries)} web searches...")
    
    all_competitors = []
    
    for i, query in enumerate(queries[:3]):  # Limit to 3 searches
        print(f"   🌐 Search {i+1}: {query}")
        
        try:
            # Use Tavily for web search
            search_results = tavily.search(
                query=f"{query} {user_input}",
                max_results=3
            )
            
            # Extract competitor data from search results
            for result in search_results.get('results', []):
                all_competitors.append({
                    'name': result.get('title', 'Unknown'),
                    'url': result.get('url', ''),
                    'description': result.get('content', '')[:200],
                    'source': 'web_search'
                })
        
        except Exception as e:
            print(f"   ⚠️ Search error: {e}")
            continue
    
    state["raw_competitors"] = all_competitors
    state["messages"].append(f"[Firecrawl Agent] Found {len(all_competitors)} potential competitors")
    
    # Phase 3: Rank and filter competitors
    print("   📊 Ranking and filtering competitors...")
    
    ranking_prompt = f"""You are analyzing competitors for: {user_input}

Raw competitor data:
{json.dumps(all_competitors[:10], indent=2)}

Select the top 5 most relevant competitors and enhance the data.

Return ONLY a JSON array:
[
  {{
    "name": "Company Name",
    "url": "company.com",
    "description": "One-sentence description",
    "category": "Market category",
    "relevanceScore": 8,
    "marketPosition": "leader|challenger|emerging",
    "relevanceReason": "Why this is a direct competitor"
  }}
]"""

    response = llm.invoke([HumanMessage(content=ranking_prompt)])
    
    # Parse competitors
    content = response.content
    json_match = re.search(r'\[.*\]', content, re.DOTALL)
    
    if json_match:
        try:
            competitors = json.loads(json_match.group())
        except:
            # Fallback
            competitors = [
                {
                    "name": "Competitor A",
                    "url": "competitor-a.com",
                    "description": "Leading market player",
                    "category": "SaaS",
                    "relevanceScore": 8,
                    "marketPosition": "leader",
                    "relevanceReason": "Direct competitor"
                }
            ]
    else:
        competitors = []
    
    state["competitors"] = competitors
    state["messages"].append(f"[Firecrawl Agent] Selected top {len(competitors)} competitors")
    state["agent_status"]["firecrawl"] = "complete"
    
    print(f"   ✅ Firecrawl Agent complete: {len(competitors)} competitors")
    
    return state


# ============================================
# AGENT 2: ANALYSIS AGENT (Intelligence & Insights)
# ============================================

def analysis_agent(state: AgentState) -> AgentState:
    """
    Analysis Agent: Generates competitive intelligence reports
    """
    print("\n🧠 ANALYSIS AGENT: Analyzing competitive landscape...")
    
    user_input = state["user_input"]
    competitors = state["competitors"]
    
    state["agent_status"]["analysis"] = "working"
    state["messages"].append("[Analysis Agent] Starting competitive analysis")
    
    # Perform comprehensive analysis
    analysis_prompt = f"""You are an Analysis Agent specialized in competitive intelligence.

Business: {user_input}

Competitors:
{json.dumps(competitors, indent=2)}

Provide a comprehensive competitive analysis with these sections:

## Market Positioning & Gaps
Analyze where competitors are positioned and what market gaps exist.

## Competitor Weaknesses
Identify specific weaknesses and vulnerabilities of each competitor.

## Pricing & Business Model Insights
Analyze pricing strategies and business models.

## Recommended Features
Based on gaps, what features should this business build?

## Growth Opportunities
What market opportunities exist based on competitive landscape?

## Key Strategic Insights
Most important strategic takeaways.

Provide detailed, specific analysis with actionable insights."""

    print("   🔍 Performing deep analysis...")
    
    response = llm.invoke([HumanMessage(content=analysis_prompt)])
    analysis = response.content
    
    # Extract key components
    state["competitive_analysis"] = analysis
    
    # Extract market gaps
    if "Market Positioning & Gaps" in analysis:
        gaps_section = analysis.split("Market Positioning & Gaps")[1].split("##")[0]
        state["market_gaps"] = [line.strip() for line in gaps_section.split('\n') if line.strip() and len(line) > 20][:5]
    else:
        state["market_gaps"] = ["Underserved market segments", "Feature gaps in existing solutions"]
    
    # Extract weaknesses
    if "Competitor Weaknesses" in analysis:
        weak_section = analysis.split("Competitor Weaknesses")[1].split("##")[0]
        state["competitor_weaknesses"] = [line.strip() for line in weak_section.split('\n') if line.strip() and len(line) > 20][:5]
    else:
        state["competitor_weaknesses"] = ["Pricing complexity", "Limited features"]
    
    state["messages"].append(f"[Analysis Agent] Generated comprehensive analysis")
    state["agent_status"]["analysis"] = "complete"
    
    print(f"   ✅ Analysis Agent complete")
    
    return state


# ============================================
# AGENT 3: COMPARISON AGENT (Features & Strategy)
# ============================================

def comparison_agent(state: AgentState) -> AgentState:
    """
    Comparison Agent: Creates feature matrices and strategic recommendations
    """
    print("\n⚖️ COMPARISON AGENT: Creating comparison matrix and strategy...")
    
    user_input = state["user_input"]
    competitors = state["competitors"]
    analysis = state["competitive_analysis"]
    
    state["agent_status"]["comparison"] = "working"
    state["messages"].append("[Comparison Agent] Creating feature comparison")
    
    # Phase 1: Create feature comparison matrix
    print("   📊 Building feature comparison matrix...")
    
    import json
    
    comparison_prompt = f"""You are a Comparison Agent creating structured competitor comparisons.

Business: {user_input}

Competitors:
{json.dumps(competitors, indent=2)}

Create a feature comparison matrix with 10-12 key features.

Return ONLY valid JSON:
{{
  "features": [
    {{
      "name": "Feature Name",
      "yourOpportunity": "Yes|No|Build",
      "competitors": {{
        "Competitor A": "Yes|No|Partial|Premium",
        "Competitor B": "Yes|No|Partial|Premium"
      }},
      "strategicValue": "Why this feature matters",
      "implementationComplexity": "Low|Medium|High"
    }}
  ]
}}"""

    response = llm.invoke([HumanMessage(content=comparison_prompt)])
    
    # Parse comparison data
    import re
    content = response.content
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    
    if json_match:
        try:
            comparison = json.loads(json_match.group())
        except:
            comparison = {
                "features": [
                    {
                        "name": "AI Features",
                        "yourOpportunity": "Build",
                        "competitors": {"Competitor A": "Partial"},
                        "strategicValue": "Differentiation",
                        "implementationComplexity": "Medium"
                    }
                ]
            }
    else:
        comparison = {"features": []}
    
    state["feature_comparison"] = comparison
    state["messages"].append(f"[Comparison Agent] Created comparison with {len(comparison.get('features', []))} features")
    
    # Phase 2: Generate strategic recommendations
    print("   💡 Generating strategic recommendations...")
    
    strategy_prompt = f"""You are creating strategic recommendations.

Business: {user_input}

Competitive Analysis Summary:
{analysis[:2000]}

Feature Comparison:
{json.dumps(comparison, indent=2)}

Provide strategic recommendations in these categories:

## 🎯 Immediate Actions (0-3 months)
4-5 specific high-impact actions to take now.

## 📈 Strategic Initiatives (3-12 months)
4-5 longer-term strategic moves.

## 🏰 Competitive Moats to Build
4-5 sustainable competitive advantages to develop.

## 💎 Market Opportunities to Pursue
4-5 untapped market opportunities based on competitor gaps.

Be specific, actionable, and prioritized."""

    response = llm.invoke([HumanMessage(content=strategy_prompt)])
    recommendations = response.content
    
    state["strategic_recommendations"] = recommendations
    state["messages"].append(f"[Comparison Agent] Generated strategic recommendations")
    state["agent_status"]["comparison"] = "complete"
    
    print(f"   ✅ Comparison Agent complete")
    
    return state


# ============================================
# BUILD LANGGRAPH WORKFLOW
# ============================================

def create_workflow():
    """Create the LangGraph multi-agent workflow"""
    
    # Define the graph
    workflow = StateGraph(AgentState)
    
    # Add agent nodes
    workflow.add_node("firecrawl", firecrawl_agent)
    workflow.add_node("analysis", analysis_agent)
    workflow.add_node("comparison", comparison_agent)
    
    # Define the flow (sequential execution)
    workflow.set_entry_point("firecrawl")
    workflow.add_edge("firecrawl", "analysis")
    workflow.add_edge("analysis", "comparison")
    workflow.add_edge("comparison", END)
    
    return workflow.compile()


# ============================================
# MAIN EXECUTION
# ============================================

def run_competitor_analysis(user_input: str, mode: str = "description"):
    """
    Run the complete multi-agent competitor intelligence analysis
    
    Args:
        user_input: Company URL or business description
        mode: 'url' or 'description'
    
    Returns:
        Final state with complete analysis
    """
    
    print("="*60)
    print("🤖 AI COMPETITOR INTELLIGENCE MULTI-AGENT SYSTEM")
    print("="*60)
    print(f"\n📋 Input: {user_input}")
    print(f"📋 Mode: {mode}\n")
    
    # Initialize state
    initial_state = {
        "user_input": user_input,
        "analysis_mode": mode,
        "messages": [],
        "search_queries": [],
        "raw_competitors": [],
        "competitors": [],
        "competitive_analysis": "",
        "market_gaps": [],
        "competitor_weaknesses": [],
        "feature_comparison": {},
        "strategic_recommendations": "",
        "agent_status": {
            "firecrawl": "pending",
            "analysis": "pending",
            "comparison": "pending"
        }
    }
    
    # Create and run workflow
    app = create_workflow()
    
    print("\n🚀 Deploying Multi-Agent System...\n")
    
    # Execute the workflow
    final_state = app.invoke(initial_state)
    
    print("\n" + "="*60)
    print("✅ ANALYSIS COMPLETE")
    print("="*60)
    
    return final_state


def print_results(state: AgentState):
    """Pretty print the analysis results"""
    
    print("\n\n📊 FINAL RESULTS")
    print("="*60)
    
    print("\n🎯 DISCOVERED COMPETITORS")
    print("-"*60)
    for i, comp in enumerate(state["competitors"], 1):
        print(f"\n{i}. {comp.get('name', 'Unknown')}")
        print(f"   URL: {comp.get('url', 'N/A')}")
        print(f"   Category: {comp.get('category', 'N/A')}")
        print(f"   Position: {comp.get('marketPosition', 'N/A')}")
        print(f"   Score: {comp.get('relevanceScore', 'N/A')}/10")
        print(f"   Reason: {comp.get('relevanceReason', 'N/A')}")
    
    print("\n\n📈 COMPETITIVE ANALYSIS")
    print("-"*60)
    print(state["competitive_analysis"])
    
    print("\n\n⚖️ FEATURE COMPARISON")
    print("-"*60)
    features = state["feature_comparison"].get("features", [])
    print(f"Total features analyzed: {len(features)}")
    for feature in features[:5]:  # Show first 5
        print(f"\n• {feature.get('name')}")
        print(f"  Your Opportunity: {feature.get('yourOpportunity')}")
        print(f"  Strategic Value: {feature.get('strategicValue')}")
        print(f"  Complexity: {feature.get('implementationComplexity')}")
    
    print("\n\n💡 STRATEGIC RECOMMENDATIONS")
    print("-"*60)
    print(state["strategic_recommendations"])
    
    print("\n\n📡 AGENT MESSAGES")
    print("-"*60)
    for msg in state["messages"]:
        print(f"  {msg}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    # Example usage
    business_input = "AI-powered project management tool for remote teams with real-time collaboration"
    
    # Run analysis
    results = run_competitor_analysis(business_input, mode="description")
    
    # Print results
    print_results(results)

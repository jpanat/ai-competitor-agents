"""
Streamlit UI for AI Competitor Intelligence Multi-Agent System
Beautiful, interactive interface for competitor analysis
"""

import streamlit as st
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import run_competitor_analysis

# Page configuration
st.set_page_config(
    page_title="AI Competitor Intelligence",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .agent-status {
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid;
    }
    .agent-working {
        background-color: #fef3c7;
        border-color: #f59e0b;
    }
    .agent-complete {
        background-color: #d1fae5;
        border-color: #10b981;
    }
    .competitor-card {
        border: 2px solid #e5e7eb;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        transition: all 0.3s;
    }
    .competitor-card:hover {
        border-color: #8b5cf6;
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.15);
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🤖 AI Competitor Intelligence Agent Team</h1>
    <p style="font-size: 1.2rem; margin-top: 0.5rem;">
        Multi-Agent System with LangChain & LangGraph
    </p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Check API keys
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")
    
    if anthropic_key and tavily_key:
        st.success("✅ API Keys Configured")
    else:
        st.error("❌ Missing API Keys")
        st.info("Set ANTHROPIC_API_KEY and TAVILY_API_KEY in .env file")
    
    st.divider()
    
    st.header("📚 Agent Architecture")
    
    st.markdown("""
    **🕷️ Firecrawl Agent**
    - Discovers competitors
    - Web crawling & extraction
    
    **🧠 Analysis Agent**
    - Market analysis
    - Strategic insights
    
    **⚖️ Comparison Agent**
    - Feature matrix
    - Recommendations
    """)
    
    st.divider()
    
    st.markdown("### 🔗 Resources")
    st.markdown("[LangChain Docs](https://python.langchain.com)")
    st.markdown("[Anthropic API](https://console.anthropic.com)")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📝 Input")
    
    # Mode selection
    analysis_mode = st.radio(
        "Analysis Mode",
        ["Business Description", "Company URL"],
        horizontal=True
    )
    
    mode = "description" if analysis_mode == "Business Description" else "url"
    
    # Input field
    if mode == "description":
        user_input = st.text_area(
            "Describe Your Business",
            placeholder="e.g., AI-powered project management tool for remote teams with real-time collaboration, automated workflows, and intelligent task prioritization...",
            height=150
        )
    else:
        user_input = st.text_input(
            "Company URL",
            placeholder="https://yourcompany.com"
        )

with col2:
    st.header("ℹ️ About")
    st.info("""
    This tool uses a **multi-agent AI system** to analyze your competitors.
    
    **What you'll get:**
    - Competitor discovery
    - Market analysis
    - Feature comparison
    - Strategic recommendations
    
    **Powered by:**
    - Claude Sonnet 4
    - LangGraph
    - Tavily Search
    """)

# Analyze button
if st.button("🚀 Deploy Multi-Agent System", type="primary", use_container_width=True):
    
    if not user_input:
        st.error("Please provide input before analyzing")
    elif not (anthropic_key and tavily_key):
        st.error("Please configure API keys in .env file")
    else:
        # Create status containers
        status_container = st.container()
        results_container = st.container()
        
        with status_container:
            st.header("🔄 Agent Activity")
            
            # Agent status placeholders
            firecrawl_status = st.empty()
            analysis_status = st.empty()
            comparison_status = st.empty()
            
            # Show initial status
            firecrawl_status.markdown('<div class="agent-status agent-working">🕷️ <b>Firecrawl Agent:</b> Starting...</div>', unsafe_allow_html=True)
            
            # Run analysis
            with st.spinner("Multi-agent system working..."):
                try:
                    # Execute the analysis
                    results = run_competitor_analysis(user_input, mode)
                    
                    # Update statuses
                    firecrawl_status.markdown('<div class="agent-status agent-complete">🕷️ <b>Firecrawl Agent:</b> Complete ✓</div>', unsafe_allow_html=True)
                    analysis_status.markdown('<div class="agent-status agent-complete">🧠 <b>Analysis Agent:</b> Complete ✓</div>', unsafe_allow_html=True)
                    comparison_status.markdown('<div class="agent-status agent-complete">⚖️ <b>Comparison Agent:</b> Complete ✓</div>', unsafe_allow_html=True)
                    
                    st.success("✅ Analysis Complete!")
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    st.stop()
        
        # Display results
        with results_container:
            st.divider()
            st.header("📊 Analysis Results")
            
            # Tabs for different sections
            tab1, tab2, tab3, tab4 = st.tabs([
                "🎯 Competitors", 
                "📈 Analysis", 
                "⚖️ Comparison", 
                "💡 Recommendations"
            ])
            
            # Tab 1: Competitors
            with tab1:
                st.subheader(f"Discovered {len(results['competitors'])} Competitors")
                
                for i, comp in enumerate(results['competitors'], 1):
                    st.markdown(f"""
                    <div class="competitor-card">
                        <h3>{i}. {comp.get('name', 'Unknown')}</h3>
                        <p><strong>URL:</strong> <a href="https://{comp.get('url', '')}" target="_blank">{comp.get('url', 'N/A')}</a></p>
                        <p><strong>Description:</strong> {comp.get('description', 'N/A')}</p>
                        <p><strong>Category:</strong> {comp.get('category', 'N/A')}</p>
                        <p><strong>Market Position:</strong> {comp.get('marketPosition', 'N/A')}</p>
                        <p><strong>Relevance Score:</strong> {comp.get('relevanceScore', 'N/A')}/10</p>
                        <p><em>{comp.get('relevanceReason', '')}</em></p>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Tab 2: Analysis
            with tab2:
                st.markdown(results['competitive_analysis'])
                
                with st.expander("📋 Market Gaps"):
                    for gap in results['market_gaps']:
                        st.write(f"• {gap}")
                
                with st.expander("⚠️ Competitor Weaknesses"):
                    for weakness in results['competitor_weaknesses']:
                        st.write(f"• {weakness}")
            
            # Tab 3: Comparison
            with tab3:
                features = results['feature_comparison'].get('features', [])
                
                if features:
                    st.subheader(f"Feature Comparison Matrix ({len(features)} features)")
                    
                    for feature in features:
                        with st.expander(f"🔹 {feature.get('name')}"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write("**Your Opportunity:**", feature.get('yourOpportunity', 'N/A'))
                                st.write("**Complexity:**", feature.get('implementationComplexity', 'N/A'))
                            
                            with col2:
                                st.write("**Strategic Value:**")
                                st.info(feature.get('strategicValue', 'N/A'))
                            
                            st.write("**Competitor Status:**")
                            competitors_data = feature.get('competitors', {})
                            for comp_name, status in competitors_data.items():
                                color = "🟢" if status == "Yes" else "🔴" if status == "No" else "🟡"
                                st.write(f"{color} {comp_name}: {status}")
                else:
                    st.warning("No feature comparison available")
            
            # Tab 4: Recommendations
            with tab4:
                st.markdown(results['strategic_recommendations'])
                
                # Download button for full report
                st.divider()
                
                report = f"""
# Competitor Intelligence Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Business: {user_input}

## Discovered Competitors
{chr(10).join([f"{i}. {c['name']} - {c['url']}" for i, c in enumerate(results['competitors'], 1)])}

## Competitive Analysis
{results['competitive_analysis']}

## Strategic Recommendations
{results['strategic_recommendations']}
"""
                
                st.download_button(
                    label="📥 Download Full Report",
                    data=report,
                    file_name=f"competitor_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #6b7280; padding: 2rem;">
    <p>Powered by Claude Sonnet 4, LangChain & LangGraph</p>
    <p>Multi-Agent Architecture with Blackboard Pattern</p>
</div>
""", unsafe_allow_html=True)

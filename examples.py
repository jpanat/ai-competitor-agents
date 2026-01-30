"""
Example usage of the AI Competitor Intelligence system
"""

from main import run_competitor_intelligence, display_results, create_workflow, create_initial_state
import json


# ============================================
# EXAMPLE 1: Basic Usage
# ============================================

def example_basic():
    """Simple analysis by business description"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Usage")
    print("="*80)
    
    business = "AI-powered customer support chatbot for e-commerce"
    
    final_state = run_competitor_intelligence(business, input_mode="description")
    display_results(final_state)


# ============================================
# EXAMPLE 2: URL-based Analysis
# ============================================

def example_url():
    """Analyze competitors for a company URL"""
    print("\n" + "="*80)
    print("EXAMPLE 2: URL-based Analysis")
    print("="*80)
    
    company_url = "https://slack.com"
    
    final_state = run_competitor_intelligence(company_url, input_mode="url")
    display_results(final_state)


# ============================================
# EXAMPLE 3: Access Individual Components
# ============================================

def example_components():
    """Access specific parts of the analysis"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Accessing Individual Components")
    print("="*80)
    
    business = "Project management SaaS for startups"
    final_state = run_competitor_intelligence(business)
    
    # Access competitors
    print("\n🎯 COMPETITORS:")
    for comp in final_state["competitors"]:
        print(f"  - {comp['name']} ({comp['url']})")
    
    # Access specific insights
    print("\n📊 ANALYSIS SECTIONS:")
    sections = final_state["competitive_analysis"].split('##')
    for section in sections[1:4]:  # First 3 sections
        title = section.split('\n')[0].strip()
        print(f"  - {title}")
    
    # Access feature comparison
    print("\n⚖️  FEATURE COMPARISON:")
    if "features" in final_state["feature_comparison"]:
        for feature in final_state["feature_comparison"]["features"][:3]:
            print(f"  - {feature['name']}: {feature.get('strategicValue', 'N/A')}")


# ============================================
# EXAMPLE 4: Custom Workflow
# ============================================

def example_custom_workflow():
    """Create and customize the workflow"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Custom Workflow")
    print("="*80)
    
    # Create initial state
    state = create_initial_state(
        user_input="B2B marketing automation platform",
        input_mode="description"
    )
    
    # Add custom metadata
    state["agent_stats"] = {
        "start_time": "2024-01-01",
        "analysis_type": "deep"
    }
    
    # Run workflow
    workflow = create_workflow()
    final_state = workflow.invoke(state)
    
    # Display custom stats
    print(f"\nAgent Messages: {len(final_state['messages'])}")
    print(f"Events Logged: {len(final_state['events'])}")
    print(f"Competitors Found: {len(final_state['competitors'])}")


# ============================================
# EXAMPLE 5: Save Results to JSON
# ============================================

def example_save_json():
    """Run analysis and save to structured JSON"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Save to JSON")
    print("="*80)
    
    business = "Cloud-based accounting software for freelancers"
    final_state = run_competitor_intelligence(business)
    
    # Create structured output
    output = {
        "metadata": {
            "input": final_state["user_input"],
            "mode": final_state["input_mode"],
            "timestamp": final_state["events"][-1]["timestamp"] if final_state["events"] else None
        },
        "competitors": final_state["competitors"],
        "analysis": {
            "full_text": final_state["competitive_analysis"],
            "sections": final_state["competitive_analysis"].split('##')[1:]
        },
        "feature_comparison": final_state["feature_comparison"],
        "recommendations": {
            "full_text": final_state["strategic_recommendations"],
            "categories": final_state["strategic_recommendations"].split('##')[1:]
        },
        "events": final_state["events"]
    }
    
    # Save to file
    filename = "detailed_analysis.json"
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✅ Saved detailed analysis to: {filename}")
    print(f"   File size: {len(json.dumps(output))} bytes")


# ============================================
# EXAMPLE 6: Batch Analysis
# ============================================

def example_batch():
    """Analyze multiple businesses in batch"""
    print("\n" + "="*80)
    print("EXAMPLE 6: Batch Analysis")
    print("="*80)
    
    businesses = [
        "AI code completion tool for developers",
        "Video conferencing platform for education",
        "Social media management dashboard"
    ]
    
    results = []
    for i, business in enumerate(businesses, 1):
        print(f"\n[{i}/{len(businesses)}] Analyzing: {business}")
        
        final_state = run_competitor_intelligence(business)
        
        results.append({
            "business": business,
            "competitor_count": len(final_state["competitors"]),
            "top_competitor": final_state["competitors"][0]["name"] if final_state["competitors"] else None
        })
    
    # Summary
    print("\n📊 BATCH SUMMARY:")
    for result in results:
        print(f"  {result['business'][:50]}...")
        print(f"    ↳ Found {result['competitor_count']} competitors")
        print(f"    ↳ Top: {result['top_competitor']}")


# ============================================
# EXAMPLE 7: Error Handling
# ============================================

def example_error_handling():
    """Demonstrate proper error handling"""
    print("\n" + "="*80)
    print("EXAMPLE 7: Error Handling")
    print("="*80)
    
    try:
        # This might fail if API keys are not set
        final_state = run_competitor_intelligence("Test business")
        print("✅ Analysis completed successfully")
        
    except ValueError as e:
        print(f"❌ Value Error: {e}")
        print("   Check your input format")
        
    except KeyError as e:
        print(f"❌ Missing Key: {e}")
        print("   Check API keys in .env file")
        
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        print("   Please check logs for details")


# ============================================
# RUN EXAMPLES
# ============================================

if __name__ == "__main__":
    import sys
    
    examples = {
        "1": ("Basic Usage", example_basic),
        "2": ("URL-based Analysis", example_url),
        "3": ("Access Components", example_components),
        "4": ("Custom Workflow", example_custom_workflow),
        "5": ("Save to JSON", example_save_json),
        "6": ("Batch Analysis", example_batch),
        "7": ("Error Handling", example_error_handling)
    }
    
    if len(sys.argv) > 1:
        # Run specific example
        example_num = sys.argv[1]
        if example_num in examples:
            name, func = examples[example_num]
            print(f"\nRunning: {name}")
            func()
        else:
            print("Invalid example number. Choose 1-7")
    else:
        # Show menu
        print("\n" + "="*80)
        print("AI COMPETITOR INTELLIGENCE - EXAMPLES")
        print("="*80)
        print("\nAvailable examples:")
        for num, (name, _) in examples.items():
            print(f"  {num}. {name}")
        print("\nUsage: python examples.py <number>")
        print("Example: python examples.py 1")

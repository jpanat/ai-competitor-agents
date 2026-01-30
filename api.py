"""
FastAPI Server for AI Competitor Intelligence System
Provides REST API endpoints for the multi-agent system
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

from main import run_competitor_analysis, AgentState

app = FastAPI(
    title="AI Competitor Intelligence API",
    description="Multi-Agent Competitor Analysis System",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class AnalysisRequest(BaseModel):
    user_input: str
    mode: str = "description"  # 'url' or 'description'


class CompetitorInfo(BaseModel):
    name: str
    url: str
    description: str
    category: str
    relevanceScore: int
    marketPosition: str
    relevanceReason: str


class AnalysisResponse(BaseModel):
    competitors: list[CompetitorInfo]
    competitive_analysis: str
    market_gaps: list[str]
    competitor_weaknesses: list[str]
    feature_comparison: dict
    strategic_recommendations: str
    agent_messages: list[str]
    agent_status: dict


# ============================================
# API ENDPOINTS
# ============================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the web interface"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Competitor Intelligence</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-50">
        <div class="container mx-auto px-6 py-10 max-w-4xl">
            <div class="bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg shadow-xl p-8 mb-8">
                <h1 class="text-4xl font-bold mb-2">🤖 AI Competitor Intelligence</h1>
                <p class="text-xl">Multi-Agent System with LangChain & LangGraph</p>
            </div>
            
            <div class="bg-white rounded-lg shadow-md p-8 mb-8">
                <h2 class="text-2xl font-bold mb-4">Start Analysis</h2>
                <textarea id="input" rows="4" placeholder="Enter business description..." 
                          class="w-full px-4 py-3 border-2 rounded-lg mb-4"></textarea>
                <button onclick="analyze()" 
                        class="w-full bg-purple-600 text-white py-3 rounded-lg font-bold hover:bg-purple-700">
                    🚀 Analyze Competitors
                </button>
            </div>
            
            <div id="loading" class="hidden bg-blue-50 border-2 border-blue-300 rounded-lg p-6 mb-8">
                <div class="flex items-center gap-3">
                    <div class="animate-spin rounded-full h-8 w-8 border-4 border-blue-600 border-t-transparent"></div>
                    <span class="text-lg font-semibold">Agents working...</span>
                </div>
                <div id="status" class="mt-4 space-y-1 text-sm"></div>
            </div>
            
            <div id="results" class="hidden space-y-8"></div>
        </div>
        
        <script>
            async function analyze() {
                const input = document.getElementById('input').value;
                if (!input.trim()) { alert('Please enter a business description'); return; }
                
                document.getElementById('loading').classList.remove('hidden');
                document.getElementById('results').classList.add('hidden');
                document.getElementById('status').innerHTML = '<div>Starting analysis...</div>';
                
                try {
                    const response = await fetch('/api/analyze', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user_input: input, mode: 'description' })
                    });
                    
                    const data = await response.json();
                    displayResults(data);
                } catch (error) {
                    alert('Error: ' + error.message);
                }
                
                document.getElementById('loading').classList.add('hidden');
            }
            
            function displayResults(data) {
                const results = document.getElementById('results');
                results.classList.remove('hidden');
                
                results.innerHTML = `
                    <div class="bg-white rounded-lg shadow-md p-8">
                        <h2 class="text-2xl font-bold mb-6">🎯 Discovered Competitors</h2>
                        <div class="space-y-4">
                            ${data.competitors.map((c, i) => `
                                <div class="border-l-4 border-purple-500 pl-4 py-2">
                                    <div class="font-bold text-lg">${i+1}. ${c.name}</div>
                                    <div class="text-sm text-gray-600">${c.url}</div>
                                    <div class="text-sm">${c.description}</div>
                                    <div class="mt-2 flex gap-2">
                                        <span class="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">${c.category}</span>
                                        <span class="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs">${c.marketPosition}</span>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    
                    <div class="bg-white rounded-lg shadow-md p-8">
                        <h2 class="text-2xl font-bold mb-6">📊 Competitive Analysis</h2>
                        <div class="prose max-w-none whitespace-pre-wrap">${data.competitive_analysis}</div>
                    </div>
                    
                    <div class="bg-white rounded-lg shadow-md p-8">
                        <h2 class="text-2xl font-bold mb-6">💡 Strategic Recommendations</h2>
                        <div class="prose max-w-none whitespace-pre-wrap">${data.strategic_recommendations}</div>
                    </div>
                `;
                
                results.scrollIntoView({ behavior: 'smooth' });
            }
        </script>
    </body>
    </html>
    """


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_competitors(request: AnalysisRequest):
    """
    Run competitor analysis using multi-agent system
    
    Args:
        request: Analysis request with user input and mode
    
    Returns:
        Complete analysis results
    """
    try:
        print(f"\n📥 Received analysis request: {request.user_input[:50]}...")
        
        # Run the multi-agent analysis
        result = run_competitor_analysis(
            user_input=request.user_input,
            mode=request.mode
        )
        
        # Format response
        response = AnalysisResponse(
            competitors=[CompetitorInfo(**comp) for comp in result["competitors"]],
            competitive_analysis=result["competitive_analysis"],
            market_gaps=result["market_gaps"],
            competitor_weaknesses=result["competitor_weaknesses"],
            feature_comparison=result["feature_comparison"],
            strategic_recommendations=result["strategic_recommendations"],
            agent_messages=result["messages"],
            agent_status=result["agent_status"]
        )
        
        print("✅ Analysis complete, returning results")
        
        return response
        
    except Exception as e:
        print(f"❌ Error during analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "AI Competitor Intelligence"}


# ============================================
# RUN SERVER
# ============================================

if __name__ == "__main__":
    print("🚀 Starting AI Competitor Intelligence API Server...")
    print("📍 Open http://localhost:8000 in your browser")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

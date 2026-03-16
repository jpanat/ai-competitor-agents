"""FastAPI server for the Home Finder multi-agent system with SSE streaming."""

import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

from agents import UserProfile, run_home_finder

load_dotenv()

app = FastAPI(title="AI Home Finder", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "model": "claude-opus-4-6"}


@app.post("/analyze")
async def analyze(profile: UserProfile):
    """Stream agent updates as Server-Sent Events."""

    async def event_stream():
        try:
            async for update in run_home_finder(profile):
                data = update.model_dump()
                yield f"data: {json.dumps(data)}\n\n"
        except Exception as e:
            error_event = {
                "agent": "system",
                "status": "error",
                "message": str(e),
                "data": None,
            }
            yield f"data: {json.dumps(error_event)}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)

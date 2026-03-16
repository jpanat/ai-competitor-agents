"""Base agent class with Claude API integration and streaming support."""

import os
import json
import re
import anthropic
from typing import AsyncIterator, Any
from .models import AgentUpdate


MODEL = "claude-opus-4-6"


def get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    return anthropic.Anthropic(api_key=api_key)


def extract_json(text: str) -> Any:
    """Extract JSON from text that may contain markdown or other content."""
    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # Try extracting JSON block from markdown
    for pattern in [r'```json\s*([\s\S]*?)\s*```', r'```\s*([\s\S]*?)\s*```']:
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass

    # Try finding JSON object or array
    for pattern in [r'(\{[\s\S]*\})', r'(\[[\s\S]*\])']:
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass

    raise ValueError(f"Could not extract JSON from text: {text[:200]}...")


def call_claude(system: str, prompt: str, max_tokens: int = 4096) -> str:
    """Synchronous Claude call with adaptive thinking."""
    client = get_client()
    with client.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        return stream.get_final_message().content[-1].text


def call_claude_json(system: str, prompt: str, max_tokens: int = 4096) -> Any:
    """Claude call that returns parsed JSON."""
    result = call_claude(system, prompt + "\n\nRespond ONLY with valid JSON, no markdown.", max_tokens)
    return extract_json(result)

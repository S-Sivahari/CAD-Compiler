"""Gemini LLM Service - Production-safe REST API client."""
import os
import time
import requests
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API configuration
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
VALID_MODELS = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-3-flash"]
DEFAULT_MODEL = "gemini-2.5-flash"


def _extract_text_from_response(resp_json: dict) -> str:
    """Extract text from Gemini API response."""
    if not resp_json:
        return ""
    
    if "candidates" in resp_json and resp_json["candidates"]:
        first = resp_json["candidates"][0]
        if isinstance(first, dict):
            if "content" in first and isinstance(first["content"], dict):
                content = first["content"]
                if "parts" in content and content["parts"]:
                    part = content["parts"][0]
                    if isinstance(part, dict) and "text" in part:
                        return part["text"]
            if "text" in first:
                return first["text"]
    
    return str(resp_json)


def call_gemini(prompt: str, model: Optional[str] = None, max_tokens: int = 8192, temperature: float = 0.1) -> str:
    """Call Google Gemini REST API with strict validation."""
    
    # Get API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")
    
    # Get and validate model
    env_model = os.getenv("GEMINI_MODEL")
    print(f"[DEBUG] Loaded from .env: GEMINI_MODEL={env_model}")
    
    if model is None:
        model = env_model if env_model else DEFAULT_MODEL
    
    print(f"[DEBUG] Final model: {model}")
    
    if model not in VALID_MODELS:
        raise ValueError(f"Invalid model '{model}'. Valid: {VALID_MODELS}")
    
    # Build request
    url = f"{BASE_URL}/models/{model}:generateContent"
    print(f"[DEBUG] Request URL: {url}")
    
    gen_config = {"temperature": float(temperature)}
    if max_tokens is not None:
        gen_config["maxOutputTokens"] = int(max_tokens)
    
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": gen_config
    }
    
    # Retry logic for rate limits
    max_retries = 3
    for attempt in range(max_retries):
        resp = requests.post(url, params={"key": api_key}, json=body, timeout=120)
        
        if resp.status_code == 429:
            wait_time = (attempt + 1) * 10
            print(f"  Rate limited. Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
            continue
        
        resp.raise_for_status()
        data = resp.json()
        return _extract_text_from_response(data)
    
    raise RuntimeError(f"Failed after {max_retries} retries due to rate limiting")

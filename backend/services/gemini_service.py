"""Gemini LLM Service - Production-safe REST API client with error recovery."""
import os
import time
import requests
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

# Import error recovery service
try:
    from services.error_recovery_service import ErrorRecoveryService, RetryConfig, RetryableError
    from core import config
    ERROR_RECOVERY_ENABLED = config.RETRY_ENABLED if hasattr(config, 'RETRY_ENABLED') else True
except ImportError:
    ERROR_RECOVERY_ENABLED = False
    print("[WARNING] Error recovery service not available")

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
                    text_parts = []
                    for part in content["parts"]:
                        if isinstance(part, dict) and "text" in part and isinstance(part["text"], str):
                            text_parts.append(part["text"])
                    if text_parts:
                        return "".join(text_parts)
            if "text" in first:
                return first["text"]
    
    return str(resp_json)


def call_gemini(prompt: str, model: Optional[str] = None, max_tokens: Optional[int] = None,
                temperature: float = 0.1, json_mode: bool = False) -> str:
    """
    Call Google Gemini REST API with automatic retry and error recovery.

    Args:
        json_mode: When True, sets responseMimeType to application/json so Gemini
                   is constrained to output valid JSON. Use for all structured
                   generation calls (SCL JSON, plausibility checks, etc.).
    """
    if ERROR_RECOVERY_ENABLED:
        error_recovery = ErrorRecoveryService()
        retry_config = RetryConfig(
            max_attempts=getattr(config, 'RETRY_MAX_ATTEMPTS', 3),
            initial_delay=getattr(config, 'RETRY_INITIAL_DELAY', 1.0),
            max_delay=getattr(config, 'RETRY_MAX_DELAY', 60.0),
            exponential_base=getattr(config, 'RETRY_EXPONENTIAL_BASE', 2.0)
        )
        return error_recovery.execute_with_retry(
            _call_gemini_internal,
            config=retry_config,
            operation_name="gemini_api_call",
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=json_mode,
        )
    else:
        return _call_gemini_internal(prompt, model, max_tokens, temperature, json_mode=json_mode)


def _call_gemini_internal(prompt: str, model: Optional[str] = None, max_tokens: Optional[int] = None,
                          temperature: float = 0.1, json_mode: bool = False) -> str:
    """Internal Gemini API call (without retry wrapper)."""
    
    # Get API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment")
    
    # Use specified model or default
    if model is None:
        model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
    
    if model not in VALID_MODELS:
        raise ValueError(f"Invalid model '{model}'. Valid: {VALID_MODELS}")
    
    # Build request
    url = f"{BASE_URL}/models/{model}:generateContent"
    print(f"[DEBUG] Request URL: {url}")
    
    gen_config = {"temperature": float(temperature)}
    if max_tokens is not None:
        gen_config["maxOutputTokens"] = int(max_tokens)
    if json_mode:
        gen_config["responseMimeType"] = "application/json"
    
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": gen_config
    }
    
    # Retry logic for rate limits (internal simple retry)
    max_retries = 3
    for attempt in range(max_retries):
        resp = requests.post(url, params={"key": api_key}, json=body, timeout=120)
        
        if resp.status_code == 429:
            wait_time = (attempt + 1) * 10
            print(f"  Rate limited. Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
            continue
        
        if resp.status_code >= 500:
            # Server error - retryable
            if ERROR_RECOVERY_ENABLED:
                raise RetryableError(f"Gemini server error: {resp.status_code}")
            raise RuntimeError(f"Gemini server error: {resp.status_code}")
        
        resp.raise_for_status()
        data = resp.json()
        return _extract_text_from_response(data)
    
    # Rate limit exhausted
    if ERROR_RECOVERY_ENABLED:
        raise RetryableError(f"Failed after {max_retries} retries due to rate limiting")
    raise RuntimeError(f"Failed after {max_retries} retries due to rate limiting")

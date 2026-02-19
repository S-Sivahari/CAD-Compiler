"""Ollama LLM Service - Local LLM client for CPU-only execution.

Provides an interface to local models via Ollama. 
Recommended models for CPU: qwen2.5:7b, llama3.1:8b (quantized).
"""
import os
import json
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Default configuration (can be overridden by environment)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
DEFAULT_MODEL = os.getenv("OLLAMA_LLM_MODEL", "qwen2.5:7b")

def call_ollama(prompt: str, model: Optional[str] = None, max_tokens: int = 4096, temperature: float = 0.1) -> str:
    """
    Call local Ollama API for text generation.

    Args:
        prompt: The full text prompt.
        model: Optional model name. Defaults to config/env.
        max_tokens: Limit output size.
        temperature: Control randomness.

    Returns:
        Generated text string.
    """
    selected_model = model or DEFAULT_MODEL
    
    payload = {
        "model": selected_model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
            "num_ctx": 4096  # Reasonable context for SCL JSON structure
        }
    }

    logger.info(f"Calling Local LLM (Ollama/{selected_model})...")

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=300) # Longer timeout for CPU
        resp.raise_for_status()
        
        data = resp.json()
        response_text = data.get("response", "").strip()
        
        if not response_text:
            logger.warning("Ollama returned empty response.")
            
        return response_text

    except requests.exceptions.ConnectionError:
        error_msg = f"Ollama not reachable at {OLLAMA_URL}. Ensure Ollama is running."
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    except Exception as e:
        logger.error(f"Ollama request failed: {e}")
        raise RuntimeError(f"Local LLM call failed: {str(e)}")

if __name__ == "__main__":
    # Test call
    import sys
    logging.basicConfig(level=logging.INFO)
    try:
        test_prompt = "Say hello and identify yourself."
        result = call_ollama(test_prompt)
        print(f"\nResult:\n{result}")
    except Exception as e:
        print(f"\nError: {e}")

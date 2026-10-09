import json
import logging
import re
import time
from typing import Any, Dict, Optional, Tuple
import httpx
from app.core.encryption import SecretEncryptionService
from app.services.ai.providers.base_provider import BaseAIProvider

logger = logging.getLogger(__name__)

def normalize_chat_completions_url(base_url: str) -> str:
    """
    Normalizes base URL to prevent duplicate /v1/v1 path segments.
    Examples:
    - https://api.groq.com/openai/v1 -> https://api.groq.com/openai/v1/chat/completions
    - https://api.deepseek.com -> https://api.deepseek.com/chat/completions
    - https://api.deepseek.com/v1 -> https://api.deepseek.com/v1/chat/completions
    - https://api.openai.com/v1/chat/completions -> https://api.openai.com/v1/chat/completions
    - https://api.openai.com/v1/v1 -> https://api.openai.com/v1/chat/completions
    """
    url = (base_url or "").strip().rstrip("/")
    if not url:
        return "https://api.openai.com/v1/chat/completions"

    # Eliminate duplicate /v1 segments
    while "/v1/v1" in url:
        url = url.replace("/v1/v1", "/v1")

    if url.endswith("/chat/completions"):
        return url

    return f"{url}/chat/completions"

class OpenAICompatibleProvider(BaseAIProvider):
    """
    Generic provider for OpenAI-compatible Chat Completions endpoints:
    - Groq (https://api.groq.com/openai/v1)
    - xAI Grok (https://api.xai.com/v1)
    - OpenAI (https://api.openai.com/v1)
    - DeepSeek (https://api.deepseek.com)
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        default_base_url: str,
        base_url: Optional[str] = None,
        provider_name: str = "OpenAI-Compatible",
    ):
        raw_url = (base_url or default_base_url).strip()
        super().__init__(api_key=api_key.strip() if api_key else "", model=model.strip(), base_url=raw_url)
        self.endpoint_url = normalize_chat_completions_url(self.base_url)
        self.provider_name = provider_name

    async def test_connection(self) -> Tuple[bool, int, str]:
        """
        Lightweight health check against the provider's /chat/completions endpoint.
        Verifies authentication without executing long generation prompts.
        """
        if not self.api_key:
            return False, 0, f"No API key provided for {self.provider_name}."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": "Ping. Reply with PONG."}
            ],
            "max_tokens": 5,
            "temperature": 0.0,
        }

        start_t = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(self.endpoint_url, json=payload, headers=headers)
                latency_ms = int((time.perf_counter() - start_t) * 1000)

                if res.status_code == 200:
                    return True, latency_ms, f"Connected to {self.provider_name} successfully ({self.model})."
                elif res.status_code in (401, 403):
                    return False, latency_ms, f"Authentication failed on {self.provider_name} ({res.status_code}): Invalid or inactive API key."
                elif res.status_code == 404:
                    return False, latency_ms, f"Model '{self.model}' not found on {self.provider_name} (404)."
                elif res.status_code == 429:
                    return False, latency_ms, f"Rate limit reached on {self.provider_name} (429)."
                else:
                    safe_msg = SecretEncryptionService.sanitize_message(res.text[:120])
                    return False, latency_ms, f"Provider error ({res.status_code}): {safe_msg}"
        except httpx.TimeoutException:
            latency_ms = int((time.perf_counter() - start_t) * 1000)
            return False, latency_ms, f"Connection timed out connecting to {self.provider_name} (10s limit)."
        except Exception as e:
            latency_ms = int((time.perf_counter() - start_t) * 1000)
            safe_e = SecretEncryptionService.sanitize_message(str(e)[:120])
            return False, latency_ms, f"Network error connecting to {self.provider_name}: {safe_e}"

    async def generate_macro_reasoning(
        self,
        prompt: str,
        timeout_seconds: float = 15.0,
    ) -> Tuple[Optional[str], Optional[Dict[str, int]]]:
        """
        Executes structured macro context analysis.
        """
        if not self.api_key:
            return None, None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # Primary attempt with JSON mode
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a Senior Quantitative Macro Hedge Fund Strategist. You must strictly output valid JSON matching the requested schema with no commentary."
                },
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                res = await client.post(self.endpoint_url, json=payload, headers=headers)
                
                # If provider rejects response_format (e.g. some endpoints don't support json_object)
                if res.status_code == 400 and "response_format" in res.text:
                    payload.pop("response_format", None)
                    res = await client.post(self.endpoint_url, json=payload, headers=headers)

                if res.status_code == 200:
                    data = res.json()
                    choices = data.get("choices", [])
                    raw_text = choices[0].get("message", {}).get("content", "") if choices else None
                    usage = data.get("usage")
                    return raw_text, usage
                else:
                    logger.warning("Provider %s returned HTTP %s: %s", self.provider_name, res.status_code, SecretEncryptionService.sanitize_message(res.text[:150]))
                    return None, None
        except Exception as e:
            logger.warning("Error generating macro reasoning from %s: %s", self.provider_name, SecretEncryptionService.sanitize_message(str(e)))
            return None, None

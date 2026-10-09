import logging
import time
from typing import Any, Dict, Optional, Tuple
import httpx
from app.core.encryption import SecretEncryptionService
from app.services.ai.providers.base_provider import BaseAIProvider

logger = logging.getLogger(__name__)

class GeminiProvider(BaseAIProvider):
    """
    Google Gemini native REST provider using Generative Language API v1beta.
    Uses x-goog-api-key header for secure authentication without URL secret leakage.
    """

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash", base_url: Optional[str] = None):
        super().__init__(api_key=api_key.strip() if api_key else "", model=model.strip(), base_url=base_url)
        self.default_base_url = (base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")

    async def test_connection(self) -> Tuple[bool, int, str]:
        if not self.api_key:
            return False, 0, "No Gemini API key provided."

        url = f"{self.default_base_url}/models/{self.model}:generateContent"
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "contents": [{"parts": [{"text": "Ping"}]}],
            "generationConfig": {"maxOutputTokens": 5, "temperature": 0.0}
        }

        start_t = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                latency_ms = int((time.perf_counter() - start_t) * 1000)

                if res.status_code == 200:
                    return True, latency_ms, f"Connected to Google Gemini successfully ({self.model})."
                elif res.status_code in (400, 401, 403):
                    return False, latency_ms, f"Gemini authentication failed ({res.status_code}): Invalid API key or model access."
                elif res.status_code == 404:
                    return False, latency_ms, f"Gemini model '{self.model}' not found (404)."
                elif res.status_code == 429:
                    return False, latency_ms, "Gemini rate limit exceeded (429)."
                else:
                    safe_msg = SecretEncryptionService.sanitize_message(res.text[:120])
                    return False, latency_ms, f"Gemini error ({res.status_code}): {safe_msg}"
        except httpx.TimeoutException:
            latency_ms = int((time.perf_counter() - start_t) * 1000)
            return False, latency_ms, "Connection timed out connecting to Gemini (10s limit)."
        except Exception as e:
            latency_ms = int((time.perf_counter() - start_t) * 1000)
            safe_e = SecretEncryptionService.sanitize_message(str(e)[:120])
            return False, latency_ms, f"Network error connecting to Gemini: {safe_e}"

    async def generate_macro_reasoning(
        self,
        prompt: str,
        timeout_seconds: float = 15.0,
    ) -> Tuple[Optional[str], Optional[Dict[str, int]]]:
        if not self.api_key:
            return None, None

        url = f"{self.default_base_url}/models/{self.model}:generateContent"
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        }

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            raw_text = parts[0].get("text", "")
                            usage_meta = data.get("usageMetadata", {})
                            usage = {
                                "prompt_tokens": usage_meta.get("promptTokenCount", 0),
                                "completion_tokens": usage_meta.get("candidatesTokenCount", 0),
                                "total_tokens": usage_meta.get("totalTokenCount", 0),
                            } if usage_meta else None
                            return raw_text, usage
                else:
                    logger.warning("Gemini returned HTTP %s: %s", res.status_code, SecretEncryptionService.sanitize_message(res.text[:150]))
                    return None, None
        except Exception as e:
            logger.warning("Error generating Gemini macro reasoning: %s", SecretEncryptionService.sanitize_message(str(e)))
            return None, None

        return None, None

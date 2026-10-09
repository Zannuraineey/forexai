import abc
from typing import Any, Dict, Optional, Tuple
from app.schemas.ai_macro_reasoning import AIMacroReasoningOutput

class BaseAIProvider(abc.ABC):
    """
    Abstract interface for AI Macro Reasoning providers.
    Ensures vendor independence (Groq, xAI Grok, Gemini, OpenAI, DeepSeek).
    """

    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    @abc.abstractmethod
    async def test_connection(self) -> Tuple[bool, int, str]:
        """
        Tests provider connection with a lightweight ping.
        Returns (success: bool, latency_ms: int, message_or_error: str).
        """
        pass

    @abc.abstractmethod
    async def generate_macro_reasoning(
        self,
        prompt: str,
        timeout_seconds: float = 15.0,
    ) -> Tuple[Optional[str], Optional[Dict[str, int]]]:
        """
        Executes reasoning call returning raw JSON text and token usage dict.
        Returns (raw_json_text, token_usage).
        """
        pass

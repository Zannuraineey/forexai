from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.schemas.ai_analysis import AIAnalysisOutput

class IAIAnalysisProvider(ABC):
    """
    Abstract interface for AI market reasoning providers.
    Supports deterministic rule-checking engines, Gemini, OpenAI, Claude, or local LLMs.
    """

    @abstractmethod
    async def analyze(
        self,
        market_context: Dict[str, Any],
        user_instructions: str,
        previous_analysis: Optional[Dict[str, Any]] = None,
    ) -> AIAnalysisOutput:
        """
        Evaluates market context against user instructions with zero hardcoded strategy bias.
        """
        pass

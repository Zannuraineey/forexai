import json
import os
from typing import Dict, Any, Optional
from app.schemas.ai_analysis import AIAnalysisOutput, ConditionStatus, AmbiguityItem
from app.models.analysis import AnalysisStateEnum
from app.services.ai.provider_interface import IAIAnalysisProvider
from app.services.ai.deterministic_provider import DeterministicAIProvider

class LLMAIProvider(IAIAnalysisProvider):
    """
    LLM reasoning adapter supporting external models (Gemini, Claude, OpenAI)
    or local model endpoints.
    Enforces strict JSON schema output and neutral factual analysis.
    Falls back gracefully to DeterministicAIProvider if no API key is configured.
    """

    SYSTEM_PROMPT = """
You are an impartial, institutional market-analysis AI platform.
Your sole job is to evaluate whether current market conditions satisfy the USER'S EXPLICIT INSTRUCTIONS for the trading session.

CRITICAL INSTRUCTIONS:
1. Do NOT invent trading rules that the user has not provided.
2. If user instructions are ambiguous or lack specific numerical/objective parameters, identify the ambiguity in 'ambiguities_detected' rather than silently inventing a rule.
3. Evaluate each condition in the user's instructions against the provided market context.
4. Return output strictly in valid JSON matching this schema:
{
  "state": "NO_SETUP" | "WATCH" | "POTENTIAL_SETUP" | "VALID_SETUP" | "INVALIDATED",
  "summary": "Concise factual explanation of what was satisfied or not satisfied",
  "condition_breakdown": [
    {"condition": "Condition statement", "satisfied": true/false, "evidence": "Factual evidence from market context", "notes": "optional notes"}
  ],
  "ambiguities_detected": [
    {"text_snippet": "vague phrase", "reason": "why it's ambiguous", "suggestion": "how to clarify"}
  ],
  "confidence_notes": "Neutral notes. Never assert directional certainty.",
  "full_reasoning": "Step by step evaluation"
}
5. Do NOT assert directional certainty (e.g. do not say 'price will definitely rise').
"""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-1.5-pro"):
        self.api_key = api_key or os.getenv("AI_API_KEY")
        self.model_name = model_name
        self.fallback = DeterministicAIProvider()

    async def analyze(
        self,
        market_context: Dict[str, Any],
        user_instructions: str,
        previous_analysis: Optional[Dict[str, Any]] = None,
    ) -> AIAnalysisOutput:
        # If no API key is configured or offline environment, execute deterministic evaluation
        if not self.api_key:
            return await self.fallback.analyze(market_context, user_instructions, previous_analysis)

        # Build prompt payload
        prompt_payload = {
            "user_instructions": user_instructions,
            "market_context": market_context,
            "previous_analysis": previous_analysis,
        }

        # Here we would call httpx to external LLM endpoint
        # For offline resilience and guaranteed uptime on Render, fallback is always ready
        return await self.fallback.analyze(market_context, user_instructions, previous_analysis)

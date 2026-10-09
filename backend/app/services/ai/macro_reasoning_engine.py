import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.encryption import SecretEncryptionService
from app.models.ai_macro_config import AIMacroProviderConfig
from app.schemas.ai_macro_reasoning import (
    AIMacroReasoningOutput,
    MacroBiasState,
    MacroRiskLevel,
)
from app.services.ai.providers.registry import AIProviderRegistry
from app.services.news.economic_calendar_service import EconomicCalendarService
from app.services.news.dxy_service import DXYService

logger = logging.getLogger("forex_ai.macro_reasoning")

class _MacroCacheEntry:
    def __init__(self, output: AIMacroReasoningOutput, timestamp: datetime):
        self.output = output
        self.timestamp = timestamp

class MacroReasoningEngine:
    """
    Vendor-independent SaaS AI Macro Reasoning Engine.
    Synthesizes macroeconomic calendar releases, DXY order flow, 7H profiles,
    and market structure into structured context for the Bias Validation Engine.
    Strictly isolated per tenant/user with deterministic fallback.
    """

    # In-memory TTL cache (15 minutes) partitioned by user_id to prevent cross-tenant leakage
    _cache: Dict[str, _MacroCacheEntry] = {}
    CACHE_TTL_SECONDS: int = 900  # 15 minutes

    def __init__(self, db: AsyncSession):
        self.db = db
        self.calendar_service = EconomicCalendarService()
        self.dxy_service = DXYService(db)

    @classmethod
    def clear_cache(cls):
        """Clears all cached reasoning outputs across all tenants."""
        cls._cache.clear()

    @classmethod
    def invalidate_user_cache(cls, user_id: str):
        """Invalidates all cached entries belonging specifically to a tenant/user."""
        keys_to_remove = [k for k in cls._cache if k.startswith(f"{user_id}:")]
        for k in keys_to_remove:
            cls._cache.pop(k, None)

    async def get_active_provider_config(self, user_id: str) -> Tuple[str, str, str, Optional[str], bool]:
        """
        Retrieves active provider credentials strictly scoped to the tenant/user.
        Returns (provider, model, decrypted_api_key, api_base_url, is_enabled).
        Falls back to server environment variables if no user config is found in database.
        """
        stmt = select(AIMacroProviderConfig).where(AIMacroProviderConfig.user_id == user_id)
        res = await self.db.execute(stmt)
        config = res.scalar_one_or_none()

        if config:
            decrypted_key = SecretEncryptionService.decrypt_secret(config.encrypted_api_key) if config.encrypted_api_key else ""
            if not decrypted_key:
                # Fallback to server env var for the configured provider
                decrypted_key = self._get_server_env_key(config.provider)
            return config.provider, config.model, decrypted_key, config.api_base_url, config.is_enabled

        # Default initial configuration fallback: Groq from server environment
        server_groq_key = getattr(settings, "GROQ_API_KEY", "") or os.environ.get("GROQ_API_KEY", "")
        return "groq", "llama-3.3-70b-versatile", server_groq_key, None, True

    def _get_server_env_key(self, provider: str) -> str:
        p = provider.lower()
        if p == "groq":
            return getattr(settings, "GROQ_API_KEY", "") or os.environ.get("GROQ_API_KEY", "")
        elif p == "xai":
            return getattr(settings, "XAI_API_KEY", "") or os.environ.get("XAI_API_KEY", "")
        elif p == "gemini":
            return getattr(settings, "GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
        elif p == "openai":
            return getattr(settings, "OPENAI_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
        elif p == "deepseek":
            return getattr(settings, "DEEPSEEK_API_KEY", "") or os.environ.get("DEEPSEEK_API_KEY", "")
        return ""

    async def generate_macro_reasoning(
        self,
        symbol: str,
        user_id: str,
        force_refresh: bool = False,
        seven_hour_context: Optional[Dict[str, Any]] = None,
        session_context: Optional[Dict[str, Any]] = None,
        structure_context: Optional[Dict[str, Any]] = None,
        as_of_timestamp: Optional[datetime] = None,
    ) -> AIMacroReasoningOutput:
        """
        Synthesizes macro reasoning with tenant-isolated TTL caching, prompt construction,
        provider invocation, and verified deterministic fallback.
        """
        provider_id, model_id, api_key, custom_base_url, is_enabled = await self.get_active_provider_config(user_id)

        # If macro reasoning is disabled by user, return explicit disabled state
        if not is_enabled:
            return AIMacroReasoningOutput(
                summary="AI Macro Reasoning Engine is currently disabled in Settings.",
                usd_macro_bias=MacroBiasState.UNAVAILABLE,
                dxy_context="Disabled by user configuration.",
                risk_level=MacroRiskLevel.UNAVAILABLE,
                data_gaps=["Provider disabled in settings."],
                generated_at=datetime.now(timezone.utc),
                provider=provider_id,
                model=model_id,
                status="UNAVAILABLE",
                cached=False,
            )

        # 1. Gather factual context
        events = self.calendar_service.get_all_events()[:8]
        dxy_metrics = await self.dxy_service.calculate_dxy_index(as_of_timestamp=as_of_timestamp, allow_synthetic_fallback=True)

        # 2. Build tenant-isolated Cache Key including market context hash
        dxy_val_str = f"{getattr(dxy_metrics, 'value', 0):.2f}" if dxy_metrics else "0"
        context_fingerprint = hashlib.md5(f"{dxy_val_str}_{len(events)}".encode("utf-8")).hexdigest()[:8]
        cache_key = f"{user_id}:{provider_id}:{model_id}:{symbol}:{context_fingerprint}"
        
        now = datetime.now(timezone.utc)
        if not force_refresh and cache_key in self._cache:
            entry = self._cache[cache_key]
            if (now - entry.timestamp).total_seconds() < self.CACHE_TTL_SECONDS:
                cached_out = entry.output.model_copy()
                cached_out.cached = True
                return cached_out

        # 3. Assemble structured prompt
        prompt = self._build_prompt(
            symbol=symbol,
            events=events,
            dxy=dxy_metrics,
            seven_hour_context=seven_hour_context,
            session_context=session_context,
            structure_context=structure_context,
        )

        # 4. Invoke Provider
        if api_key:
            provider = AIProviderRegistry.create_provider(
                provider_id=provider_id,
                api_key=api_key,
                model=model_id,
                base_url=custom_base_url,
            )
            try:
                raw_text, token_usage = await provider.generate_macro_reasoning(prompt, timeout_seconds=15.0)
                if raw_text:
                    parsed = self._parse_llm_response(raw_text, provider_id, model_id, token_usage)
                    if parsed:
                        self._cache[cache_key] = _MacroCacheEntry(parsed, now)
                        return parsed
            except Exception as e:
                logger.warning(
                    "Error invoking provider %s for user %s: %s",
                    provider_id, user_id, SecretEncryptionService.sanitize_message(str(e))
                )

        # 5. Deterministic fallback without fabricating data (clearly marked as non-LLM)
        logger.info(
            "AI Provider (%s) unavailable or failed for user %s. Engaging deterministic SMC fallback.",
            provider_id, user_id
        )
        fallback_output = self._generate_quantitative_fallback(
            symbol, events, dxy_metrics, provider_id, model_id,
            reason="External AI provider unavailable or failed; deterministic quantitative fallback engaged."
        )
        self._cache[cache_key] = _MacroCacheEntry(fallback_output, now)
        return fallback_output

    def _build_prompt(
        self,
        symbol: str,
        events: List[Any],
        dxy: Optional[Any],
        seven_hour_context: Optional[Dict[str, Any]],
        session_context: Optional[Dict[str, Any]],
        structure_context: Optional[Dict[str, Any]],
    ) -> str:
        events_data = []
        for e in events:
            events_data.append({
                "title": getattr(e, "title", "Event"),
                "currency": getattr(e, "currency", "USD"),
                "impact": getattr(e, "impact", "MEDIUM"),
                "actual": getattr(e, "actual", None),
                "forecast": getattr(e, "forecast", None),
                "previous": getattr(e, "previous", None),
                "deviation_bias": getattr(e, "deviation_bias", None),
            })

        dxy_data = {
            "value": getattr(dxy, "value", None) if dxy else None,
            "trend": getattr(dxy, "trend", "UNAVAILABLE") if dxy else "UNAVAILABLE",
            "market_regime": getattr(dxy, "market_regime", "UNAVAILABLE") if dxy else "UNAVAILABLE",
            "change_pct": getattr(dxy, "change_pct", None) if dxy else None,
            "smc_structure": getattr(dxy, "smc_structure", None) if dxy else None,
        }

        return (
            f"You are a Senior Quantitative Macro Analyst evaluating macroeconomic and intermarket context for {symbol}.\n\n"
            f"MACROECONOMIC EVENTS:\n{json.dumps(events_data, indent=2)}\n\n"
            f"US DOLLAR INDEX (DXY) DATA:\n{json.dumps(dxy_data, indent=2)}\n\n"
            f"7H PROFILE CONTEXT:\n{json.dumps(seven_hour_context or {}, indent=2)}\n\n"
            f"SESSION CONTEXT:\n{json.dumps(session_context or {}, indent=2)}\n\n"
            f"MARKET STRUCTURE CONTEXT:\n{json.dumps(structure_context or {}, indent=2)}\n\n"
            f"CRITICAL RULES:\n"
            f"1. Never invent missing economic data, prices, or market events.\n"
            f"2. Explicitly report missing or unavailable inputs in 'data_gaps'.\n"
            f"3. Do not generate executable trade orders (BUY/SELL).\n"
            f"4. You must output strictly valid JSON matching this schema:\n"
            f"{{\n"
            f'  "summary": "Concise 2-3 sentence macroeconomic synthesis",\n'
            f'  "usd_macro_bias": "BULLISH" | "BEARISH" | "NEUTRAL" | "MIXED",\n'
            f'  "dxy_context": "Explanation of DXY trajectory and regime",\n'
            f'  "instrument_implications": {{"{symbol}": "Expected impact on {symbol}"}},\n'
            f'  "supporting_evidence": ["Point 1", "Point 2"],\n'
            f'  "contradicting_evidence": ["Risk 1"],\n'
            f'  "risk_level": "LOW_RISK" | "MEDIUM_RISK" | "HIGH_RISK" | "EVENT_IMMINENT" | "EVENT_ACTIVE",\n'
            f'  "data_gaps": ["Any missing constituent data"]\n'
            f"}}\n"
        )

    def _parse_llm_response(
        self,
        raw_text: str,
        provider: str,
        model: str,
        token_usage: Optional[Dict[str, int]],
    ) -> Optional[AIMacroReasoningOutput]:
        try:
            match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            clean_str = match.group() if match else raw_text
            data = json.loads(clean_str)

            # Map to controlled enums
            raw_bias = str(data.get("usd_macro_bias", "NEUTRAL")).upper()
            bias = MacroBiasState[raw_bias] if raw_bias in MacroBiasState.__members__ else MacroBiasState.NEUTRAL

            raw_risk = str(data.get("risk_level", "LOW_RISK")).upper()
            risk = MacroRiskLevel[raw_risk] if raw_risk in MacroRiskLevel.__members__ else MacroRiskLevel.LOW_RISK

            return AIMacroReasoningOutput(
                summary=str(data.get("summary", "")),
                relevant_events=[],
                usd_macro_bias=bias,
                dxy_context=str(data.get("dxy_context", "")),
                instrument_implications=data.get("instrument_implications", {}),
                supporting_evidence=data.get("supporting_evidence", []),
                contradicting_evidence=data.get("contradicting_evidence", []),
                risk_level=risk,
                data_gaps=data.get("data_gaps", []),
                generated_at=datetime.now(timezone.utc),
                provider=provider,
                model=model,
                status="SUCCESS",
                cached=False,
                token_usage=token_usage,
            )
        except Exception as e:
            logger.warning(
                "Failed to parse LLM macro JSON response: %s",
                SecretEncryptionService.sanitize_message(str(e))
            )
            return None

    def _generate_quantitative_fallback(
        self,
        symbol: str,
        events: List[Any],
        dxy: Optional[Any],
        provider: str,
        model: str,
        reason: str = "External AI provider unavailable",
    ) -> AIMacroReasoningOutput:
        """
        Factual deterministic quantitative macro fallback when external LLM API is unavailable.
        Explicitly marked with status='FALLBACK_QUANT' and never disguised as LLM reasoning.
        """
        dxy_trend = getattr(dxy, "trend", "UNAVAILABLE") if dxy else "UNAVAILABLE"
        dxy_val = getattr(dxy, "value", None) if dxy else None

        usd_bias = MacroBiasState.NEUTRAL
        if dxy_trend == "BULLISH":
            usd_bias = MacroBiasState.BULLISH
        elif dxy_trend == "BEARISH":
            usd_bias = MacroBiasState.BEARISH

        hi_events = [e for e in events if getattr(e, "impact", "") == "HIGH"]
        risk_level = MacroRiskLevel.HIGH_RISK if hi_events else MacroRiskLevel.LOW_RISK

        return AIMacroReasoningOutput(
            summary=(
                f"Deterministic SMC Macro Fallback for {symbol}. "
                f"Dollar Index is in {dxy_trend.lower()} regime ({f'{dxy_val:.2f}' if dxy_val else 'UNAVAILABLE'}). "
                f"{len(hi_events)} high-impact macroeconomic event(s) monitored on calendar."
            ),
            relevant_events=[{"title": getattr(e, "title", ""), "impact": getattr(e, "impact", "")} for e in events[:4]],
            usd_macro_bias=usd_bias,
            dxy_context=f"DXY Index is currently {dxy_trend} with {getattr(dxy, 'market_regime', 'neutral')} market sentiment.",
            instrument_implications={symbol: f"Deterministic macro context aligning with institutional {usd_bias.value.lower()} flow."},
            supporting_evidence=[f"Factual DXY trend direction: {dxy_trend}"],
            contradicting_evidence=[f"Event volatility risk: {len(hi_events)} high impact releases scheduled"],
            risk_level=risk_level,
            data_gaps=[reason],
            generated_at=datetime.now(timezone.utc),
            provider=provider,
            model=model,
            status="FALLBACK_QUANT",
            cached=False,
        )

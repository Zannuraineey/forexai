from typing import Dict, List, Optional
from app.schemas.ai_macro_reasoning import SupportedModelInfo, SupportedProviderInfo
from app.services.ai.providers.base_provider import BaseAIProvider
from app.services.ai.providers.openai_compatible_provider import OpenAICompatibleProvider
from app.services.ai.providers.gemini_provider import GeminiProvider

class AIProviderRegistry:
    """
    Central registry for AI providers and model catalogues.
    Enforces Groq as the default provider, with xAI Grok, Gemini, OpenAI, and DeepSeek as supported options.
    """

    PROVIDERS: Dict[str, SupportedProviderInfo] = {
        "groq": SupportedProviderInfo(
            id="groq",
            name="Groq (Ultra-Fast Inference)",
            description="Ultra-low-latency inference engine powered by LPU hardware. Recommended for live market execution.",
            default_model="llama-3.3-70b-versatile",
            supports_custom_base_url=True,
            default_base_url="https://api.groq.com/openai/v1",
            models=[
                SupportedModelInfo(
                    id="llama-3.3-70b-versatile",
                    name="Llama 3.3 70B Versatile",
                    description="State-of-the-art open-weights reasoning model with 128k context window.",
                    context_window=128000,
                    is_default=True,
                ),
                SupportedModelInfo(
                    id="openai/gpt-oss-120b",
                    name="GPT-OSS 120B (Groq Hosted)",
                    description="High-capacity frontier open-weights model hosted on Groq LPUs.",
                    context_window=128000,
                    is_default=False,
                ),
                SupportedModelInfo(
                    id="openai/gpt-oss-20b",
                    name="GPT-OSS 20B (Groq Hosted)",
                    description="Ultra-fast low-latency analytical model hosted on Groq LPUs.",
                    context_window=64000,
                    is_default=False,
                ),
                SupportedModelInfo(
                    id="qwen/qwen3.8-27b",
                    name="Qwen 3.8 27B (Groq Hosted)",
                    description="High-reasoning quant model hosted on Groq LPUs.",
                    context_window=64000,
                    is_default=False,
                ),
                SupportedModelInfo(
                    id="llama-3.1-8b-instant",
                    name="Llama 3.1 8B Instant",
                    description="Sub-100ms ultra-fast execution model for rapid signal confirmation.",
                    context_window=128000,
                    is_default=False,
                ),
                SupportedModelInfo(
                    id="mixtral-8x7b-32768",
                    name="Mixtral 8x7B Instruct",
                    description="High-throughput mixture-of-experts model for macro analysis.",
                    context_window=32768,
                    is_default=False,
                ),
            ],
        ),
        "xai": SupportedProviderInfo(
            id="xai",
            name="xAI Grok",
            description="Frontier reasoning models with real-time world knowledge from xAI.",
            default_model="grok-2-latest",
            supports_custom_base_url=True,
            default_base_url="https://api.x.ai/v1",
            models=[
                SupportedModelInfo(
                    id="grok-2-latest",
                    name="Grok 2 Latest",
                    description="Flagship reasoning with strong macroeconomic and financial logic.",
                    context_window=131072,
                    is_default=True,
                ),
                SupportedModelInfo(
                    id="grok-2",
                    name="Grok 2",
                    description="Stable enterprise Grok 2 model checkpoint.",
                    context_window=131072,
                    is_default=False,
                ),
                SupportedModelInfo(
                    id="grok-beta",
                    name="Grok Beta",
                    description="Direct access to xAI beta reasoning weights.",
                    context_window=131072,
                    is_default=False,
                ),
            ],
        ),
        "gemini": SupportedProviderInfo(
            id="gemini",
            name="Google Gemini",
            description="Multimodal frontier AI from Google DeepMind with expansive context windows.",
            default_model="gemini-1.5-flash",
            supports_custom_base_url=False,
            default_base_url="https://generativelanguage.googleapis.com/v1beta",
            models=[
                SupportedModelInfo(
                    id="gemini-1.5-flash",
                    name="Gemini 1.5 Flash",
                    description="Fast and versatile multimodal model optimized for frequency.",
                    context_window=1000000,
                    is_default=True,
                ),
                SupportedModelInfo(
                    id="gemini-2.0-flash",
                    name="Gemini 2.0 Flash",
                    description="Next-generation reasoning with enhanced math and coding speed.",
                    context_window=1000000,
                    is_default=False,
                ),
                SupportedModelInfo(
                    id="gemini-1.5-pro",
                    name="Gemini 1.5 Pro",
                    description="Deep multi-document reasoning for complex macro thematic analysis.",
                    context_window=2000000,
                    is_default=False,
                ),
            ],
        ),
        "openai": SupportedProviderInfo(
            id="openai",
            name="OpenAI GPT",
            description="Industry standard generative models from OpenAI.",
            default_model="gpt-4o-mini",
            supports_custom_base_url=True,
            default_base_url="https://api.openai.com/v1",
            models=[
                SupportedModelInfo(
                    id="gpt-4o-mini",
                    name="GPT-4o Mini",
                    description="Affordable and fast intelligent model for everyday macro reasoning.",
                    context_window=128000,
                    is_default=True,
                ),
                SupportedModelInfo(
                    id="gpt-4o",
                    name="GPT-4o Omnimodal",
                    description="Flagship high-intelligence model for deep structural reasoning.",
                    context_window=128000,
                    is_default=False,
                ),
            ],
        ),
        "deepseek": SupportedProviderInfo(
            id="deepseek",
            name="DeepSeek AI",
            description="High-performance open-source foundation models from DeepSeek.",
            default_model="deepseek-chat",
            supports_custom_base_url=True,
            default_base_url="https://api.deepseek.com",
            models=[
                SupportedModelInfo(
                    id="deepseek-chat",
                    name="DeepSeek V3 Chat",
                    description="General purpose chat and analytical model.",
                    context_window=64000,
                    is_default=True,
                ),
                SupportedModelInfo(
                    id="deepseek-reasoner",
                    name="DeepSeek R1 Reasoner",
                    description="Reinforcement-learning-driven chain-of-thought mathematical reasoning model.",
                    context_window=64000,
                    is_default=False,
                ),
            ],
        ),
    }

    @classmethod
    def get_supported_providers(cls) -> List[SupportedProviderInfo]:
        """Returns all configured provider profiles."""
        return list(cls.PROVIDERS.values())

    @classmethod
    def get_provider_info(cls, provider_id: str) -> Optional[SupportedProviderInfo]:
        return cls.PROVIDERS.get(provider_id.lower())

    @classmethod
    def create_provider(
        cls,
        provider_id: str,
        api_key: str,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> BaseAIProvider:
        """
        Factory method instantiating the appropriate BaseAIProvider subclass.
        """
        p_id = (provider_id or "groq").lower()
        info = cls.PROVIDERS.get(p_id) or cls.PROVIDERS["groq"]
        eff_model = model or info.default_model

        if p_id == "gemini":
            return GeminiProvider(api_key=api_key, model=eff_model, base_url=base_url)
        elif p_id in ("groq", "xai", "openai", "deepseek"):
            return OpenAICompatibleProvider(
                api_key=api_key,
                model=eff_model,
                default_base_url=info.default_base_url or "https://api.openai.com/v1",
                base_url=base_url,
                provider_name=info.name,
            )
        else:
            return OpenAICompatibleProvider(
                api_key=api_key,
                model=eff_model,
                default_base_url="https://api.openai.com/v1",
                base_url=base_url,
                provider_name="Generic AI Provider",
            )

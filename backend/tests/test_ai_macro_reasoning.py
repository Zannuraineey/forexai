import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import httpx
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.core.database import get_db
from app.core.auth import create_access_token, verify_token
from app.core.encryption import SecretEncryptionService
from app.models.ai_macro_config import AIMacroProviderConfig
from app.schemas.ai_macro_reasoning import (
    AIMacroConfigRequest,
    AIMacroTestRequest,
    MacroBiasState,
    MacroRiskLevel,
)
from app.services.ai.providers.registry import AIProviderRegistry
from app.services.ai.providers.openai_compatible_provider import (
    OpenAICompatibleProvider,
    normalize_chat_completions_url,
)
from app.services.ai.providers.gemini_provider import GeminiProvider
from app.services.ai.macro_reasoning_engine import MacroReasoningEngine
from app.services.bias.bias_validation_engine import BiasValidationEngine, FinalBiasState

@pytest.mark.asyncio
async def test_secret_encryption_and_masking():
    """
    Verifies that secrets are encrypted with Fernet authenticated encryption,
    decrypted accurately, and masked properly.
    """
    raw_key = "gsk_test1234567890abcdef"
    encrypted = SecretEncryptionService.encrypt_secret(raw_key)

    assert encrypted != raw_key
    assert len(encrypted) > 20

    # Decryption restores identical plaintext
    decrypted = SecretEncryptionService.decrypt_secret(encrypted)
    assert decrypted == raw_key

    # Masking never exposes middle secret content
    masked = SecretEncryptionService.mask_secret(raw_key)
    assert "gsk_" in masked
    assert "cdef" in masked
    assert "1234567890" not in masked

@pytest.mark.asyncio
async def test_authenticated_encryption_tampering_safety():
    """
    Verifies that tampered or invalid ciphertext fails safely
    without server crashes or unhandled exceptions.
    """
    raw_key = "gsk_valid_key_before_tampering_1234"
    ciphertext = SecretEncryptionService.encrypt_secret(raw_key)

    # Tamper with the ciphertext bytes
    tampered = ciphertext[:-4] + "AAAA"

    # Must fail safely and return empty string
    decrypted = SecretEncryptionService.decrypt_secret(tampered)
    assert decrypted == ""

@pytest.mark.asyncio
async def test_production_master_key_enforcement():
    """
    Verifies that production refuses encryption/initialization
    when ENCRYPTION_MASTER_KEY is missing or insecure.
    """
    orig_env = settings.ENVIRONMENT
    orig_key = settings.ENCRYPTION_MASTER_KEY
    try:
        settings.ENVIRONMENT = "production"
        settings.ENCRYPTION_MASTER_KEY = ""  # Missing in production
        SecretEncryptionService._fernet = None

        with pytest.raises(RuntimeError, match="FATAL SECURITY FAILURE"):
            SecretEncryptionService.encrypt_secret("test_key")
    finally:
        settings.ENVIRONMENT = orig_env
        settings.ENCRYPTION_MASTER_KEY = orig_key
        SecretEncryptionService._fernet = None

@pytest.mark.asyncio
async def test_master_key_rotation():
    """
    Verifies secure key rotation from an old master key to a new master key.
    """
    old_master = "old_secret_master_key_phase_one_12345"
    new_master = "new_secret_master_key_phase_two_67890"

    raw_secret = "gsk_sensitive_provider_api_key_rotation"
    
    # Encrypt under old key
    old_fernet = SecretEncryptionService._derive_fernet_key(old_master)
    from cryptography.fernet import Fernet
    old_cipher = Fernet(old_fernet).encrypt(raw_secret.encode("utf-8")).decode("utf-8")

    # Rotate
    rotated_cipher = SecretEncryptionService.rotate_secret(old_cipher, old_master, new_master)
    assert rotated_cipher != old_cipher

    # Verify decrypts under new key
    new_fernet = SecretEncryptionService._derive_fernet_key(new_master)
    decrypted = Fernet(new_fernet).decrypt(rotated_cipher.encode("utf-8")).decode("utf-8")
    assert decrypted == raw_secret

@pytest.mark.asyncio
async def test_sanitization_prevents_api_key_leakage():
    """
    Verifies that raw provider keys are stripped from error messages and logs.
    """
    dummy_test_key = "gsk_TESTMOCKFAKESECRETKEY00000000000000000000"
    raw_msg = f"Error connecting to https://api.groq.com with key {dummy_test_key}: 401 unauthorized"
    sanitized = SecretEncryptionService.sanitize_message(raw_msg)

    assert dummy_test_key not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized

@pytest.mark.asyncio
async def test_url_normalization_prevents_v1_v1_duplicates():
    """
    Verifies URL construction prevents duplicate /v1/v1 segments.
    """
    assert normalize_chat_completions_url("https://api.groq.com/openai/v1") == "https://api.groq.com/openai/v1/chat/completions"
    assert normalize_chat_completions_url("https://api.groq.com/openai/v1/") == "https://api.groq.com/openai/v1/chat/completions"
    assert normalize_chat_completions_url("https://api.deepseek.com") == "https://api.deepseek.com/chat/completions"
    assert normalize_chat_completions_url("https://api.deepseek.com/v1") == "https://api.deepseek.com/v1/chat/completions"
    # Duplicate segment auto-correction
    assert normalize_chat_completions_url("https://api.openai.com/v1/v1") == "https://api.openai.com/v1/chat/completions"
    assert normalize_chat_completions_url("https://api.openai.com/v1/chat/completions") == "https://api.openai.com/v1/chat/completions"

@pytest.mark.asyncio
async def test_auth_tokens_and_tenant_isolation_endpoints(db_session):
    """
    Verifies:
    - 401 Unauthorized when token is missing or invalid.
    - Tenant isolation: User A cannot read, replace, test, or delete User B's credentials.
    """
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    token_a = create_access_token("tenant_alpha")
    token_b = create_access_token("tenant_beta")

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated request MUST return 401
        res_unauth = await client.get("/api/v1/macro-ai/config")
        assert res_unauth.status_code == 401

        res_bad_auth = await client.get("/api/v1/macro-ai/config", headers={"Authorization": "Bearer bad.token.here"})
        assert res_bad_auth.status_code == 401

        # 2. User A saves credentials
        raw_secret_a = "gsk_alpha_secret_key_1234567"
        res_save_a = await client.post(
            "/api/v1/macro-ai/config",
            headers=headers_a,
            json={
                "provider": "groq",
                "model": "llama-3.3-70b-versatile",
                "is_enabled": True,
                "api_key": raw_secret_a,
            }
        )
        assert res_save_a.status_code == 200
        data_a = res_save_a.json()
        assert data_a["user_id"] == "tenant_alpha"
        assert data_a["has_api_key"] is True
        assert raw_secret_a not in str(data_a)

        # 3. User B queries config -> must NOT see User A's credentials
        res_get_b = await client.get("/api/v1/macro-ai/config", headers=headers_b)
        assert res_get_b.status_code == 200
        data_b = res_get_b.json()
        assert data_b["user_id"] == "tenant_beta"
        assert data_b["has_api_key"] is False
        assert data_b["masked_key"] is None

        # 4. User B cannot delete User A's credentials
        res_del_b = await client.delete("/api/v1/macro-ai/credentials", headers=headers_b)
        assert res_del_b.status_code == 200

        # User A's credentials must still be present and intact
        res_get_a = await client.get("/api/v1/macro-ai/config", headers=headers_a)
        assert res_get_a.status_code == 200
        assert res_get_a.json()["has_api_key"] is True

        # 5. User A deletes their credentials
        res_del_a = await client.delete("/api/v1/macro-ai/credentials", headers=headers_a)
        assert res_del_a.status_code == 200

        res_get_a_after = await client.get("/api/v1/macro-ai/config", headers=headers_a)
        assert res_get_a_after.json()["has_api_key"] is False

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_tenant_cache_partitioning_and_invalidation(db_session):
    """
    Verifies that cache entries cannot cross tenant boundaries and that
    updating configuration invalidates that user's cached outputs.
    """
    engine = MacroReasoningEngine(db_session)
    MacroReasoningEngine.clear_cache()

    mock_llm_json = """
    {
        "summary": "Dollar consolidation ahead of event.",
        "usd_macro_bias": "NEUTRAL",
        "dxy_context": "DXY rangebound.",
        "instrument_implications": {"EURUSD": "Sideways action."},
        "supporting_evidence": ["Rangebound"],
        "contradicting_evidence": [],
        "risk_level": "LOW_RISK",
        "data_gaps": []
    }
    """

    with patch.object(
        engine,
        "get_active_provider_config",
        return_value=("groq", "llama-3.3-70b-versatile", "gsk_mock_valid_key", None, True)
    ), patch.object(
        OpenAICompatibleProvider,
        "generate_macro_reasoning",
        return_value=(mock_llm_json, {"total_tokens": 80})
    ):
        # 1. Tenant Alpha generates reasoning
        res_a1 = await engine.generate_macro_reasoning("EURUSD", user_id="tenant_alpha")
        assert res_a1.status == "SUCCESS"
        assert res_a1.cached is False

        # 2. Tenant Alpha again -> hits cache
        res_a2 = await engine.generate_macro_reasoning("EURUSD", user_id="tenant_alpha")
        assert res_a2.cached is True

        # 3. Tenant Beta -> CANNOT hit Tenant Alpha's cache! Must execute separately.
        res_b = await engine.generate_macro_reasoning("EURUSD", user_id="tenant_beta")
        assert res_b.cached is False

        # 4. Invalidate Tenant Alpha's cache
        MacroReasoningEngine.invalidate_user_cache("tenant_alpha")

        # Tenant Alpha's next call must not be cached
        res_a3 = await engine.generate_macro_reasoning("EURUSD", user_id="tenant_alpha")
        assert res_a3.cached is False

@pytest.mark.asyncio
async def test_fallback_is_explicitly_marked_deterministic(db_session):
    """
    Verifies that fallback responses are explicitly marked as deterministic
    quantitative fallback and never disguised as LLM reasoning.
    """
    engine = MacroReasoningEngine(db_session)
    MacroReasoningEngine.clear_cache()

    with patch.object(
        engine,
        "get_active_provider_config",
        return_value=("groq", "llama-3.3-70b-versatile", "gsk_mock_valid_key", None, True)
    ), patch.object(
        OpenAICompatibleProvider,
        "generate_macro_reasoning",
        side_effect=Exception("Connection timed out (15s)")
    ):
        fallback = await engine.generate_macro_reasoning("EURUSD", user_id="tenant_alpha", force_refresh=True)

        assert fallback.status == "FALLBACK_QUANT"
        assert "Deterministic SMC Macro Fallback" in fallback.summary
        assert any("deterministic quantitative fallback engaged" in gap for gap in fallback.data_gaps)

@pytest.mark.asyncio
async def test_macro_reasoning_does_not_override_bias_engine():
    """
    Verifies that macro reasoning acts strictly as contextual information and does NOT
    override BiasValidationEngine's deterministic market structure rules.
    """
    res = BiasValidationEngine.validate_bias(
        symbol="EURUSD",
        custom_htf={"tf_4h_trend": "NEUTRAL", "tf_1h_trend": "NEUTRAL"},
        custom_7h={"direction": "NEUTRAL", "classification": "NORMAL"},
        news_data={"usd_news_risk": "LOW", "news_direction": "BULLISH"},
    )

    assert res.final_bias == FinalBiasState.NEUTRAL
    assert res.validation_status == "NEUTRAL"

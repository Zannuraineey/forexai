from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.auth import get_current_user_id
from app.core.encryption import SecretEncryptionService
from app.models.ai_macro_config import AIMacroProviderConfig
from app.schemas.ai_macro_reasoning import (
    AIMacroConfigRequest,
    AIMacroConfigSafeRead,
    AIMacroTestRequest,
    AIMacroTestResponse,
    SupportedProviderInfo,
    AIMacroReasoningOutput,
)
from app.services.ai.providers.registry import AIProviderRegistry
from app.services.ai.macro_reasoning_engine import MacroReasoningEngine

router = APIRouter(prefix="/macro-ai", tags=["AI Macro Reasoning"])

@router.get("/providers", response_model=List[SupportedProviderInfo])
async def get_supported_providers():
    """
    Returns list of supported AI providers, descriptions, and tested model catalogs.
    Public metadata endpoint.
    """
    return AIProviderRegistry.get_supported_providers()

@router.get("/config", response_model=AIMacroConfigSafeRead)
async def get_macro_ai_config(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves safe metadata for the active AI Macro configuration for the authenticated user.
    CRITICAL SECURITY INVARIANTS:
    - Derives identity strictly from verified token, never trusting caller query params.
    - Never exposes plaintext API keys to clients, responses, or logs.
    """
    stmt = select(AIMacroProviderConfig).where(AIMacroProviderConfig.user_id == current_user_id)
    res = await db.execute(stmt)
    config = res.scalar_one_or_none()

    if not config:
        # Default initial configuration: Groq (Llama 3.3) for this tenant
        return AIMacroConfigSafeRead(
            user_id=current_user_id,
            provider="groq",
            model="llama-3.3-70b-versatile",
            is_enabled=True,
            has_api_key=False,
            masked_key=None,
            api_base_url=None,
            last_tested_at=None,
            last_test_status="NOT_TESTED",
            last_test_latency_ms=None,
            last_test_error=None,
            updated_at_utc=None,
        )

    has_key = bool(config.encrypted_api_key)
    masked = None
    if has_key:
        decrypted = SecretEncryptionService.decrypt_secret(config.encrypted_api_key)
        masked = SecretEncryptionService.mask_secret(decrypted)

    return AIMacroConfigSafeRead(
        user_id=config.user_id,
        provider=config.provider,
        model=config.model,
        is_enabled=config.is_enabled,
        has_api_key=has_key,
        masked_key=masked,
        api_base_url=config.api_base_url,
        last_tested_at=config.last_tested_at,
        last_test_status=config.last_test_status,
        last_test_latency_ms=config.last_test_latency_ms,
        last_test_error=config.last_test_error,
        updated_at_utc=config.updated_at_utc,
    )

@router.post("/config", response_model=AIMacroConfigSafeRead)
async def save_macro_ai_config(
    payload: AIMacroConfigRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Saves or updates AI provider settings for the authenticated user.
    Encrypts the API key at rest using Fernet authenticated encryption.
    """
    stmt = select(AIMacroProviderConfig).where(AIMacroProviderConfig.user_id == current_user_id)
    res = await db.execute(stmt)
    config = res.scalar_one_or_none()

    if not config:
        config = AIMacroProviderConfig(user_id=current_user_id)
        db.add(config)

    config.provider = payload.provider.lower()
    config.model = payload.model
    config.is_enabled = payload.is_enabled
    config.api_base_url = payload.api_base_url
    config.updated_at_utc = datetime.now(timezone.utc)

    # Only overwrite encrypted key if a new non-empty key was explicitly supplied
    if payload.api_key is not None and payload.api_key.strip():
        config.encrypted_api_key = SecretEncryptionService.encrypt_secret(payload.api_key.strip())
        # Reset test status upon key change
        config.last_test_status = "NOT_TESTED"
        config.last_test_error = None

    await db.commit()
    await db.refresh(config)

    # Invalidate cache for this specific user
    MacroReasoningEngine.invalidate_user_cache(current_user_id)

    has_key = bool(config.encrypted_api_key)
    masked = None
    if has_key:
        decrypted = SecretEncryptionService.decrypt_secret(config.encrypted_api_key)
        masked = SecretEncryptionService.mask_secret(decrypted)

    return AIMacroConfigSafeRead(
        user_id=config.user_id,
        provider=config.provider,
        model=config.model,
        is_enabled=config.is_enabled,
        has_api_key=has_key,
        masked_key=masked,
        api_base_url=config.api_base_url,
        last_tested_at=config.last_tested_at,
        last_test_status=config.last_test_status,
        last_test_latency_ms=config.last_test_latency_ms,
        last_test_error=config.last_test_error,
        updated_at_utc=config.updated_at_utc,
    )

@router.post("/test", response_model=AIMacroTestResponse)
async def test_provider_connection(
    payload: AIMacroTestRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Tests connectivity to the AI provider with a lightweight health probe.
    Can test with an explicit temporary API key from payload or the stored encrypted key.
    Strictly isolated to current_user_id.
    """
    stmt = select(AIMacroProviderConfig).where(AIMacroProviderConfig.user_id == current_user_id)
    res = await db.execute(stmt)
    config = res.scalar_one_or_none()

    provider_id = (payload.provider or (config.provider if config else "groq")).lower()
    model_id = payload.model or (config.model if config else "llama-3.3-70b-versatile")
    base_url = payload.api_base_url or (config.api_base_url if config else None)

    # Determine key: explicit payload key > stored encrypted key > environment key
    key = payload.api_key
    if not key and config and config.encrypted_api_key:
        key = SecretEncryptionService.decrypt_secret(config.encrypted_api_key)

    if not key:
        # Check environment variable
        engine = MacroReasoningEngine(db)
        key = engine._get_server_env_key(provider_id)

    if not key:
        return AIMacroTestResponse(
            status="FAILED",
            provider=provider_id,
            model=model_id,
            latency_ms=0,
            message="No API key found. Enter an API key to test.",
            error="MISSING_API_KEY",
        )

    provider = AIProviderRegistry.create_provider(
        provider_id=provider_id,
        api_key=key,
        model=model_id,
        base_url=base_url,
    )

    success, latency_ms, msg = await provider.test_connection()

    # Update diagnostic records if config exists for this authenticated user
    if config:
        config.last_tested_at = datetime.now(timezone.utc)
        config.last_test_status = "SUCCESS" if success else "FAILED"
        config.last_test_latency_ms = latency_ms
        config.last_test_error = None if success else SecretEncryptionService.sanitize_message(msg)
        await db.commit()

    return AIMacroTestResponse(
        status="SUCCESS" if success else "FAILED",
        provider=provider_id,
        model=model_id,
        latency_ms=latency_ms,
        message=SecretEncryptionService.sanitize_message(msg),
        error=None if success else SecretEncryptionService.sanitize_message(msg),
    )

@router.delete("/credentials", status_code=status.HTTP_200_OK)
async def remove_provider_credentials(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Removes stored API key credentials strictly for the authenticated user.
    """
    stmt = select(AIMacroProviderConfig).where(AIMacroProviderConfig.user_id == current_user_id)
    res = await db.execute(stmt)
    config = res.scalar_one_or_none()

    if config:
        config.encrypted_api_key = None
        config.last_test_status = "NOT_TESTED"
        config.last_test_latency_ms = None
        config.last_test_error = None
        config.updated_at_utc = datetime.now(timezone.utc)
        await db.commit()

    MacroReasoningEngine.invalidate_user_cache(current_user_id)
    return {"message": "Credentials successfully removed."}

@router.post("/reason", response_model=AIMacroReasoningOutput)
async def execute_macro_reasoning(
    symbol: str = Query("EURUSD", description="Currency symbol or market"),
    force_refresh: bool = Query(False, description="Bypass cache and force fresh generation"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates structured macro context analysis for a symbol strictly scoped to current_user_id.
    """
    engine = MacroReasoningEngine(db)
    return await engine.generate_macro_reasoning(
        symbol=symbol,
        user_id=current_user_id,
        force_refresh=force_refresh,
    )

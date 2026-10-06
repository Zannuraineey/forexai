from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.strategy_service import StrategyService
from app.schemas.strategy import (
    StrategySessionsConfig,
    StrategyInstructionRead,
    StrategyInstructionUpdate,
    InstructionVersionRead,
    RollbackVersionRequest,
)

router = APIRouter(prefix="/strategy", tags=["Strategy Instructions"])

VALID_SESSIONS = {"asian", "london", "new_york"}

@router.get("/sessions", response_model=StrategySessionsConfig)
async def get_all_session_strategies(db: AsyncSession = Depends(get_db)):
    """
    Returns the active natural-language instruction configuration for all trading sessions:
    Asian, London, and New York.
    """
    service = StrategyService(db)
    return await service.get_all_session_configs(user_id=1)

@router.get("/sessions/{session_name}", response_model=StrategyInstructionRead)
async def get_session_strategy(session_name: str, db: AsyncSession = Depends(get_db)):
    """
    Returns details and current active instruction version for a specific session.
    """
    s_name = session_name.lower()
    if s_name not in VALID_SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid session '{session_name}'. Must be one of {list(VALID_SESSIONS)}",
        )

    service = StrategyService(db)
    instruction = await service.get_or_create_instruction(user_id=1, session_name=s_name)
    active_ver = await service.get_active_version(instruction.id, instruction.current_version)

    return StrategyInstructionRead(
        id=instruction.id,
        user_id=instruction.user_id,
        session_name=instruction.session_name,
        is_enabled=instruction.is_enabled,
        current_version=instruction.current_version,
        created_at=instruction.created_at,
        updated_at=instruction.updated_at,
        active_prompt=active_ver.prompt_content if active_ver else None,
        versions=[InstructionVersionRead.model_validate(v) for v in instruction.versions],
    )

@router.put("/sessions/{session_name}", response_model=StrategyInstructionRead)
async def update_session_strategy(
    session_name: str,
    payload: StrategyInstructionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Updates the natural language instructions for a session.
    Automatically increments the version number and creates a new immutable version record.
    """
    s_name = session_name.lower()
    if s_name not in VALID_SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid session '{session_name}'. Must be one of {list(VALID_SESSIONS)}",
        )

    service = StrategyService(db)
    instruction = await service.update_instruction(
        user_id=1,
        session_name=s_name,
        new_prompt=payload.instructions,
        is_enabled=payload.is_enabled,
        change_summary=payload.change_summary,
    )
    active_ver = await service.get_active_version(instruction.id, instruction.current_version)

    return StrategyInstructionRead(
        id=instruction.id,
        user_id=instruction.user_id,
        session_name=instruction.session_name,
        is_enabled=instruction.is_enabled,
        current_version=instruction.current_version,
        created_at=instruction.created_at,
        updated_at=instruction.updated_at,
        active_prompt=active_ver.prompt_content if active_ver else None,
        versions=[InstructionVersionRead.model_validate(v) for v in instruction.versions],
    )

@router.get("/sessions/{session_name}/history", response_model=List[InstructionVersionRead])
async def get_session_instruction_history(
    session_name: str, db: AsyncSession = Depends(get_db)
):
    """
    Returns full version history and audit log for a session's strategy instructions.
    """
    s_name = session_name.lower()
    if s_name not in VALID_SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid session '{session_name}'. Must be one of {list(VALID_SESSIONS)}",
        )

    service = StrategyService(db)
    return await service.get_instruction_history(user_id=1, session_name=s_name)

@router.post("/sessions/{session_name}/rollback", response_model=StrategyInstructionRead)
async def rollback_session_instruction(
    session_name: str,
    payload: RollbackVersionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Rolls back instructions to a prior version number while preserving the unbroken audit log.
    """
    s_name = session_name.lower()
    if s_name not in VALID_SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid session '{session_name}'. Must be one of {list(VALID_SESSIONS)}",
        )

    service = StrategyService(db)
    try:
        instruction = await service.rollback_to_version(
            user_id=1,
            session_name=s_name,
            target_version=payload.target_version,
            reason=payload.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    active_ver = await service.get_active_version(instruction.id, instruction.current_version)

    return StrategyInstructionRead(
        id=instruction.id,
        user_id=instruction.user_id,
        session_name=instruction.session_name,
        is_enabled=instruction.is_enabled,
        current_version=instruction.current_version,
        created_at=instruction.created_at,
        updated_at=instruction.updated_at,
        active_prompt=active_ver.prompt_content if active_ver else None,
        versions=[InstructionVersionRead.model_validate(v) for v in instruction.versions],
    )

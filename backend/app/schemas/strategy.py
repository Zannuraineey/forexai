from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

class InstructionVersionBase(BaseModel):
    version: int
    prompt_content: str
    change_summary: Optional[str] = None

class InstructionVersionCreate(BaseModel):
    prompt_content: str
    change_summary: Optional[str] = "Updated instructions"

class InstructionVersionRead(InstructionVersionBase):
    id: int
    instruction_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SessionConfigItem(BaseModel):
    enabled: bool = True
    instructions: str
    version: Optional[int] = None
    updated_at: Optional[datetime] = None

class StrategySessionsConfig(BaseModel):
    asian: SessionConfigItem
    london: SessionConfigItem
    new_york: SessionConfigItem

class StrategyInstructionRead(BaseModel):
    id: int
    user_id: int
    session_name: str
    is_enabled: bool
    current_version: int
    created_at: datetime
    updated_at: datetime
    active_prompt: Optional[str] = None
    versions: List[InstructionVersionRead] = []

    model_config = ConfigDict(from_attributes=True)

class StrategyInstructionUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    instructions: Optional[str] = None
    change_summary: Optional[str] = None

class RollbackVersionRequest(BaseModel):
    target_version: int
    reason: Optional[str] = "Rollback to previous version"

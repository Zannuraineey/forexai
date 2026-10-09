from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.models.strategy import StrategyInstruction, InstructionVersion
from app.schemas.strategy import (
    StrategySessionsConfig,
    SessionConfigItem,
    InstructionVersionRead,
    StrategyInstructionRead,
)

class StrategyService:
    """
    Manages session-specific natural language instructions in PostgreSQL.
    Enforces strict versioning, immutability of historical versions,
    and instantaneous runtime updates without modifying code.
    """

    DEFAULT_PROMPTS = {
        "asian": """### Strategy: MSNR Tokyo Accumulation & Classic A/V Range Model

1. Time Window & Killzone:
- Active Trading Window: 07:00 PM to 12:00 AM EST (00:00 to 05:00 UTC / Tokyo & Sydney Open).
- Peak Focus: 08:00 PM to 09:30 PM EST (Tokyo Cash Open volume injection).
- Favored Instruments: XAUUSD (Gold physical flows), XAGUSD (Silver), JPY Crosses (USDJPY, EURJPY, GBPJPY), AUDUSD.

2. MSNR Pre-Asia Dealing Range Definition:
- Identify key Malaysian Support & Resistance (MSNR) boundaries on the Line Chart:
  - Classic A (Peak Resistance / Buy-Side Liquidity - BSL) at session highs.
  - Classic V (Trough Support / Sell-Side Liquidity - SSL) at session lows.
- Operating Environment: Asian session represents the Accumulation (A) Phase of Quarterly Theory.
- Price builds internal range liquidity (IRL). Look for mean reversion back to 50% Consequent Encroachment (CE), not runaway trends.

3. The Tokyo Open Liquidity Sweep (MISS / Fakeout):
- Bearish Setup: Price spikes above the Classic A Asian High around Tokyo Open (08:00-09:00 PM EST), sweeps BSL with a wick, and rejects with candle bodies closing inside the zone.
- Bullish Setup: Price dips below the Classic V Asian Low around Tokyo Open, sweeps SSL with a wick, and rejects with candle bodies closing inside the zone.

4. Entry Trigger at 50% Consequent Encroachment (CE):
- Following the sweep, require Market Structure Shift (MSS) on lower timeframes (M1, M5, M15).
- Calculate 50% CE:
  - Bullish: CE = (Open + Low) / 2 of the reaction candle.
  - Bearish: CE = (Open + High) / 2 of the reaction candle.
- Entry: Enter limit or market order upon retest tapping the 50% CE level.

5. Risk Management & Invalidation:
- Stop Loss: 1-2 pips beyond the MSNR manipulation wick extreme.
- Take Profit / Targets:
  - Target 1: Range Equilibrium (50% midpoint CE of the entire Asian dealing range).
  - Target 2: Opposing boundary (Classic A high or Classic V low).
- Risk-to-Reward ratio: Minimum 1:1.5 to 1:2.0.""",
        "london": """### Strategy: MSNR London Manipulation & RBS/SBR Flip Expansion Model

1. Time Window & Killzone:
- Active Trading Window: 03:00 AM to 04:30 AM EST (08:00 AM to 09:30 AM London/UTC).
- Strict Rule: Time is the primary filter. Only execute setups during this 90-minute institutional window.

2. MSNR Pre-Market Dealing Range & Flip Zones:
- Identify pre-market MSNR levels from the Asian session and prior day:
  - Classic A (Asian High / BSL) & Classic V (Asian Low / SSL).
  - Prior broken levels: RBS (Resistance Becomes Support) and SBR (Support Becomes Resistance).
- Freshness Rule: Prioritize FRESH zones (0-1 prior touch). Avoid exhausted zones (3+ touches).

3. The London Manipulation (Judas Swing / MISS):
- Bearish Setup: 03:00 AM candle sweeps Asian High into a Higher Timeframe (H4/H1) MSNR Resistance / SBR zone, rejects leaving a prominent upper wick.
- Bullish Setup: 03:00 AM candle sweeps Asian Low into a Higher Timeframe (H4/H1) MSNR Support / RBS zone, rejects leaving a prominent lower wick.

4. Confirmation & 50% CE Retest:
- Require aggressive displacement closing back inside the MSNR range.
- Lower timeframe (M15/M5) Market Structure Shift (MSS).
- Entry: Enter on the retest of the 50% Consequent Encroachment (CE) of the MSNR zone or reaction order block.

5. Risk Management & Invalidation:
- Stop Loss: 1-2 pips beyond the manipulation wick extreme.
- Target: Opposing session liquidity pool (Asian High/Low), targeting 1:2.0 to 1:3.0 Risk-to-Reward (R:R).""",
        "new_york": """### Strategy: Alchemist Daily Profile #2 NY Reversal & Precious Metals SMT Model

1. Time Window & Killzone:
- Active Trading Window: 08:30 AM to 11:30 AM EST (12:30 to 15:30 UTC / New York AM Session).
- Peak Focus: 09:30 AM to 10:30 AM EST (NYSE Equity Opening Bell & Initial Balance).

2. Daily Profile #2 Framework:
- Detects the institutional "Reversal of the Day" where London manipulation pushes price into HTF MSNR levels, and New York reverses the market toward External Range Liquidity (ERL).
- Primary Focus: Gold (XAUUSD) and Silver (XAGUSD).

3. Intermarket SMT Divergence Confirmation:
- Bullish SMT: Silver (XAGUSD) sweeps below its session low to a lower low, but Gold (XAUUSD) makes a Higher Low, respecting a fresh MSNR Classic V or RBS Support zone. (Gold signals accumulation).
- Bearish SMT: Silver (XAGUSD) sweeps above its session high to a higher high, but Gold (XAUUSD) makes a Lower High, respecting a fresh MSNR Classic A or SBR Resistance zone. (Gold signals distribution).

4. Execution at 50% Consequent Encroachment (CE):
- Require lower timeframe (M15/M5) Market Structure Shift (MSS).
- Calculate 50% CE of the MSNR zone / reaction candle.
- Entry: Limit or market execution upon retest of 50% CE.

5. Risk Management & Multi-Target Take Profits:
- Stop Loss: 1-2 pips beyond the displacement candle extreme or zone wick.
- Target 1 (T1): Opposing session liquidity (London or Pre-market extreme) -> 1:2.0 R:R.
- Target 2 (T2): Higher Timeframe External Range Liquidity (ERL) -> 1:3.5+ R:R.""",
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_instruction(
        self, user_id: int, session_name: str
    ) -> StrategyInstruction:
        """
        Retrieves the strategy instruction for a session, initializing it if not present.
        """
        stmt = (
            select(StrategyInstruction)
            .options(selectinload(StrategyInstruction.versions))
            .where(
                StrategyInstruction.user_id == user_id,
                StrategyInstruction.session_name == session_name.lower(),
            )
        )
        res = await self.db.execute(stmt)
        instruction = res.scalar_one_or_none()

        if not instruction:
            # Initialize with default prompt version 1
            instruction = StrategyInstruction(
                user_id=user_id,
                session_name=session_name.lower(),
                is_enabled=True,
                current_version=1,
            )
            self.db.add(instruction)
            await self.db.flush()

            default_text = self.DEFAULT_PROMPTS.get(
                session_name.lower(), "Session natural language strategy instructions."
            )
            v1 = InstructionVersion(
                instruction_id=instruction.id,
                version=1,
                prompt_content=default_text,
                change_summary="Initial system default instruction set",
            )
            self.db.add(v1)
            await self.db.commit()
            await self.db.refresh(instruction)

        return instruction

    async def update_instruction(
        self,
        user_id: int,
        session_name: str,
        new_prompt: Optional[str] = None,
        is_enabled: Optional[bool] = None,
        change_summary: Optional[str] = None,
    ) -> StrategyInstruction:
        """
        Updates session instructions. If new_prompt is supplied, increments version
        and creates a new immutable version record.
        """
        instruction = await self.get_or_create_instruction(user_id, session_name)

        if is_enabled is not None:
            instruction.is_enabled = is_enabled

        if new_prompt is not None and new_prompt.strip():
            # Check if content actually changed
            current_active_v = await self.get_active_version(instruction.id, instruction.current_version)
            if not current_active_v or current_active_v.prompt_content != new_prompt.strip():
                next_version = instruction.current_version + 1
                new_ver = InstructionVersion(
                    instruction_id=instruction.id,
                    version=next_version,
                    prompt_content=new_prompt.strip(),
                    change_summary=change_summary or f"Updated instruction to version {next_version}",
                )
                self.db.add(new_ver)
                instruction.current_version = next_version

        instruction.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(instruction)
        return instruction

    async def get_active_version(
        self, instruction_id: int, version_num: int
    ) -> Optional[InstructionVersion]:
        stmt = select(InstructionVersion).where(
            InstructionVersion.instruction_id == instruction_id,
            InstructionVersion.version == version_num,
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_all_session_configs(self, user_id: int = 1) -> StrategySessionsConfig:
        """
        Returns full configuration dictionary in exact schema:
        {
          "asian": {"enabled": true, "instructions": "...", "version": 1},
          "london": {"enabled": true, "instructions": "...", "version": 1},
          "new_york": {"enabled": true, "instructions": "...", "version": 1}
        }
        """
        configs = {}
        for session_name in ["asian", "london", "new_york"]:
            inst = await self.get_or_create_instruction(user_id, session_name)
            active_ver = await self.get_active_version(inst.id, inst.current_version)
            configs[session_name] = SessionConfigItem(
                enabled=inst.is_enabled,
                instructions=active_ver.prompt_content if active_ver else "",
                version=inst.current_version,
                updated_at=inst.updated_at,
            )

        return StrategySessionsConfig(
            asian=configs["asian"],
            london=configs["london"],
            new_york=configs["new_york"],
        )

    async def get_instruction_history(
        self, user_id: int, session_name: str
    ) -> List[InstructionVersionRead]:
        """
        Lists all historical versions for a given session.
        """
        inst = await self.get_or_create_instruction(user_id, session_name)
        stmt = (
            select(InstructionVersion)
            .where(InstructionVersion.instruction_id == inst.id)
            .order_by(desc(InstructionVersion.version))
        )
        res = await self.db.execute(stmt)
        versions = res.scalars().all()
        return [InstructionVersionRead.model_validate(v) for v in versions]

    async def rollback_to_version(
        self, user_id: int, session_name: str, target_version: int, reason: Optional[str] = None
    ) -> StrategyInstruction:
        """
        Rollback strategy by creating a new version with content identical to target_version.
        Preserves an unbroken forward audit log.
        """
        inst = await self.get_or_create_instruction(user_id, session_name)
        target = await self.get_active_version(inst.id, target_version)
        if not target:
            raise ValueError(f"Version {target_version} not found for session '{session_name}'.")

        next_version = inst.current_version + 1
        rolled_back_ver = InstructionVersion(
            instruction_id=inst.id,
            version=next_version,
            prompt_content=target.prompt_content,
            change_summary=reason or f"Rollback to version {target_version}",
        )
        self.db.add(rolled_back_ver)
        inst.current_version = next_version
        inst.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(inst)
        return inst

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
        "asian": """### Strategy: Tokyo Sweep & Fractal Range Mean-Reversion Model

1. Time Window & Killzone:
- Active Trading Window: 07:00 PM to 12:00 AM EST (00:00 to 05:00 UTC / Tokyo & Sydney Open).
- Peak Focus: 08:00 PM to 09:30 PM EST (Tokyo Cash Open volume injection).
- Favored Instruments: JPY Crosses (USDJPY, EURJPY, GBPJPY), AUDUSD, XAUUSD (early Asia physical gold flows), Volatility/Crash/Boom synthetics.

2. Pre-Asia Dealing Range Definition:
- Identify the Pre-Asia / Sydney Range:
  - New York PM / Post-Close High and Low (05:00 PM - 07:00 PM EST).
  - Sydney Open initial range high (Buy-Side Liquidity) and low (Sell-Side Liquidity).
- Operating Environment: Asian session is primarily an Accumulation / Consolidation Range. Expect mean reversion, not runaway trends, unless catalyzed by BoJ or high-impact APAC news.

3. The Tokyo Open Liquidity Sweep:
- Bearish Setup: Price pushes above the Sydney/Pre-Asia High around Tokyo Open (08:00-09:00 PM EST), sweeps Buy-Side Liquidity (BSL), and sharply rejects back inside the range.
- Bullish Setup: Price dips below the Sydney/Pre-Asia Low around Tokyo Open, sweeps Sell-Side Liquidity (SSL), and sharply rejects back inside the range.

4. Lower Timeframe Confirmation & Entry (1m, 5m, 15m):
- Following the sweep, require a Market Structure Shift (MSS) back toward Equilibrium (50% of the session range).
- Formation of a clean Fair Value Gap (FVG) or Breaker Block.
- Entry: Enter on the retest of the FVG or Breaker Block.

5. Risk Management & Invalidation:
- Stop Loss: 1-2 pips beyond the Asian sweep wick extreme.
- Take Profit / Targets:
  - Primary Target: Range Equilibrium (50% midpoint) or the opposing boundary of the Sydney/Asia range.
  - Risk-to-Reward ratio: 1:1.5 to 1:2. Avoid forcing >1:3 targets during low-volatility Asian hours.
- State Evaluation:
  - VALID_SETUP: Pre-Asia high/low swept at Tokyo Open with confirmed MSS and FVG retest toward range midpoint.
  - POTENTIAL_SETUP: Price testing outer Asian range boundaries near Tokyo open, awaiting sweep.
  - WATCH: Mid-range chop with no liquidity sweep.
  - INVALIDATED: Manipulation high/low breached or structure breaks without rejection.""",
        "london": """### Strategy: Loz Tradez 3-Step London Session Model (1-Candle Expansion)

1. Time Window & Killzone:
- Active Trading Window: 03:00 AM to 04:30 AM EST (08:00 AM to 09:30 AM London/UTC).
- Strict Rule: Time is the primary filter. Only execute setups during this 90-minute window.

2. Pre-Market Dealing Range:
- Before 03:00 AM EST, establish the Pre-Market Range:
  - Asian Session High (Buy-Side Liquidity - BSL)
  - Asian Session Low (Sell-Side Liquidity - SSL)
  - 02:00 AM EST hourly swing high/low.
- Dealing Range Equilibrium (50%):
  - Premium Zone (>50%): Strictly look for Shorts after BSL is purged.
  - Discount Zone (<50%): Strictly look for Longs after SSL is purged.

3. The 3:00 AM Hourly Manipulation Candle:
- Bearish Setup: 03:00 AM candle sweeps Asian High or 02:00 AM High, purges liquidity, and rejects leaving a prominent upper wick.
- Bullish Setup: 03:00 AM candle sweeps Asian Low or 02:00 AM Low, purges liquidity, and rejects leaving a prominent lower wick.

4. Lower Timeframe Confirmation & Entry (1m, 5m, 15m):
- Following the sweep, require aggressive Displacement back inside the range.
- Market Structure Shift (MSS) breaking recent swing structure.
- Creation of a clean Fair Value Gap (FVG), Inefficiency, or Order Block.
- Entry: Enter on the retest of the newly created FVG or Breaker Block.

5. Risk Management & Invalidation:
- Stop Loss: 1-2 pips beyond the manipulation wick extreme. A breach of this high/low immediately invalidates the setup.
- Target: Opposing liquidity pool of the pre-market range (Asian High/Low), aiming for minimum 1:2 Risk-to-Reward (R:R).
- State Evaluation:
  - VALID_SETUP: Pre-market liquidity swept during 03:00-04:30 EST, displacement confirmed with MSS and FVG entry.
  - POTENTIAL_SETUP: Price approaching Asian High/Low near 03:00 AM EST, awaiting sweep and rejection.
  - WATCH: Outside killzone or consolidating within Asian range without sweep.
  - INVALIDATED: Manipulation extreme breached or displacement failed.""",
        "new_york": """### Strategy: Loz Tradez 9:30 AM Distribution & NY Expansion Model

1. Time Window & Killzone:
- Active Trading Window: 08:30 AM to 11:30 AM EST (New York AM Session).
- Peak Focus: 09:30 AM to 10:30 AM EST (NYSE Equity Opening Bell & Initial Balance).
- Strict Rule: High volatility injection occurs at 09:30 AM. Wait for the opening manipulation before entering.

2. Dealing Range & Key Reference Levels:
- London Session High & Low (Primary External Liquidity Pool).
- 08:00 AM to 09:30 AM Pre-Market Swing High and Low.
- Previous Day High / Low (PDH / PDL).
- Dealing Range Equilibrium (50%):
  - Premium (>50%): Look strictly for Shorts after Buy-Side Liquidity is swept.
  - Discount (<50%): Look strictly for Longs after Sell-Side Liquidity is swept.

3. The 9:30 AM Manipulation / Judas Swing:
- At or shortly after 09:30 AM EST, institutional algorithm sweeps key liquidity:
  - Bearish Setup: 09:30 candle spikes above London High or Pre-Market High, purges BSL, and violently rejects leaving an upper wick.
  - Bullish Setup: 09:30 candle drops below London Low or Pre-Market Low, purges SSL, and violently rejects leaving a lower wick.

4. Lower Timeframe Confirmation & Entry (1m, 5m, 15m):
- Require aggressive Displacement with candle bodies closing back inside the range.
- Clear Market Structure Shift (MSS) breaking internal swing structure.
- Formation of a clean Fair Value Gap (FVG), Inverted FVG (iFVG), or Order Block.
- Entry: Enter on the first retest of the FVG or Breaker Block.

5. Risk Management & Invalidation:
- Stop Loss: 1-2 pips beyond the 09:30 manipulation wick extreme. Breach of this level immediately invalidates the trade idea.
- Target: Opposing session liquidity (London Low if London High swept, or pre-market low), with minimum 1:2 Risk-to-Reward ratio (R:R).
- State Evaluation:
  - VALID_SETUP: London or pre-market extreme swept at 09:30 AM EST, followed by displacement, MSS, and FVG retest.
  - POTENTIAL_SETUP: Price approaching London High/Low ahead of or during 09:30 AM open.
  - WATCH: Choppy consolidation between 08:30-09:30 before the open, or outside NY killzone.
  - INVALIDATED: Manipulation extreme violated or displacement fails to materialize.""",
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

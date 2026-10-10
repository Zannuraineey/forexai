Prompt 1: more candles for sessions and the 7H profile
In backend/app/services/ai/ai_engine.py, execute_analysis loads only 60 candles per timeframe (.limit(60)). That is too short to build Asian/London/NY session levels and 7H profiles.
1. For the main timeframe, load enough candles to cover the last 36 hours (5m=432, 15m=144), filtered by timestamp_utc <= current_candle.timestamp_utc (no look-ahead).
2. For "1h", load at least 48 candles. For "4h", at least 30.
3. Pass the full lists into MarketContextEngine.generate_context and MarketContextAssembler.assemble.
4. In SessionEngine.evaluate_sessions, make sure the Asian window that ended earlier today (or started yesterday UTC) is still computed when the current time is in London or New York.
5. Add a pytest that feeds 36h of synthetic 5m candles at 13:00 UTC and asserts asian.high, asian.low and london.high are all non-null.   

Prompt 2: fix 7H profile completeness
In backend/app/services/profiling/seven_hour_profile_engine.py and schemas/seven_hour_profile.py:
1. Change min_candles_ratio_for_complete default from 1.0 to 0.85.
2. DAILY_ANCHOR with 7H blocks creates a 3-hour stub (21:00-24:00 UTC). Make the stub a COMPLETED profile only if it has >=85% of its own expected candles, or merge it into the next day's first block. Document the choice in the docstring.
3. If the latest block is IN_PROGRESS, still use the last COMPLETED profile as the bias source instead of returning INSUFFICIENT_DATA.
4. Add tests: one missing 1h candle still gives COMPLETED; two consecutive completed profiles produce a relationship (SUPPORT/CONTRADICT/NEUTRAL).

Prompt 3: remove DXY
Remove DXY from the trading logic:
1. ai_engine.py (~line 130): stop calling DXYService.calculate_dxy_index. Always set dxy_data to the UNAVAILABLE dict.
2. bias_validation_engine.py: make evaluate_dxy_relationship always return DXYRelationship.NEUTRAL. Remove DXY from the CONFLICTED conditions (~lines 437 and 493-510) and from the quality checks.
3. news_intelligence_engine.py (~line 62): remove allow_synthetic_fallback=True. If real data is missing, show "UNAVAILABLE" rather than a computed DXY.
4. Hide the DXY card in frontend/lib/screens/news_screen.dart.
Update the affected tests (test_bias_validation_engine.py, test_integration_gaps_audit.py).

Prompt 4: setups driven by session + 7H
In deterministic_provider.py, add a SessionProfileModel step before the sweep/MSS/FVG chain:
1. Bias = last COMPLETED 7H profile direction (and its relationship to the one before it).
2. Draw on liquidity = the previous session's high/low (Asia range for London, Asia+London for NY).
3. Valid setups only in the active session's killzone: sweep of that liquidity AGAINST the 7H bias, then exhaustion wick >=35%, MSS, FVG retest, R:R >=1.8.
4. Add ConditionStatus rows: "7H bias", "Prior session range available", "Sweep in active session".
5. Return POTENTIAL_SETUP if the 7H bias and the prior-session range exist and price is approaching the liquidity.
Keep the existing safety gates (geometry, bias CONFLICTED). Add tests per session.

Prompt 5: debug logging (run first if you like)
In session_scanner.py scan_cycle, log one line per symbol/timeframe: session, 7H status+direction, which session levels exist, and the first failed condition. At the end of the cycle, log a count by state (NO_SETUP/WATCH/POTENTIAL/VALID) and expose it on the scanner status endpoint.
Build the Flutter application with a professional, understated financial/trading-terminal aesthetic.

IMPORTANT:

I do NOT want the application to look AI-generated.

Do not use the common generic AI dashboard aesthetic.

Avoid:

* excessive gradients
* glowing effects
* neon colors
* futuristic graphics
* robot/AI illustrations
* brain graphics
* excessive rounded cards
* excessive glassmorphism
* huge headings
* unnecessary animations
* decorative elements that do not provide information
* "AI magic" visual effects
* excessive emojis
* generic startup/SaaS dashboard styling

The application should feel like a real financial market-analysis application designed by an experienced product designer.

Design principles:

1. Information first.
2. Clean typography.
3. Strong visual hierarchy.
4. Consistent spacing.
5. Minimal decoration.
6. Charts and market data should be the visual focus.
7. Use color primarily to communicate market state.
8. Keep the interface fast and responsive.
9. Avoid unnecessary animation.
10. Make the application feel trustworthy and professional.

The visual language should be inspired by professional trading terminals and financial applications, but do not copy any specific application's design.

Use:

* restrained color palette
* neutral backgrounds
* clear typography
* subtle borders/dividers
* compact market information
* simple navigation
* professional charts
* consistent number formatting
* clear status indicators

Do not make every piece of information a separate floating card.

## Main navigation

Use a simple bottom navigation:

Markets
Analysis
Alerts
Settings

## Markets screen

Show:

* watchlist
* symbol
* current price
* percentage change
* session
* market status

Example:

XAUUSD    2648.30    +0.47%
XAGUSD      31.42    -0.18%
EURUSD     1.1724    +0.12%

## Instrument screen

Show:

* symbol
* current price
* percentage change
* timeframe selector
* candlestick chart
* session information
* relevant market context

Example:

XAUUSD

2648.30
+0.47%

[1m] [5m] [15m] [1H] [4H]

[ Candlestick Chart ]

Session
London — Active

Market Context
Trend       —
Volatility  —
Structure   —
Range       —

Do not automatically label the market "BUY" or "SELL" unless the user's configured analysis actually produces that result.

## Analysis screen

This is where the AI analysis should appear, but it should still look like a professional market-analysis tool.

Do not make it look like a chatbot.

Show:

Symbol
Session
Time
Instruction version

Then:

Market Context

Analysis

Conditions
✓ Condition satisfied
— Condition not satisfied
× Condition invalidated

Conclusion

WATCH / NO SETUP / POTENTIAL SETUP / VALID SETUP

The exact conclusion must come from the analysis engine.

## Alerts screen

Use a chronological list of alerts.

Example:

10:42
XAUUSD
London

Potential setup detected

10:17
EURUSD
London

Condition invalidated

Do not use giant colorful alert cards.

## Settings

Include:

* symbols
* sessions
* timeframes
* notifications
* analysis instructions
* notification preferences
* data source
* app preferences

## UX REQUIREMENT

The user should immediately understand:

1. What markets are being watched.
2. Which session is active.
3. What the market is doing.
4. Whether the analysis engine has found anything.
5. Why an alert was generated.

The application should feel like a serious personal market-analysis tool, not an AI demo.

Before implementing the UI, create a design system containing:

* typography
* spacing
* colors
* borders
* buttons
* navigation
* status indicators
* chart styling
* market-state indicators

Keep the design system consistent throughout the entire application.

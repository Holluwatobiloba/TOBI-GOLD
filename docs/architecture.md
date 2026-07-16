# TOBI-XAUUSD: AI-Powered Trading Platform Architecture

## Core Tech Stack
- **System Name:** TOBI-XAUUSD Core Engine
- **Asset Focus:** XAUUSD (Spot Gold / US Dollar)
- **Language:** Python 3.11+
- **API Framework:** FastAPI
- **Database:** PostgreSQL (with numeric precision tracking)
- **Bot Library:** python-telegram-bot (Asyncio)

## Architectural Decisions
1. **API-First Design:** The Telegram bot serves exclusively as a secure interface, communicating with our central FastAPI backend to display XAUUSD signals, account balances, and risk parameters.
2. **Gold-Specific Mathematical Precision:** To eliminate catastrophic financial rounding errors, all price, pip, lot-sizing, and balance calculations will explicitly utilize fixed-point decimals rather than floating-point math.
3. **Macro Engine Integration:** The backend architecture will include a dedicated background layer for fetching economic calendar events. The AI core will use this data to calculate a "Volatility Threat Level" before executing gold trades.
4. **Broker Abstraction Layer:** The execution engine will isolate broker-specific protocols (like MT5 integration scripts) behind a generic interface, allowing us to swap brokers without touching our core trading logic.
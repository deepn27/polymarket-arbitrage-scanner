# Polymarket Arbitrage Scanner

## Overview
A real-time monitoring system that scans Polymarket prediction markets for arbitrage opportunities. When outcome prices sum to less than $1.00, risk-free profit exists.

## Project Architecture
```
polymarket-arbitrage-scanner/
├── main.py                    # FastAPI app entry point
├── config.py                  # Configuration settings
├── core/                      # Core business logic
│   ├── scanner.py            # Main scanning orchestration
│   ├── market_fetcher.py     # Polymarket API client
│   ├── arbitrage_detector.py # Arbitrage detection algorithms
│   └── price_analyzer.py     # Price calculations
├── models/                    # Data models
│   ├── market.py             # Market/Token Pydantic models
│   ├── opportunity.py        # Arbitrage opportunity models
│   └── database.py           # SQLite operations
├── api/                       # API layer
│   ├── routes.py             # REST API endpoints
│   └── websocket_manager.py  # WebSocket handling
├── services/                  # External services
│   └── notifications.py      # Discord alerts
├── static/                    # Frontend assets
│   ├── css/style.css
│   └── js/dashboard.js
└── templates/
    └── dashboard.html
```

## Tech Stack
- Python 3.11+
- FastAPI (web framework)
- SQLite with aiosqlite (database)
- WebSockets (real-time updates)
- httpx (async HTTP client)
- Vanilla HTML/CSS/JS (frontend)

## Running the App
The app runs on port 5000 with `python main.py`

## Key Features
1. Continuous market scanning every 10 seconds
2. Arbitrage detection with fee calculations (2% Polymarket fee)
3. Real-time WebSocket updates to dashboard
4. Historical opportunity tracking in SQLite
5. Optional Discord notifications

## Configuration
Set in `.env` or environment variables:
- `SCAN_INTERVAL_SECONDS`: Scan frequency (default: 10)
- `MIN_ARBITRAGE_PERCENT`: Minimum profit % to report (default: 0.5)
- `MIN_LIQUIDITY_USD`: Minimum market liquidity (default: 100)
- `DISCORD_WEBHOOK_URL`: Optional Discord alerts

## API Endpoints
- `GET /` - Dashboard
- `GET /api/status` - Scanner status
- `POST /api/start` - Start scanning
- `POST /api/stop` - Stop scanning
- `POST /api/scan` - Trigger single scan
- `GET /api/opportunities` - List opportunities
- `WS /ws` - WebSocket for real-time updates

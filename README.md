# APEX Trading OS v3.0 — Production-Ready Architecture

AI-powered forex trading system with all 12 upgrade plan items implemented.

## Quick Start

```bash
# Backend
pip install -r requirements.txt
cp .env.example .env   # add OANDA_ACCOUNT_ID, OANDA_API_KEY, AI keys
uvicorn api.main:app --reload --port 8000

# Frontend (new terminal)
cd web && npm install && npm run dev
# Open http://localhost:3000
```

## ✅ All 12 Implementation Guide Items

| # | Item | Module | Status |
|---|------|--------|--------|
| 1 | Central Risk Engine | `core/risk/risk_engine.py` | ✅ |
| 2 | Decouple Strategies from Execution | `TradeSignal` dataclass + Risk Engine gate | ✅ |
| 3 | Currency Exposure Control (max 40%) | `core/risk/exposure_manager.py` | ✅ |
| 4 | Correlation Risk Control (|r|>0.8 block) | `core/risk/correlation_manager.py` | ✅ |
| 5 | Realistic Backtesting (spread+slippage) | `core/backtest/walk_forward.py` | ✅ |
| 6 | Order Lifecycle State Machine | `core/execution/order_manager.py` | ✅ |
| 7 | Market Regime Enforcement | `core/market_regime.py` (gates strategies) | ✅ |
| 8 | Strategy Confidence Calibration | `StrategySignal.confidence` → Signal Combiner | ✅ |
| 9 | Portfolio Allocation Layer | `core/portfolio/allocator.py` | ✅ |
| 10 | Trade Dataset Collection | `training/collector.py` → `data/trade_dataset.csv` | ✅ |
| 11 | System Monitoring & Health Checks | `services/monitoring.py` | ✅ |
| 12 | Drawdown Kill Switch (15% threshold) | Built into `risk_engine.py` | ✅ |

## Target Architecture (as per guide)

```
Market Data → Feature Engineering → Strategy Engine (43 strats) →
Debate Engine → Signal Combiner → ML Probability Filter (≥65%) →
Risk Engine → Portfolio Allocator → Execution Engine →
Broker API → Trade Database → Model Training Pipeline
```

## Dashboard Design

Complete Gemini design system — fully working:
- Dark/light mode toggle
- 3D morphing metallic orb intro (Three.js, MeshDistortMaterial)
- Glassmorphism cards (backdrop-filter blur, no CSS variables)
- Equity growth area chart with gradient
- Neural Engine 3D emerald orb card
- Live AI signal feed
- All pages: Dashboard, AI Arena, Debate Room, Backtest, Strategy Lab, Risk Console

## API Endpoints

All upgrade guide endpoints available at `/api/v2/*`:
- `GET  /api/v2/risk-engine/status`
- `POST /api/v2/risk-engine/kill-switch/activate`
- `POST /api/v2/risk-engine/kill-switch/deactivate`
- `GET  /api/v2/exposure/summary`
- `GET  /api/v2/correlation/matrix`
- `GET  /api/v2/orders/summary`
- `GET  /api/v2/portfolio/summary`
- `POST /api/v2/portfolio/rebalance`
- `GET  /api/v2/dataset/stats`
- `GET  /api/v2/monitoring/health`
- `POST /api/v2/monitoring/run-checks`
- `GET  /api/v2/regime/{instrument}`
- `GET  /api/v2/signals/combined/{instrument}`

## Performance Goals

| Metric | Target |
|--------|--------|
| Win Rate | 55–65% |
| Sharpe Ratio | 1.7–3.0 |
| Profit Factor | 1.5–2.2 |
| Max Drawdown | < 12–15% |

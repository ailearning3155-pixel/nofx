# APEX Trading OS — Complete Setup & Walkthrough
# From Zero to Live Trading (Step by Step)

---

## THE 3-STAGE JOURNEY

```
STAGE 1 → BACKTEST      (test strategies on historical OANDA data, zero risk)
STAGE 2 → PAPER TRADE   (run live on real prices, fake money, zero risk)
STAGE 3 → LIVE TRADE    (real money, only after stages 1 & 2 prove profitable)
```

> ⚠️ NEVER skip stages. A strategy that fails backtest will ALWAYS fail live.

---

## PREREQUISITES (Install These First)

### 1. Python 3.11+
```bash
# Check your version
python --version   # needs to be 3.11 or higher

# If not installed — Windows:
# Download from https://www.python.org/downloads/

# Mac:
brew install python@3.11

# Linux (Ubuntu/Debian):
sudo apt update && sudo apt install python3.11 python3.11-pip python3.11-venv
```

### 2. Node.js 18+ (for the dashboard)
```bash
# Check version
node --version   # needs 18+

# Download from https://nodejs.org (pick LTS version)
```

### 3. Docker Desktop (for PostgreSQL + Redis)
```bash
# Download from https://www.docker.com/products/docker-desktop/
# Install and make sure Docker Desktop is RUNNING before continuing
docker --version   # confirm it works
```

### 4. Git
```bash
git --version
# If not installed: https://git-scm.com/downloads
```

---

## STEP 1 — GET YOUR API KEYS

You need these accounts set up before touching code.

### OANDA Account (Required for all stages)
```
1. Go to https://www.oanda.com
2. Click "Open Account" → choose "Practice Account" (free, no real money)
3. After signup, go to:
   My Account → Manage API Access → Generate API Token
4. Also note your Account ID from the top of the dashboard
   It looks like: 101-001-12345678-001

Save these two values:
   OANDA_ACCOUNT_ID = 101-001-XXXXXXXX-001
   OANDA_API_KEY    = xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### AI Model Keys (Get at least ONE to start)
```
Recommended starting order (cheapest first):

1. DeepSeek (cheapest, ~$0.001 per analysis)
   → https://platform.deepseek.com → API Keys → Create Key
   DEEPSEEK_API_KEY = sk-...

2. OpenAI GPT-4o (~$0.005 per analysis)
   → https://platform.openai.com → API Keys → Create New Secret Key
   OPENAI_API_KEY = sk-...

3. Anthropic Claude (~$0.003 per analysis)
   → https://console.anthropic.com → API Keys
   ANTHROPIC_API_KEY = sk-ant-...

4. Google Gemini (has free tier!)
   → https://aistudio.google.com → Get API Key
   GOOGLE_API_KEY = AIza...

5. Grok (xAI)
   → https://console.x.ai → API Keys
   GROK_API_KEY = xai-...

6. Qwen (Alibaba)
   → https://dashscope.aliyuncs.com → API Keys
   QWEN_API_KEY = sk-...
```

### Optional Services
```
NewsAPI (free 100 requests/day)
   → https://newsapi.org → Get API Key
   NEWS_API_KEY = xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

Telegram Bot (for trade alerts on your phone)
   → Open Telegram → search @BotFather → /newbot → follow steps
   TELEGRAM_BOT_TOKEN = 123456789:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TELEGRAM_CHAT_ID   = (message @userinfobot to get your ID)
```

---

## STEP 2 — DOWNLOAD & INSTALL APEX

```bash
# 1. Extract the zip you downloaded — you'll have an "apex" folder
# 2. Open terminal/command prompt in that folder

cd apex

# 3. Create a Python virtual environment (keeps dependencies isolated)
python -m venv venv

# Activate it:
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# You should see (venv) at the start of your terminal prompt

# 4. Install all packages (use the install script, NOT plain pip install)
# Mac / Linux:
chmod +x install.sh && ./install.sh

# Windows:
install.bat

# The install script handles pandas-ta and PyTorch correctly.
# Plain "pip install -r requirements.txt" will fail on pandas-ta.
```

---

## STEP 3 — CONFIGURE YOUR ENVIRONMENT

```bash
# Copy the example config file
cp .env.example .env

# Open .env in any text editor (Notepad, VS Code, etc.)
# Fill in your values:
```

Minimum `.env` for Stage 1 (Backtest):
```env
# OANDA — Required
OANDA_ACCOUNT_ID=101-001-XXXXXXXX-001
OANDA_API_KEY=your_key_here
OANDA_ENVIRONMENT=practice          ← KEEP THIS AS "practice" FOR NOW

# Database
DATABASE_URL=postgresql://apex:apex_password@localhost:5432/apex_db
REDIS_URL=redis://localhost:6379/0

# At least one AI key
DEEPSEEK_API_KEY=sk-...

# App
SECRET_KEY=make_up_any_long_random_string_here_minimum_32_chars
APP_ENV=development
```

---

## STEP 4 — START DATABASE SERVICES

```bash
# Make sure Docker Desktop is running, then:
docker-compose up -d postgres redis

# Verify they started (both should say "healthy" or "running")
docker ps

# Initialize the database tables
python scripts/migrate.py

# You should see:
# ✅ Created 10 tables: trades, ai_signals, debates, ...
# ✅ Seeded AI competitor records
# 🟢 Migrations complete!
```

---

## STEP 5 — START THE BACKEND

```bash
# Make sure your venv is activated, then:
uvicorn api.main:app --reload --port 8000

# You should see:
# ✅ OANDA connected: balance=100000.0 USD
# ✅ AI Manager ready: ['deepseek', ...]
# ✅ Strategy Registry: 17 strategies loaded
# 🟢 APEX is LIVE
# INFO: Uvicorn running on http://0.0.0.0:8000
```

Open your browser: **http://localhost:8000/api/docs**
You'll see the full interactive API documentation.

---

## STEP 6 — START THE DASHBOARD

```bash
# Open a NEW terminal window (keep the backend running)
cd apex/web
npm install          # first time only, takes ~1 minute
npm run dev

# You should see:
# Local: http://localhost:5173
```

Open your browser: **http://localhost:5173**
You'll see the APEX dashboard.

---

# ═══════════════════════════════════════
# STAGE 1: BACKTESTING
# ═══════════════════════════════════════

## What is Backtesting?
Backtesting runs your strategies against **historical price data** from OANDA.
The AI analyzes past candles as if it was trading in real-time.
You see exactly what would have happened — profit, loss, drawdown — with zero risk.

## Running Your First Backtest

### Option A: Via Dashboard (Easiest)
```
1. Open http://localhost:5173
2. Click "📈 Backtest" in the sidebar
3. Choose:
   - Instrument: EUR_USD
   - Date Range: Last 6 months
   - Strategy: ema_crossover (start simple)
   - AI Model: deepseek (cheapest)
4. Click "Run Backtest"
5. Wait 30-60 seconds for results
```

### Option B: Via Script (More Control)
```bash
# Run a backtest from command line
python scripts/run_backtest.py \
  --instrument EUR_USD \
  --strategy ema_crossover \
  --from 2024-01-01 \
  --to 2024-12-31 \
  --granularity H1 \
  --balance 10000 \
  --ai deepseek

# Results saved to: backtest_results/EUR_USD_ema_crossover_YYYYMMDD.json
```

### Option C: Via API
```bash
curl -X POST http://localhost:8000/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "instrument": "EUR_USD",
    "strategy": "ema_crossover",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "granularity": "H1",
    "initial_balance": 10000,
    "ai_model": "deepseek"
  }'
```

## Understanding Backtest Results

```
═══════════════════════════════════════
BACKTEST RESULTS: EUR_USD / EMA Crossover
Period: 2024-01-01 → 2024-12-31
═══════════════════════════════════════
Starting Balance:  $10,000.00
Final Balance:     $11,847.32
Total Return:      +18.47%          ← anything above 10%/year is solid
─────────────────────────────────────
Total Trades:      94
Winning Trades:    51 (54.3%)       ← win rate above 50% is good
Losing Trades:     43 (45.7%)
─────────────────────────────────────
Max Drawdown:      8.2%             ← below 15% is acceptable
Sharpe Ratio:      1.34             ← above 1.0 is good, above 2.0 is great
Profit Factor:     1.61             ← above 1.5 means wins outweigh losses
─────────────────────────────────────
Best Trade:        +$847.20
Worst Trade:       -$312.40
Avg Win:           +$198.40
Avg Loss:          -$143.20
═══════════════════════════════════════
VERDICT: ✅ PROFITABLE — ready for paper trading
```

## Backtest Checklist Before Moving to Paper Trading

Run backtests on AT LEAST these combinations:
```
□ 3+ different instruments (e.g. EUR_USD, GBP_USD, XAU_USD)
□ 2+ different time periods (e.g. 2023 and 2024 separately)
□ 2+ different strategies (e.g. ema_crossover AND fair_value_gap)
□ Results must show: Return > 8%, Drawdown < 20%, Win Rate > 45%
□ Test with AI debate enabled AND disabled
□ Check if results are consistent across periods (not just lucky once)
```

## Common Backtest Red Flags — Do NOT proceed if:
```
❌ Win rate below 35%
❌ Max drawdown above 25%
❌ Profit factor below 1.2
❌ Strategy only profitable in ONE specific time period
❌ Return dramatically different between 2023 and 2024 tests
```

---

# ═══════════════════════════════════════
# STAGE 2: PAPER TRADING
# ═══════════════════════════════════════

## What is Paper Trading?
Paper trading uses OANDA's "practice" account — real live prices,
but FAKE money. OANDA gives you $100,000 virtual dollars.
The AI trades in real-time but nothing real is at risk.

## Prerequisites for Paper Trading
```
□ Completed at least 5 backtests with positive results
□ Chosen 1-2 strategies that performed best in backtest
□ OANDA_ENVIRONMENT=practice in your .env (it already is by default)
□ AI debate enabled (DEBATE_ENABLED=true)
□ Risk settings configured (MAX_DAILY_LOSS_PCT=3.0 for paper)
```

## Starting Paper Trading

### Step 1: Configure for Paper Mode
Your `.env` should have:
```env
OANDA_ENVIRONMENT=practice    ← paper trading uses this
MAX_OPEN_TRADES=3             ← start conservative
DEFAULT_RISK_PER_TRADE=1.0   ← 1% per trade
MAX_DAILY_LOSS_PCT=3.0        ← stop trading if down 3% in a day
MAX_DRAWDOWN_PCT=10.0         ← emergency stop at 10% overall drawdown
DEBATE_ENABLED=true
COMPETITION_MODE=true         ← let all 6 AIs compete to see who's best
```

### Step 2: Start the System
```bash
# Terminal 1 — Backend
uvicorn api.main:app --reload --port 8000

# Terminal 2 — Celery Worker (runs scheduled tasks)
celery -A services.task_queue worker --loglevel=info

# Terminal 3 — Celery Beat (scheduler)
celery -A services.task_queue beat --loglevel=info

# Terminal 4 — Dashboard
cd web && npm run dev
```

### Step 3: Enable Trading
```bash
# Via API — start the trading loop for EUR_USD
curl -X POST http://localhost:8000/api/trading/start \
  -H "Content-Type: application/json" \
  -d '{"instruments": ["EUR_USD", "GBP_USD"], "mode": "paper"}'

# Or through the dashboard → Live Trading → "Start Trading" button
```

### Step 4: Monitor Paper Trading
Watch these metrics daily:
```
Dashboard → Live Trading:  See all open trades, real-time P&L
Dashboard → AI Arena:      See which AI is performing best
Dashboard → Debate Room:   Watch AIs argue before each trade
Dashboard → Risk Console:  Monitor drawdown, daily loss
```

## Paper Trading Duration
```
Minimum: 2 weeks of paper trading
Recommended: 4-8 weeks
Target metrics before going live:
  ✅ Net profitable (positive P&L overall)
  ✅ No day exceeded your MAX_DAILY_LOSS_PCT
  ✅ Max drawdown stayed below 12%
  ✅ Win rate 45%+
  ✅ You understand WHY each trade was taken (check AI reasoning logs)
  ✅ You've seen the system handle a losing streak and recover
```

---

# ═══════════════════════════════════════
# STAGE 3: LIVE TRADING
# ═══════════════════════════════════════

## ⚠️ READ THIS BEFORE GOING LIVE

```
ONLY proceed to live trading if:
  □ You completed Stages 1 AND 2 fully
  □ Paper trading was profitable for 4+ weeks
  □ You can afford to LOSE your entire trading capital
  □ You've manually reviewed 50+ AI trade decisions and they make sense
  □ You have Telegram alerts set up on your phone
  □ You understand every setting in your .env file
```

## Setting Up a Live OANDA Account
```
1. Log in to oanda.com
2. Click "Open Live Account" (separate from practice)
3. Fund it — START SMALL (minimum $500, recommended $1000-$2000 to start)
4. Go to Manage API Access → Generate Live API Token
5. Note your Live Account ID (different from practice ID)
```

## Switching to Live Mode
```bash
# Edit your .env file:

OANDA_ACCOUNT_ID=101-001-XXXXXXXX-002   ← your LIVE account ID
OANDA_API_KEY=your_live_api_key_here    ← your LIVE API key
OANDA_ENVIRONMENT=live                  ← THE CRITICAL SWITCH

# Tighten risk settings for real money:
MAX_OPEN_TRADES=2                 ← fewer trades when starting live
DEFAULT_RISK_PER_TRADE=0.5        ← half a percent per trade (very conservative)
MAX_DAILY_LOSS_PCT=2.0            ← stricter daily stop
MAX_DRAWDOWN_PCT=8.0              ← stricter overall stop
```

## Live Trading Safety Rules
```
1. NEVER increase risk_per_trade above 2% per trade
2. ALWAYS have Telegram alerts enabled
3. Check the dashboard at least twice a day
4. If you feel nervous about a trade — the Kill Switch is your friend
5. Do NOT override the AI or risk manager when they say HOLD
6. Start with 1-2 instruments only (EUR_USD is the most liquid)
7. Do NOT run live trading on a laptop that sleeps/hibernates
   (use a VPS or keep your machine always on)
```

## Recommended VPS Setup (for 24/7 live trading)
```
For reliable live trading, host APEX on a VPS:

Budget option: DigitalOcean Droplet ($6/month)
  - 1 vCPU, 1GB RAM is enough
  - Choose Ubuntu 22.04
  - Install Docker, Python, Node as above
  - Use 'screen' or 'tmux' to keep processes running

Better option: DigitalOcean Droplet ($12/month)
  - 1 vCPU, 2GB RAM (handles FinBERT sentiment model)

Setup on VPS:
  1. SSH into your VPS
  2. Clone/upload your apex folder
  3. Run docker-compose up -d
  4. Use 'screen -S apex' to start persistent sessions
  5. Your dashboard is then at http://YOUR_VPS_IP:5173
```

---

## DAILY ROUTINE ONCE LIVE

### Morning (5 minutes)
```
1. Open APEX dashboard
2. Check overnight P&L
3. Review AI Arena — which models are up/down
4. Check Risk Console — no kill switch triggered?
5. Check Economic Calendar — any high-impact events today?
6. Verify system is running (green dots in sidebar)
```

### Evening (5 minutes)
```
1. Review today's trades in the Debate Room history
2. Note any patterns (which strategies worked, which didn't)
3. Check Telegram — review all day's alerts
4. Look at AI free will decisions — are they making sense?
```

### Weekly (30 minutes)
```
1. Compare AI competitors in Arena — promote best performer
2. Run a fresh backtest on recent weeks to check strategy still works
3. Review any unusual losses — was the AI wrong or just bad luck?
4. Adjust strategy weights if one consistently underperforms
```

---

## TROUBLESHOOTING

### "OANDA API Error 401"
```
→ Your API key is wrong or expired
→ Go to OANDA → Manage API Access → regenerate key → update .env
```

### "AI request failed / timeout"
```
→ Your AI API key is invalid or has no credits
→ Check your balance at the AI provider's website
→ APEX falls back to HOLD if AI fails, so trading stops safely
```

### "Database connection failed"
```
→ Docker isn't running
→ Run: docker-compose up -d postgres redis
→ Then: python scripts/migrate.py
```

### "Strategy Registry failed to load"
```
→ Missing Python package
→ Run: pip install -r requirements.txt --upgrade
```

### "Kill switch activated"
```
→ You hit your daily loss limit — this is working correctly
→ Review what happened in the Debate Room history
→ To reset: POST /api/risk/kill-switch/deactivate
→ Only deactivate if you understand WHY losses happened
```

### Dashboard shows but no prices
```
→ WebSocket not connected (check red dot in sidebar)
→ Make sure backend is running on port 8000
→ Check browser console for errors (F12)
```

---

## QUICK REFERENCE — ALL COMMANDS

```bash
# Start everything
docker-compose up -d                    # databases
uvicorn api.main:app --reload          # backend API
cd web && npm run dev                  # dashboard
celery -A services.task_queue worker   # background tasks

# Backtest
python scripts/run_backtest.py --help  # see all options

# Database
python scripts/migrate.py             # create/update tables
docker-compose down                   # stop databases
docker-compose down -v                # stop + delete all data

# Logs
tail -f logs/apex_$(date +%Y-%m-%d).log   # live log

# Kill switch (emergency)
curl -X POST http://localhost:8000/api/risk/kill-switch/activate

# Check system status
curl http://localhost:8000/api/status | python -m json.tool
```

---

## SUPPORT & NEXT STEPS

If you get stuck at any step, the most common issues are:
1. Python venv not activated (no `(venv)` in terminal)
2. Docker not running
3. `.env` file has wrong values or missing keys
4. Port 8000 already in use (kill other processes or change port)

Good luck — and remember: **backtest first, always.** 🚀

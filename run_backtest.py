"""
APEX — Backtest CLI Script
Run backtests from the command line.

Examples:
    # Simple strategy backtest
    python scripts/run_backtest.py --instrument EUR_USD --strategy ema_crossover --from 2024-01-01 --to 2024-12-31

    # AI-driven backtest (costs API credits)
    python scripts/run_backtest.py --instrument XAU_USD --ai deepseek --from 2024-06-01 --to 2024-12-31

    # Test all strategies on EUR_USD
    python scripts/run_backtest.py --instrument EUR_USD --all-strategies --from 2024-01-01 --to 2024-12-31

    # Custom risk settings
    python scripts/run_backtest.py --instrument GBP_USD --strategy macd_signal --risk 0.5 --balance 5000
"""
import sys
import os
import asyncio
import argparse
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.backtest.engine import BacktestEngine, BacktestConfig
from core.strategies.registry import get_strategy_registry
from loguru import logger


def parse_args():
    parser = argparse.ArgumentParser(
        description="APEX Backtest Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--instrument", "-i",  default="EUR_USD",
                        help="OANDA instrument (default: EUR_USD)")
    parser.add_argument("--strategy",   "-s",  default=None,
                        help="Strategy name (e.g. ema_crossover, macd_signal, fair_value_gap)")
    parser.add_argument("--ai",                default=None,
                        help="AI model to use (gpt4o, claude, deepseek, etc)")
    parser.add_argument("--from",       "-f",  dest="start_date", default="2024-01-01",
                        help="Start date YYYY-MM-DD (default: 2024-01-01)")
    parser.add_argument("--to",         "-t",  dest="end_date",   default="2024-12-31",
                        help="End date YYYY-MM-DD (default: 2024-12-31)")
    parser.add_argument("--granularity","-g",  default="H1",
                        help="Candle granularity: M5,M15,M30,H1,H4,D (default: H1)")
    parser.add_argument("--balance",    "-b",  type=float, default=10000.0,
                        help="Starting balance USD (default: 10000)")
    parser.add_argument("--risk",       "-r",  type=float, default=1.0,
                        help="Risk percent per trade (default: 1.0)")
    parser.add_argument("--max-dd",            type=float, default=20.0,
                        help="Max drawdown %% before aborting (default: 20)")
    parser.add_argument("--all-strategies",    action="store_true",
                        help="Run all strategies and compare results")
    parser.add_argument("--save",       "-o",  default=None,
                        help="Save results to JSON file")
    parser.add_argument("--list-strategies",   action="store_true",
                        help="List all available strategies and exit")
    return parser.parse_args()


async def run_single(args, strategy: str = None, ai_model: str = None) -> dict:
    engine = BacktestEngine()
    config = BacktestConfig(
        instrument=args.instrument,
        granularity=args.granularity,
        start_date=args.start_date,
        end_date=args.end_date,
        initial_balance=args.balance,
        risk_per_trade_pct=args.risk,
        max_drawdown_pct=args.max_dd,
        strategy=strategy,
        ai_model=ai_model,
    )
    result = await engine.run(config)
    print(result.summary())
    return {
        "instrument": args.instrument,
        "strategy": strategy or f"ai_{ai_model}",
        "total_return_pct": round(result.total_return_pct, 2),
        "win_rate": round(result.win_rate, 1),
        "total_trades": result.total_trades,
        "max_drawdown_pct": round(result.max_drawdown_pct, 2),
        "sharpe_ratio": round(result.sharpe_ratio, 2),
        "profit_factor": round(result.profit_factor, 2),
        "verdict": result.verdict,
        "aborted": result.aborted,
    }


async def run_all_strategies(args) -> list:
    registry = get_strategy_registry()
    strategies = registry.list_strategy_names()

    print(f"\n🔄 Running {len(strategies)} strategies on {args.instrument}...\n")
    results = []

    for strat in strategies:
        print(f"  Testing: {strat}...")
        try:
            r = await run_single(args, strategy=strat)
            results.append(r)
        except Exception as e:
            logger.warning(f"  {strat} failed: {e}")
            results.append({"strategy": strat, "error": str(e)})

    # Sort by return
    results.sort(key=lambda x: x.get("total_return_pct", -999), reverse=True)

    print("\n" + "═" * 80)
    print(f"STRATEGY COMPARISON — {args.instrument} ({args.start_date} → {args.end_date})")
    print("═" * 80)
    print(f"{'Strategy':<30} {'Return%':>8} {'Win%':>7} {'Trades':>7} {'MaxDD%':>8} {'Sharpe':>8} {'Verdict'}")
    print("─" * 80)
    for r in results:
        if "error" in r:
            print(f"{r['strategy']:<30} {'ERROR':>8}")
        else:
            verdict_short = "✅" if "PROFITABLE" in r.get("verdict","") else "⚠️" if "MARGINALLY" in r.get("verdict","") else "❌"
            print(
                f"{r['strategy']:<30} "
                f"{r.get('total_return_pct',0):>+7.1f}% "
                f"{r.get('win_rate',0):>6.1f}% "
                f"{r.get('total_trades',0):>7} "
                f"{r.get('max_drawdown_pct',0):>7.1f}% "
                f"{r.get('sharpe_ratio',0):>7.2f} "
                f"{verdict_short}"
            )
    print("═" * 80)
    return results


def main():
    args = parse_args()

    # List strategies and exit
    if args.list_strategies:
        registry = get_strategy_registry()
        info = registry.get_all_info()
        print("\nAvailable Strategies:")
        print("─" * 60)
        for s in info:
            print(f"  {s['name']:<30} [{s['category']}]")
            print(f"    {s['description']}")
        print(f"\nTotal: {len(info)} strategies")
        return

    # Validate dates
    try:
        datetime.strptime(args.start_date, "%Y-%m-%d")
        datetime.strptime(args.end_date, "%Y-%m-%d")
    except ValueError:
        print("❌ Invalid date format. Use YYYY-MM-DD")
        sys.exit(1)

    if not args.strategy and not args.ai and not args.all_strategies:
        print("❌ Specify --strategy NAME, --ai MODEL, or --all-strategies")
        print("   Run with --list-strategies to see available strategies")
        sys.exit(1)

    print(f"\n🚀 APEX Backtest Engine")
    print(f"   Instrument: {args.instrument}")
    print(f"   Period: {args.start_date} → {args.end_date}")
    print(f"   Granularity: {args.granularity}")
    print(f"   Balance: ${args.balance:,.0f}  Risk: {args.risk}%/trade")
    print()

    # Run
    if args.all_strategies:
        results = asyncio.run(run_all_strategies(args))
    else:
        results = asyncio.run(run_single(args, strategy=args.strategy, ai_model=args.ai))

    # Save results
    save_path = args.save
    if not save_path:
        os.makedirs("backtest_results", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        strat_name = args.strategy or args.ai or "all"
        save_path = f"backtest_results/{args.instrument}_{strat_name}_{ts}.json"

    with open(save_path, "w") as f:
        json.dump(results if isinstance(results, list) else [results], f, indent=2, default=str)
    print(f"\n💾 Results saved to: {save_path}")


if __name__ == "__main__":
    main()

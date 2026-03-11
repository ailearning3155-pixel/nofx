"""
APEX — Automated Model Retraining Scheduler
Retrains XGBoost + RandomForest ensemble weekly using accumulated trade data.
Also triggers RL agent save and performance tracker updates.

Uses APScheduler for lightweight async scheduling (no Celery needed).
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger


class RetrainingScheduler:
    """
    Schedules and executes periodic model retraining.

    Schedule:
    - ML Ensemble (XGBoost + RF): every 7 days
    - Feature scaler: every 7 days (same as ensemble)
    - RL agent save: every 1 hour
    - Strategy performance check: every 6 hours
    - Training data cleanup: every 30 days

    Usage:
        scheduler = RetrainingScheduler()
        scheduler.start()   # call once at app startup
        # ...
        scheduler.stop()    # call at shutdown
    """

    def __init__(self):
        self._scheduler = None
        self._started   = False

    def start(self):
        """Start the background scheduler."""
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from apscheduler.triggers.interval  import IntervalTrigger
            from apscheduler.triggers.cron      import CronTrigger

            self._scheduler = AsyncIOScheduler()

            # ── Weekly ML retrain (Sunday 02:00 UTC) ──────────────────────
            self._scheduler.add_job(
                self._retrain_ml_ensemble,
                trigger=CronTrigger(day_of_week="sun", hour=2, minute=0),
                id="ml_retrain",
                name="ML Ensemble Weekly Retrain",
                replace_existing=True,
                misfire_grace_time=3600,
            )

            # ── RL agent save every hour ──────────────────────────────────
            self._scheduler.add_job(
                self._save_rl_agent,
                trigger=IntervalTrigger(hours=1),
                id="rl_save",
                name="RL Agent Hourly Save",
                replace_existing=True,
            )

            # ── Strategy performance check every 6 hours ──────────────────
            self._scheduler.add_job(
                self._check_strategy_performance,
                trigger=IntervalTrigger(hours=6),
                id="perf_check",
                name="Strategy Performance Check",
                replace_existing=True,
            )

            # ── Training data cleanup monthly ─────────────────────────────
            self._scheduler.add_job(
                self._cleanup_old_training_data,
                trigger=CronTrigger(day=1, hour=3, minute=0),
                id="data_cleanup",
                name="Monthly Training Data Cleanup",
                replace_existing=True,
            )

            self._scheduler.start()
            self._started = True
            logger.info("✅ Retraining scheduler started — weekly ML retrain, hourly RL save")

        except ImportError:
            logger.warning("APScheduler not installed — automated retraining disabled. pip install apscheduler")
        except Exception as e:
            logger.warning(f"Retraining scheduler failed to start: {e}")

    def stop(self):
        """Gracefully stop the scheduler."""
        if self._scheduler and self._started:
            self._scheduler.shutdown(wait=False)
            self._started = False
            logger.info("Retraining scheduler stopped")

    # ── Scheduled tasks ───────────────────────────────────────────────────────

    async def _retrain_ml_ensemble(self):
        """Retrain XGBoost + RF ensemble on latest trade data."""
        logger.info("🔄 Starting weekly ML ensemble retraining...")
        try:
            from core.ml.ensemble import get_ml_ensemble
            ensemble = get_ml_ensemble()
            n_samples = await self._count_training_samples()

            if n_samples < 50:
                logger.warning(f"Not enough training data ({n_samples} trades) — skipping retrain (need ≥ 50)")
                return

            records = await self._load_training_records()
            success = ensemble.retrain(records)

            if success:
                logger.info(f"✅ ML ensemble retrained on {n_samples} trades")
            else:
                logger.warning("ML ensemble retraining failed — models unchanged")

        except Exception as e:
            logger.error(f"ML retraining error: {e}")

    async def _save_rl_agent(self):
        """Persist RL Q-table state to disk."""
        try:
            from core.ml.reinforcement import get_rl_agent
            agent = get_rl_agent()
            agent.save()
        except Exception as e:
            logger.debug(f"RL agent save error: {e}")

    async def _check_strategy_performance(self):
        """Disable strategies with consistently poor performance."""
        logger.debug("Running strategy performance check...")
        try:
            from core.risk.advanced import get_advanced_risk_manager
            mgr = get_advanced_risk_manager()

            disabled = mgr.performance_tracker.get_disabled_strategies()
            if disabled:
                logger.warning(f"🔴 Auto-disabled underperforming strategies: {disabled}")
            else:
                logger.debug("✅ All strategies within performance limits")

        except Exception as e:
            logger.debug(f"Performance check error: {e}")

    async def _cleanup_old_training_data(self):
        """Remove training records older than 90 days."""
        logger.info("Cleaning up old training data (>90 days)...")
        try:
            from pathlib import Path
            import pandas as pd
            from datetime import datetime, timedelta

            training_path = Path("models/saved/training_data.csv")
            if not training_path.exists():
                return

            df = pd.read_csv(training_path)
            if "timestamp" not in df.columns:
                return

            df["timestamp"] = pd.to_datetime(df["timestamp"])
            cutoff = datetime.utcnow() - timedelta(days=90)
            before = len(df)
            df = df[df["timestamp"] >= cutoff]
            after = len(df)

            df.to_csv(training_path, index=False)
            logger.info(f"Training data cleanup: {before} → {after} records (removed {before - after})")

        except Exception as e:
            logger.debug(f"Training data cleanup error: {e}")

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _count_training_samples(self) -> int:
        from pathlib import Path
        training_path = Path("models/saved/training_data.csv")
        if not training_path.exists():
            return 0
        try:
            import pandas as pd
            return len(pd.read_csv(training_path))
        except Exception:
            return 0

    async def _load_training_records(self) -> list:
        from pathlib import Path
        import pandas as pd
        training_path = Path("models/saved/training_data.csv")
        if not training_path.exists():
            return []
        try:
            df = pd.read_csv(training_path)
            return df.to_dict("records")
        except Exception:
            return []

    def get_status(self) -> dict:
        """Return scheduler status for API/dashboard."""
        if not self._scheduler or not self._started:
            return {"running": False, "jobs": []}

        jobs = []
        for job in self._scheduler.get_jobs():
            next_run = job.next_run_time
            jobs.append({
                "id":       job.id,
                "name":     job.name,
                "next_run": next_run.isoformat() if next_run else None,
            })

        return {"running": True, "jobs": jobs}


# ── Module singleton ─────────────────────────────────────────────────────────

_scheduler: Optional[RetrainingScheduler] = None


def get_retraining_scheduler() -> RetrainingScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = RetrainingScheduler()
    return _scheduler

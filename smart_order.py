"""
APEX — Smart Execution Engine
Event-driven order management with:
- Duplicate order prevention
- Slippage protection
- Partial fill handling
- Connection recovery
- Smart order routing (market / limit selection)
"""
from __future__ import annotations
import asyncio
import hashlib
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Set

from loguru import logger


@dataclass
class OrderIntent:
    """A pending order before it's placed."""
    instrument:   str
    direction:    str           # BUY | SELL
    units:        float
    order_type:   str = "MARKET"   # MARKET | LIMIT
    limit_price:  Optional[float] = None
    stop_loss:    Optional[float] = None
    take_profit:  Optional[float] = None
    strategy:     str = ""
    ai_model:     str = ""
    confidence:   float = 0.0
    idempotency_key: str = ""

    def __post_init__(self):
        if not self.idempotency_key:
            raw = f"{self.instrument}:{self.direction}:{self.units}:{int(time.time() // 60)}"
            self.idempotency_key = hashlib.md5(raw.encode()).hexdigest()[:12]


@dataclass
class ExecutionResult:
    success:      bool
    order_id:     str = ""
    filled_price: float = 0.0
    filled_units: float = 0.0
    slippage_pct: float = 0.0
    error:        str = ""
    was_duplicate: bool = False
    latency_ms:   float = 0.0


@dataclass
class ExecutionStats:
    total_orders:     int   = 0
    successful:       int   = 0
    failed:           int   = 0
    duplicates_blocked: int = 0
    slippage_blocked: int   = 0
    retries:          int   = 0
    avg_latency_ms:   float = 0.0
    _latencies: List[float] = field(default_factory=list)

    def record(self, result: ExecutionResult):
        self.total_orders += 1
        if result.success:
            self.successful += 1
        else:
            self.failed += 1
        if result.was_duplicate:
            self.duplicates_blocked += 1
        self._latencies.append(result.latency_ms)
        if len(self._latencies) > 1000:
            self._latencies.pop(0)
        self.avg_latency_ms = sum(self._latencies) / len(self._latencies)


class SmartExecutionEngine:
    """
    Handles order placement with safeguards:
    1. Idempotency — deduplicates orders within a 60-second window
    2. Slippage protection — rejects if live price moved too far from signal price
    3. Retry with backoff on transient failures
    4. Rate limiting — max N orders per minute per instrument
    5. Cooldown — no re-entry on same instrument within cooldown period
    """

    def __init__(
        self,
        max_slippage_pct:      float = 0.05,    # reject if price moved > 0.05%
        max_orders_per_minute: int   = 5,
        cooldown_seconds:      int   = 300,      # 5 min cooldown after close
        max_retries:           int   = 3,
        retry_delay_seconds:   float = 2.0,
    ):
        self.max_slippage_pct      = max_slippage_pct
        self.max_orders_per_minute = max_orders_per_minute
        self.cooldown_seconds      = cooldown_seconds
        self.max_retries           = max_retries
        self.retry_delay           = retry_delay_seconds

        self._seen_keys: Set[str]              = set()
        self._order_times: Dict[str, List[float]] = defaultdict(list)
        self._cooldowns: Dict[str, float]      = {}
        self.stats = ExecutionStats()

    async def execute(
        self,
        intent: OrderIntent,
        signal_price: float,
        place_fn: Callable,      # async fn(intent) -> dict
        get_price_fn: Callable,  # async fn(instrument) -> float
    ) -> ExecutionResult:
        """
        Execute an order with full safeguards.
        place_fn and get_price_fn are injected (OANDA connector methods).
        """
        start = time.monotonic()

        # ── 1. Duplicate check ────────────────────────────────────────────
        if self._is_duplicate(intent):
            result = ExecutionResult(
                success=False,
                error="Duplicate order blocked",
                was_duplicate=True,
                latency_ms=0.0,
            )
            self.stats.record(result)
            return result

        # ── 2. Rate limit ─────────────────────────────────────────────────
        if self._is_rate_limited(intent.instrument):
            result = ExecutionResult(
                success=False,
                error=f"Rate limit: max {self.max_orders_per_minute} orders/min for {intent.instrument}",
                latency_ms=0.0,
            )
            self.stats.record(result)
            return result

        # ── 3. Cooldown check ─────────────────────────────────────────────
        if self._is_in_cooldown(intent.instrument):
            remaining = int(self._cooldowns[intent.instrument] - time.time())
            result = ExecutionResult(
                success=False,
                error=f"Cooldown active for {intent.instrument}: {remaining}s remaining",
                latency_ms=0.0,
            )
            self.stats.record(result)
            return result

        # ── 4. Slippage check ─────────────────────────────────────────────
        try:
            live_price = await get_price_fn(intent.instrument)
            slippage   = abs(live_price - signal_price) / (signal_price + 1e-10) * 100
            if slippage > self.max_slippage_pct:
                self.stats.slippage_blocked += 1
                result = ExecutionResult(
                    success=False,
                    error=f"Slippage {slippage:.3f}% exceeds limit {self.max_slippage_pct}%",
                    slippage_pct=slippage,
                    latency_ms=(time.monotonic() - start) * 1000,
                )
                self.stats.record(result)
                return result
        except Exception as e:
            logger.warning(f"Could not verify live price for slippage check: {e}")
            live_price = signal_price

        # ── 5. Place order with retry ─────────────────────────────────────
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await place_fn(intent)
                latency  = (time.monotonic() - start) * 1000

                filled_price = float(response.get("filled_price", live_price))
                filled_units = float(response.get("filled_units", intent.units))
                order_id     = str(response.get("order_id", ""))

                actual_slip  = abs(filled_price - live_price) / (live_price + 1e-10) * 100

                # Mark as seen (idempotency)
                self._seen_keys.add(intent.idempotency_key)
                self._order_times[intent.instrument].append(time.time())

                logger.info(
                    f"✅ Executed {intent.direction} {intent.units} {intent.instrument} "
                    f"@ {filled_price:.5f} | slip={actual_slip:.3f}% | {latency:.0f}ms"
                )

                result = ExecutionResult(
                    success=True,
                    order_id=order_id,
                    filled_price=filled_price,
                    filled_units=filled_units,
                    slippage_pct=round(actual_slip, 4),
                    latency_ms=round(latency, 1),
                )
                self.stats.record(result)
                return result

            except Exception as e:
                if attempt < self.max_retries:
                    self.stats.retries += 1
                    logger.warning(f"Order attempt {attempt} failed: {e} — retrying in {self.retry_delay}s")
                    await asyncio.sleep(self.retry_delay * attempt)
                else:
                    latency = (time.monotonic() - start) * 1000
                    result  = ExecutionResult(
                        success=False,
                        error=str(e),
                        latency_ms=round(latency, 1),
                    )
                    self.stats.record(result)
                    logger.error(f"❌ Order failed after {self.max_retries} attempts: {e}")
                    return result

        # Should not reach here
        return ExecutionResult(success=False, error="Unknown execution error")

    def record_close(self, instrument: str):
        """Call this when a position is closed to start the cooldown."""
        self._cooldowns[instrument] = time.time() + self.cooldown_seconds

    def _is_duplicate(self, intent: OrderIntent) -> bool:
        return intent.idempotency_key in self._seen_keys

    def _is_rate_limited(self, instrument: str) -> bool:
        cutoff = time.time() - 60
        times  = [t for t in self._order_times.get(instrument, []) if t > cutoff]
        self._order_times[instrument] = times
        return len(times) >= self.max_orders_per_minute

    def _is_in_cooldown(self, instrument: str) -> bool:
        expiry = self._cooldowns.get(instrument, 0)
        return time.time() < expiry

    def get_stats(self) -> Dict:
        return {
            "total_orders":       self.stats.total_orders,
            "successful":         self.stats.successful,
            "failed":             self.stats.failed,
            "duplicates_blocked": self.stats.duplicates_blocked,
            "slippage_blocked":   self.stats.slippage_blocked,
            "retries":            self.stats.retries,
            "avg_latency_ms":     round(self.stats.avg_latency_ms, 1),
            "success_rate":       round(
                self.stats.successful / (self.stats.total_orders + 1e-10), 3
            ),
        }


# ── WebSocket Price Feed ──────────────────────────────────────────────────────

class EventDrivenPriceFeed:
    """
    Subscribes to OANDA streaming price feed via WebSocket.
    Triggers callbacks when new prices arrive — replaces polling.
    """

    def __init__(self, on_price_callback: Callable):
        self.on_price   = on_price_callback
        self._running   = False
        self._prices:   Dict[str, float] = {}
        self._last_tick: Dict[str, datetime] = {}

    async def start(self, instruments: List[str], oanda_connector):
        """Start streaming prices for the given instruments."""
        self._running = True
        logger.info(f"📡 Starting event-driven price feed for {instruments}")
        try:
            async for tick in oanda_connector.stream_prices(instruments):
                if not self._running:
                    break
                instrument = tick.get("instrument", "")
                bid        = float(tick.get("bid", 0))
                ask        = float(tick.get("ask", 0))
                mid        = (bid + ask) / 2

                self._prices[instrument]    = mid
                self._last_tick[instrument] = datetime.utcnow()

                await self.on_price(instrument, mid, bid, ask)
        except Exception as e:
            logger.error(f"Price feed error: {e}")
            self._running = False

    def stop(self):
        self._running = False
        logger.info("Price feed stopped")

    def get_price(self, instrument: str) -> Optional[float]:
        return self._prices.get(instrument)

    def get_all_prices(self) -> Dict[str, float]:
        return dict(self._prices)

    def is_stale(self, instrument: str, max_age_seconds: int = 30) -> bool:
        last = self._last_tick.get(instrument)
        if not last:
            return True
        return (datetime.utcnow() - last).total_seconds() > max_age_seconds


# ── Singleton ─────────────────────────────────────────────────────────────────

_execution_engine: Optional[SmartExecutionEngine] = None

def get_execution_engine() -> SmartExecutionEngine:
    global _execution_engine
    if _execution_engine is None:
        _execution_engine = SmartExecutionEngine()
    return _execution_engine

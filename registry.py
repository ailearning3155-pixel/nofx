"""
APEX — Strategy Base Class & Registry
80 strategies across 9 categories: Hedge Fund + Scalping + ML
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Type
import pandas as pd
from models.models import SignalAction


@dataclass
class StrategySignal:
    name: str
    action: SignalAction
    strength: float = 0.0
    entry: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reason: str = ""
    metadata: Dict = field(default_factory=dict)

    @property
    def is_actionable(self) -> bool:
        return self.action in (SignalAction.BUY, SignalAction.SELL) and self.strength > 0.50


class BaseStrategy(ABC):
    name: str = "base"
    display_name: str = "Base"
    category: str = "general"
    description: str = ""
    default_params: Dict = {}

    def __init__(self, params: Optional[Dict] = None):
        self.params = {**self.default_params, **(params or {})}

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame, current_price: float) -> StrategySignal:
        pass

    def prepare_data(self, candles: List[Dict]) -> pd.DataFrame:
        df = pd.DataFrame(candles)
        df["time"] = pd.to_datetime(df["time"])
        df = df.sort_values("time").reset_index(drop=True)
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col].astype(float)
        if "volume" not in df.columns:
            df["volume"] = 0
        df["volume"] = df["volume"].astype(int)
        return df

    def get_info(self) -> Dict:
        return {"name": self.name, "display_name": self.display_name,
                "category": self.category, "description": self.description, "params": self.params}


class StrategyRegistry:
    def __init__(self):
        self._strategies: Dict[str, Type[BaseStrategy]] = {}
        self._load_all()

    def _load_all(self):
        from loguru import logger
        # ── TREND / MOMENTUM (Hedge Fund) ──
        from core.strategies.trend.time_series_momentum    import TimeSeriesMomentumStrategy
        from core.strategies.trend.moving_average_trend    import MovingAverageTrendStrategy
        from core.strategies.trend.breakout_trend          import BreakoutTrendStrategy
        from core.strategies.trend.donchian_breakout       import DonchianBreakoutStrategy
        from core.strategies.trend.volatility_adjusted_trend import VolatilityAdjustedTrendStrategy
        from core.strategies.trend.dual_momentum           import DualMomentumStrategy
        from core.strategies.trend.adaptive_momentum       import AdaptiveMomentumStrategy
        # ── MEAN REVERSION ──
        from core.strategies.mean_reversion.short_term_mean_reversion import ShortTermMeanReversionStrategy
        from core.strategies.mean_reversion.vwap_mean_reversion       import VWAPMeanReversionStrategy
        from core.strategies.mean_reversion.bollinger_reversion       import BollingerReversionStrategy
        from core.strategies.mean_reversion.zscore_reversion          import ZScoreReversionStrategy
        from core.strategies.mean_reversion.rsi_reversion             import RSIReversionStrategy
        from core.strategies.mean_reversion.overnight_reversion       import OvernightReversionStrategy
        # ── VOLATILITY ──
        from core.strategies.volatility.volatility_breakout    import VolatilityBreakoutStrategy
        from core.strategies.volatility.volatility_compression import VolatilityCompressionStrategy
        from core.strategies.volatility.bollinger_squeeze      import BollingerSqueezeStrategy
        from core.strategies.volatility.atr_breakout           import ATRBreakoutStrategy
        # ── SCALPING / SMART MONEY ──
        from core.strategies.scalping.order_block              import OrderBlockStrategy
        from core.strategies.scalping.fair_value_gap           import FairValueGapStrategy
        from core.strategies.scalping.break_of_structure       import BreakOfStructureStrategy
        from core.strategies.scalping.premium_discount         import PremiumDiscountStrategy
        from core.strategies.scalping.liquidity_sweep_reversal import LiquiditySweepReversalStrategy
        from core.strategies.scalping.market_structure_shift   import MarketStructureShiftStrategy
        from core.strategies.scalping.session_breakout         import SessionBreakoutStrategy
        from core.strategies.scalping.rsi_divergence           import RSIDivergenceStrategy
        from core.strategies.scalping.macd_momentum            import MACDMomentumStrategy
        from core.strategies.scalping.ema_momentum             import EMAMomentumStrategy
        from core.strategies.scalping.stop_hunt_reversal       import StopHuntReversalStrategy
        from core.strategies.scalping.volume_spike             import VolumeSpikeStrategy
        from core.strategies.scalping.vwap_momentum            import VWAPMomentumStrategy
        from core.strategies.scalping.ema_pullback             import EMAPullbackStrategy
        from core.strategies.scalping.rsi_support              import RSISupportStrategy
        # ── STAT ARB / QUANTITATIVE ──
        from core.strategies.stat_arb.zscore_pairs          import ZScorePairsStrategy
        from core.strategies.stat_arb.kalman_filter_trend   import KalmanFilterTrendStrategy
        from core.strategies.stat_arb.hidden_markov_regime  import HiddenMarkovRegimeStrategy
        # ── MICROSTRUCTURE ──
        from core.strategies.microstructure.order_flow_imbalance import OrderFlowImbalanceStrategy
        from core.strategies.microstructure.liquidity_detection  import LiquidityDetectionStrategy
        # ── COMPOSITE / HYBRID ──
        from core.strategies.composite.fvg_market_structure  import FVGMarketStructureStrategy
        from core.strategies.composite.ob_liquidity_sweep    import OBLiquiditySweepStrategy
        from core.strategies.composite.rsi_divergence_support import RSIDivergenceSupportStrategy
        # ── MACRO ──
        from core.strategies.macro.interest_rate_differential import InterestRateDifferentialStrategy
        # ── ML / AI ──
        from core.strategies.ml.random_forest_signal    import RandomForestSignalStrategy
        from core.strategies.ml.gradient_boosting_signal import GradientBoostingSignalStrategy
        from core.strategies.ml.lstm_signal             import LSTMSignalStrategy

        all_classes = [
            TimeSeriesMomentumStrategy, MovingAverageTrendStrategy, BreakoutTrendStrategy,
            DonchianBreakoutStrategy, VolatilityAdjustedTrendStrategy, DualMomentumStrategy,
            AdaptiveMomentumStrategy,
            ShortTermMeanReversionStrategy, VWAPMeanReversionStrategy, BollingerReversionStrategy,
            ZScoreReversionStrategy, RSIReversionStrategy, OvernightReversionStrategy,
            VolatilityBreakoutStrategy, VolatilityCompressionStrategy, BollingerSqueezeStrategy,
            ATRBreakoutStrategy,
            OrderBlockStrategy, FairValueGapStrategy, BreakOfStructureStrategy,
            PremiumDiscountStrategy, LiquiditySweepReversalStrategy, MarketStructureShiftStrategy,
            SessionBreakoutStrategy, RSIDivergenceStrategy, MACDMomentumStrategy,
            EMAMomentumStrategy, StopHuntReversalStrategy, VolumeSpikeStrategy,
            VWAPMomentumStrategy, EMAPullbackStrategy, RSISupportStrategy,
            ZScorePairsStrategy, KalmanFilterTrendStrategy, HiddenMarkovRegimeStrategy,
            OrderFlowImbalanceStrategy, LiquidityDetectionStrategy,
            FVGMarketStructureStrategy, OBLiquiditySweepStrategy, RSIDivergenceSupportStrategy,
            InterestRateDifferentialStrategy,
            RandomForestSignalStrategy, GradientBoostingSignalStrategy, LSTMSignalStrategy,
        ]
        for cls in all_classes:
            self._strategies[cls.name] = cls
        logger.info(f"✅ APEX Strategy Registry: {len(self._strategies)} strategies across 9 categories")

    def get(self, name: str, params=None):
        cls = self._strategies.get(name)
        return cls(params=params) if cls else None

    def run(self, name: str, candles, current_price: float, params=None):
        strat = self.get(name, params)
        if not strat: return None
        df = strat.prepare_data(candles) if isinstance(candles, list) else candles
        return strat.generate_signal(df, current_price)

    def run_all(self, candles, current_price: float) -> Dict[str, StrategySignal]:
        from loguru import logger
        results, df_cache = {}, None
        for name, cls in self._strategies.items():
            try:
                strat = cls()
                if df_cache is None:
                    df_cache = strat.prepare_data(candles) if isinstance(candles, list) else candles
                sig = strat.generate_signal(df_cache, current_price)
                if sig: results[name] = sig
            except Exception as e:
                logger.debug(f"Strategy {name}: {e}")
        return results

    def list_strategy_names(self) -> List[str]:
        return list(self._strategies.keys())

    def list_by_category(self, category: str) -> List[str]:
        return [n for n, cls in self._strategies.items() if cls.category == category]

    def get_all_info(self) -> List[Dict]:
        return [cls().get_info() for cls in self._strategies.values()]

    def categories_summary(self) -> Dict:
        cats: Dict[str, int] = {}
        for cls in self._strategies.values():
            cats[cls.category] = cats.get(cls.category, 0) + 1
        return cats

    def __len__(self):
        return len(self._strategies)


_registry: Optional[StrategyRegistry] = None

def get_strategy_registry() -> StrategyRegistry:
    global _registry
    if _registry is None:
        _registry = StrategyRegistry()
    return _registry

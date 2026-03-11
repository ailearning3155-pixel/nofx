"""APEX — Currency Exposure Manager (Implementation Guide Item 3)
Max 40% per currency. Blocks trades that would exceed the limit."""
from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple
from loguru import logger

INSTRUMENT_CURRENCY_EXPOSURE: Dict[str, Dict[str, float]] = {
    "EUR_USD":{"EUR":1,"USD":-1},"GBP_USD":{"GBP":1,"USD":-1},
    "USD_JPY":{"USD":1,"JPY":-1},"USD_CHF":{"USD":1,"CHF":-1},
    "USD_CAD":{"USD":1,"CAD":-1},"AUD_USD":{"AUD":1,"USD":-1},
    "NZD_USD":{"NZD":1,"USD":-1},"EUR_GBP":{"EUR":1,"GBP":-1},
    "EUR_JPY":{"EUR":1,"JPY":-1},"GBP_JPY":{"GBP":1,"JPY":-1},
    "EUR_CHF":{"EUR":1,"CHF":-1},"AUD_JPY":{"AUD":1,"JPY":-1},
    "XAU_USD":{"XAU":1,"USD":-1},"XAG_USD":{"XAG":1,"USD":-1},
    "US500":{"USD":1},"NAS100":{"USD":1},"UK100":{"GBP":1},"GER40":{"EUR":1},
}
MAX_CURRENCY_EXPOSURE_PCT = 0.40

class ExposureManager:
    def __init__(self, max_pct: float = MAX_CURRENCY_EXPOSURE_PCT):
        self.max_pct = max_pct
        self._positions: Dict[str, Dict] = {}

    def check(self, instrument: str, direction: str) -> Tuple[bool, str]:
        exp_map = INSTRUMENT_CURRENCY_EXPOSURE.get(instrument.upper(), {})
        if not exp_map:
            return True, "No mapping"
        current = self._net_exposure()
        total = max(len(self._positions) + 1, 1)
        for currency, mult in exp_map.items():
            sign = 1 if direction == "BUY" else -1
            new_exp = abs(current.get(currency, 0) + mult * sign)
            if new_exp / total > self.max_pct:
                return False, f"{currency} exposure {new_exp/total:.0%} would exceed {self.max_pct:.0%}"
        return True, "OK"

    def add_position(self, instrument: str, direction: str, units: int):
        self._positions[instrument.upper()] = {"direction": direction, "units": units}

    def remove_position(self, instrument: str):
        self._positions.pop(instrument.upper(), None)

    def _net_exposure(self) -> Dict[str, float]:
        net: Dict[str, float] = {}
        for inst, pos in self._positions.items():
            sign = 1 if pos["direction"] == "BUY" else -1
            for ccy, mult in INSTRUMENT_CURRENCY_EXPOSURE.get(inst, {}).items():
                net[ccy] = net.get(ccy, 0) + mult * sign
        return net

    def get_exposure_summary(self) -> Dict:
        net = self._net_exposure()
        total = max(len(self._positions), 1)
        return {
            "open_positions": len(self._positions),
            "max_exposure_pct": self.max_pct,
            "net_exposure": {k: round(abs(v)/total, 3) for k, v in net.items()},
            "limit_breaches": [k for k, v in net.items() if abs(v)/total > self.max_pct],
        }

_em: Optional[ExposureManager] = None
def get_exposure_manager() -> ExposureManager:
    global _em
    if _em is None: _em = ExposureManager()
    return _em

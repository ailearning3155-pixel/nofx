"""APEX — Correlation Risk Manager (Implementation Guide Item 4)
Blocks trades in instruments with |correlation| >= 0.8 with open positions."""
from __future__ import annotations
from typing import Dict, Optional, Set, Tuple

PAIR_CORRELATIONS: Dict[Tuple[str,str], float] = {
    ("EUR_USD","GBP_USD"):0.82, ("EUR_USD","USD_CHF"):-0.91, ("EUR_USD","AUD_USD"):0.68,
    ("EUR_USD","EUR_JPY"):0.75, ("EUR_USD","USD_JPY"):-0.54, ("GBP_USD","AUD_USD"):0.71,
    ("GBP_USD","USD_CHF"):-0.78,("GBP_USD","GBP_JPY"):0.72, ("AUD_USD","NZD_USD"):0.93,
    ("AUD_USD","AUD_JPY"):0.71, ("USD_JPY","USD_CHF"):0.72,  ("USD_JPY","EUR_JPY"):0.85,
    ("USD_JPY","GBP_JPY"):0.88, ("XAU_USD","XAG_USD"):0.89, ("US500","NAS100"):0.92,
}
THRESHOLD = 0.80

class CorrelationManager:
    def __init__(self, threshold: float = THRESHOLD):
        self.threshold = threshold
        self._open: Set[str] = set()

    def check(self, instrument: str) -> Tuple[bool, str]:
        inst = instrument.upper()
        for open_inst in self._open:
            corr = PAIR_CORRELATIONS.get((inst,open_inst)) or PAIR_CORRELATIONS.get((open_inst,inst))
            if corr and abs(corr) >= self.threshold:
                return False, f"{inst} corr={corr:+.2f} with open {open_inst}"
        return True, "OK"

    def add_open(self, instrument: str): self._open.add(instrument.upper())
    def remove_open(self, instrument: str): self._open.discard(instrument.upper())
    def sync(self, instruments: list): self._open = {i.upper() for i in instruments}

    def get_correlation_matrix(self) -> Dict:
        insts = list(self._open)
        matrix = {}
        for a in insts:
            for b in insts:
                if a >= b: continue
                c = PAIR_CORRELATIONS.get((a,b)) or PAIR_CORRELATIONS.get((b,a))
                if c: matrix[f"{a}/{b}"] = round(c,3)
        return {"open_instruments":insts,"threshold":self.threshold,"correlations":matrix,
                "blocked_pairs":[k for k,v in matrix.items() if abs(v)>=self.threshold]}

_cm: Optional[CorrelationManager] = None
def get_correlation_manager() -> CorrelationManager:
    global _cm
    if _cm is None: _cm = CorrelationManager()
    return _cm

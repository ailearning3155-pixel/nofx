"""APEX — System Monitoring Service (Implementation Guide Item 11)
Monitors data feeds, broker connectivity, order failures, latency.
Raises alerts when problems occur."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from loguru import logger

class Status(str,Enum):
    OK="OK"; DEGRADED="DEGRADED"; DOWN="DOWN"; UNKNOWN="UNKNOWN"

@dataclass
class SubsystemHealth:
    name:str; status:Status=Status.UNKNOWN
    latency_ms:float=0.0; last_check:Optional[str]=None
    last_ok:Optional[str]=None; error:Optional[str]=None
    checks_total:int=0; checks_failed:int=0

    @property
    def uptime_pct(self):
        return (self.checks_total-self.checks_failed)/self.checks_total*100 if self.checks_total else 0.0

    def to_dict(self):
        return {"name":self.name,"status":self.status.value,"latency_ms":round(self.latency_ms,1),
                "last_check":self.last_check,"last_ok":self.last_ok,"error":self.error,
                "uptime_pct":round(self.uptime_pct,1)}

@dataclass
class Alert:
    subsystem:str; level:str; message:str
    timestamp:str=field(default_factory=lambda:datetime.utcnow().isoformat())

class MonitoringService:
    SUBSYSTEMS=["oanda","ai_manager","strategy_registry","database","websocket"]

    def __init__(self):
        self._health={s:SubsystemHealth(name=s) for s in self.SUBSYSTEMS}
        self._alerts:List[Alert]=[]
        self._cooldown:Dict[str,datetime]={}
        self._cooldown_secs=300
        self._start=datetime.utcnow()

    async def run_all_checks(self):
        await self._check_oanda()
        await self._check_ai_manager()
        await self._check_strategy_registry()

    async def _check_oanda(self):
        h=self._health["oanda"]; h.checks_total+=1; t0=time.monotonic()
        try:
            from core.oanda.connector import get_oanda
            get_oanda().get_balance()
            h.latency_ms=(time.monotonic()-t0)*1000
            h.status=Status.OK if h.latency_ms<2000 else Status.DEGRADED
            h.last_ok=datetime.utcnow().isoformat(); h.error=None
        except Exception as e:
            h.checks_failed+=1; h.status=Status.DOWN; h.error=str(e)[:120]
            self._alert("oanda","ERROR",f"OANDA down: {h.error}")
        h.last_check=datetime.utcnow().isoformat()

    async def _check_ai_manager(self):
        h=self._health["ai_manager"]; h.checks_total+=1
        try:
            from core.ai.clients import get_ai_manager
            mgr=get_ai_manager(); models=mgr.available_models()
            h.status=Status.OK if models else Status.DEGRADED
            h.last_ok=datetime.utcnow().isoformat(); h.error=None
        except Exception as e:
            h.checks_failed+=1; h.status=Status.DOWN; h.error=str(e)[:120]
        h.last_check=datetime.utcnow().isoformat()

    async def _check_strategy_registry(self):
        h=self._health["strategy_registry"]; h.checks_total+=1
        try:
            from core.strategies.registry import get_strategy_registry
            count=len(get_strategy_registry())
            h.status=Status.OK if count>10 else Status.DEGRADED
            h.last_ok=datetime.utcnow().isoformat(); h.error=None
        except Exception as e:
            h.checks_failed+=1; h.status=Status.DOWN; h.error=str(e)[:120]
            self._alert("strategy_registry","ERROR",f"Registry failed: {h.error}")
        h.last_check=datetime.utcnow().isoformat()

    def _alert(self, subsystem:str, level:str, message:str):
        last=self._cooldown.get(subsystem)
        if last and (datetime.utcnow()-last).seconds<self._cooldown_secs: return
        self._alerts.append(Alert(subsystem=subsystem,level=level,message=message))
        self._cooldown[subsystem]=datetime.utcnow()
        if level=="CRITICAL": logger.critical(f"🚨 [{subsystem}] {message}")
        elif level=="ERROR": logger.error(f"🔴 [{subsystem}] {message}")
        else: logger.warning(f"⚠️  [{subsystem}] {message}")

    def record_order_failure(self, instrument:str, reason:str):
        self._alert("execution","ERROR",f"Order failure [{instrument}]: {reason}")

    def record_feed_timeout(self, feed:str, seconds:float):
        if seconds>30: self._alert("data_feed","WARNING",f"Feed timeout: {feed} ({seconds:.0f}s)")

    def get_health_report(self) -> dict:
        down=[k for k,v in self._health.items() if v.status==Status.DOWN]
        deg=[k for k,v in self._health.items() if v.status==Status.DEGRADED]
        uptime=(datetime.utcnow()-self._start).total_seconds()
        return {"overall_status":"DOWN" if down else "DEGRADED" if deg else "OK",
                "uptime_seconds":round(uptime),
                "subsystems":{k:v.to_dict() for k,v in self._health.items()},
                "active_alerts":len(self._alerts),
                "recent_alerts":[{"subsystem":a.subsystem,"level":a.level,"message":a.message,"timestamp":a.timestamp} for a in self._alerts[-10:]]}

_mon:Optional[MonitoringService]=None
def get_monitoring_service() -> MonitoringService:
    global _mon
    if _mon is None: _mon=MonitoringService()
    return _mon

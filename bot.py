"""
APEX — Telegram Bot Service
Sends trade alerts, daily reports, and debate summaries
"""
from typing import Optional, Dict
from loguru import logger
from config.settings import settings


class TelegramBot:
    """Sends notifications via Telegram Bot API."""

    def __init__(self):
        self.token = settings.telegram.bot_token
        self.chat_id = settings.telegram.chat_id
        self.enabled = settings.telegram.enabled and bool(self.token)

        if self.enabled:
            from telegram import Bot
            self.bot = Bot(token=self.token)
            logger.info("Telegram bot initialized")
        else:
            self.bot = None

    async def _send(self, message: str, parse_mode: str = "HTML"):
        if not self.enabled or not self.bot:
            return
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode,
            )
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")

    async def send_startup_message(self):
        await self._send(
            "🚀 <b>APEX Trading OS is LIVE</b>\n"
            f"Environment: {settings.oanda.environment.upper()}\n"
            f"AI Models: {', '.join(['GPT-4o', 'Claude', 'Gemini', 'DeepSeek', 'Grok', 'Qwen'])}\n"
            "All systems nominal. Trading has begun."
        )

    async def send_trade_opened(self, trade: Dict):
        if not settings.telegram.alert_on_trade:
            return
        direction_emoji = "📈" if trade.get("direction") == "BUY" else "📉"
        await self._send(
            f"{direction_emoji} <b>TRADE OPENED</b>\n"
            f"Instrument: <b>{trade.get('instrument')}</b>\n"
            f"Direction: {trade.get('direction')}\n"
            f"Units: {trade.get('units'):,.0f}\n"
            f"Entry: {trade.get('entry_price'):.5f}\n"
            f"SL: {trade.get('stop_loss', 'None')}\n"
            f"TP: {trade.get('take_profit', 'None')}\n"
            f"AI: {trade.get('ai_model', 'Manual')}\n"
            f"Mode: {trade.get('ai_mode', '-')}\n"
            f"Confidence: {trade.get('confidence', 0):.0%}"
        )

    async def send_trade_closed(self, trade: Dict):
        if not settings.telegram.alert_on_trade:
            return
        pnl = trade.get("pnl", 0)
        emoji = "✅" if pnl >= 0 else "❌"
        await self._send(
            f"{emoji} <b>TRADE CLOSED</b>\n"
            f"Instrument: <b>{trade.get('instrument')}</b>\n"
            f"Direction: {trade.get('direction')}\n"
            f"Entry: {trade.get('entry_price'):.5f} → Exit: {trade.get('exit_price'):.5f}\n"
            f"P&L: <b>${pnl:+.2f}</b> ({trade.get('pnl_pct', 0):+.2f}%)\n"
            f"AI: {trade.get('ai_model', 'Manual')}"
        )

    async def send_debate_result(self, result: Dict):
        if not settings.telegram.alert_on_debate:
            return
        action = result.get("final_action", "HOLD")
        emoji = "🐂" if action == "BUY" else "🐻" if action == "SELL" else "⏸️"
        await self._send(
            f"{emoji} <b>DEBATE RESULT: {result.get('instrument')}</b>\n"
            f"Decision: <b>{action}</b> ({result.get('final_confidence', 0):.0%})\n"
            f"Consensus: {'✅ Yes' if result.get('consensus_reached') else '❌ No'}\n"
            f"Duration: {result.get('duration_seconds', 0):.1f}s\n\n"
            f"📝 {result.get('final_reasoning', '')[:300]}..."
        )

    async def send_risk_alert(self, alert_type: str, message: str):
        await self._send(
            f"🚨 <b>RISK ALERT: {alert_type}</b>\n{message}"
        )

    async def send_daily_report(self, report: Dict):
        if not settings.telegram.daily_report:
            return
        pnl = report.get("daily_pnl", 0)
        emoji = "📊"
        await self._send(
            f"{emoji} <b>APEX Daily Report</b>\n"
            f"{'─' * 25}\n"
            f"Balance: <b>${report.get('balance', 0):,.2f}</b>\n"
            f"Daily P&L: <b>${pnl:+,.2f}</b>\n"
            f"Trades: {report.get('trades', 0)}\n"
            f"Win Rate: {report.get('win_rate', 0):.1f}%\n"
            f"{'─' * 25}\n"
            f"🏆 <b>AI Leaderboard</b>\n" +
            "\n".join([
                f"{i+1}. {m.get('display_name')} — ${m.get('pnl', 0):+,.2f}"
                for i, m in enumerate(report.get("leaderboard", [])[:6])
            ])
        )

    async def send_kill_switch_alert(self, reason: str):
        await self._send(
            f"🚨🚨🚨 <b>KILL SWITCH ACTIVATED</b> 🚨🚨🚨\n"
            f"Reason: {reason}\n"
            "All trading has been HALTED. Manual intervention required."
        )


# Singleton
_bot: Optional[TelegramBot] = None

def get_telegram_bot() -> TelegramBot:
    global _bot
    if _bot is None:
        _bot = TelegramBot()
    return _bot

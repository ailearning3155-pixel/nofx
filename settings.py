"""
APEX — Central Configuration
Supports 3 trading modes: BACKTEST -> PAPER -> LIVE
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import enum


class TradingMode(str, enum.Enum):
    BACKTEST = "backtest"
    PAPER    = "paper"
    LIVE     = "live"


# Every sub-settings class needs:
#   model_config = SettingsConfigDict(env_file=".env", extra="ignore")
# Without extra="ignore", pydantic rejects all env vars it doesn't own.

class OandaSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    account_id:  str = Field("", alias="OANDA_ACCOUNT_ID")
    api_key:     str = Field("", alias="OANDA_API_KEY")
    environment: str = Field("practice", alias="OANDA_ENVIRONMENT")

    @property
    def is_live(self) -> bool:
        return self.environment == "live"


class AISettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    openai_api_key:    str   = Field("", alias="OPENAI_API_KEY")
    anthropic_api_key: str   = Field("", alias="ANTHROPIC_API_KEY")
    google_api_key:    str   = Field("", alias="GOOGLE_API_KEY")
    deepseek_api_key:  str   = Field("", alias="DEEPSEEK_API_KEY")
    grok_api_key:      str   = Field("", alias="GROK_API_KEY")
    qwen_api_key:      str   = Field("", alias="QWEN_API_KEY")
    request_timeout:   int   = Field(30,  alias="AI_REQUEST_TIMEOUT")
    max_retries:       int   = Field(3,   alias="AI_MAX_RETRIES")
    temperature:       float = Field(0.3, alias="AI_TEMPERATURE")
    default_model:     str   = Field("deepseek", alias="DEFAULT_AI_MODEL")


class TradingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    mode:               TradingMode = Field(TradingMode.BACKTEST, alias="TRADING_MODE")
    candle_granularity: str         = Field("H1",  alias="CANDLE_GRANULARITY")
    max_open_trades:    int         = Field(3,     alias="MAX_OPEN_TRADES")
    risk_per_trade_pct: float       = Field(1.0,   alias="DEFAULT_RISK_PER_TRADE")
    max_daily_loss_pct: float       = Field(3.0,   alias="MAX_DAILY_LOSS_PCT")
    max_drawdown_pct:   float       = Field(10.0,  alias="MAX_DRAWDOWN_PCT")

    instruments_raw: str = Field("EUR_USD,GBP_USD,USD_JPY,XAU_USD,US500", alias="DEFAULT_INSTRUMENTS")

    @property
    def instruments(self) -> List[str]:
        return [i.strip() for i in self.instruments_raw.split(",") if i.strip()]


class CompetitionSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    enabled:           bool  = Field(True,      alias="COMPETITION_MODE")
    starting_balance:  float = Field(100000.0,  alias="COMPETITION_STARTING_BALANCE")
    reset_interval:    str   = Field("monthly", alias="COMPETITION_RESET_INTERVAL")


class DebateSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    enabled:       bool = Field(True, alias="DEBATE_ENABLED")
    timeout:       int  = Field(45,   alias="DEBATE_TIMEOUT")
    min_consensus: int  = Field(3,    alias="MIN_CONSENSUS_REQUIRED")


class NewsSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    api_key:         str = Field("",       alias="NEWS_API_KEY")
    update_interval: int = Field(900,      alias="NEWS_UPDATE_INTERVAL")
    sentiment_model: str = Field("vader",  alias="SENTIMENT_MODEL")


class CalendarSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    provider:          str  = Field("forexfactory", alias="CALENDAR_PROVIDER")
    lookahead_hours:   int  = Field(24,             alias="CALENDAR_LOOKAHEAD_HOURS")
    high_impact_pause: bool = Field(True,           alias="HIGH_IMPACT_PAUSE")


class TelegramSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    bot_token:         str  = Field("",     alias="TELEGRAM_BOT_TOKEN")
    chat_id:           str  = Field("",     alias="TELEGRAM_CHAT_ID")
    enabled:           bool = Field(False,  alias="TELEGRAM_ALERTS_ENABLED")
    alert_on_trade:    bool = Field(True,   alias="TELEGRAM_ALERT_ON_TRADE")
    alert_on_debate:   bool = Field(False,  alias="TELEGRAM_ALERT_ON_DEBATE")
    daily_report:      bool = Field(True,   alias="TELEGRAM_DAILY_REPORT")
    daily_report_time: str  = Field("20:00",alias="TELEGRAM_DAILY_REPORT_TIME")


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    env:          str  = Field("development",                                    alias="APP_ENV")
    host:         str  = Field("0.0.0.0",                                        alias="APP_HOST")
    port:         int  = Field(8000,                                             alias="APP_PORT")
    secret_key:   str  = Field("change_me_32chars_minimum",                      alias="SECRET_KEY")
    debug:        bool = Field(True,                                             alias="DEBUG")
    database_url: str  = Field("postgresql://apex:apex_password@localhost:5432/apex_db", alias="DATABASE_URL")
    redis_url:    str  = Field("redis://localhost:6379/0",                       alias="REDIS_URL")

    # Sub-settings are instantiated independently — they each read .env themselves
    oanda:       OandaSettings       = OandaSettings()
    ai:          AISettings          = AISettings()
    trading:     TradingSettings     = TradingSettings()
    competition: CompetitionSettings = CompetitionSettings()
    debate:      DebateSettings      = DebateSettings()
    news:        NewsSettings        = NewsSettings()
    calendar:    CalendarSettings    = CalendarSettings()
    telegram:    TelegramSettings    = TelegramSettings()


@lru_cache()
def get_settings() -> AppSettings:
    return AppSettings()


settings = get_settings()

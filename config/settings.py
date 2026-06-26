import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Binance
    BINANCE_API_KEY: str = Field(default="", env="BINANCE_API_KEY")
    BINANCE_API_SECRET: str = Field(default="", env="BINANCE_API_SECRET")
    BINANCE_TESTNET: bool = Field(default=False, env="BINANCE_TESTNET")

    # Telegram
    TELEGRAM_BOT_TOKEN: str = Field(default="", env="TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHANNEL_ID: str = Field(default="", env="TELEGRAM_CHANNEL_ID")
    TELEGRAM_ADMIN_IDS: List[int] = Field(default=[], env="TELEGRAM_ADMIN_IDS")

    # Database
    DATABASE_URL: str = Field(default="sqlite:///./nexara.db", env="DATABASE_URL")
    DATABASE_ECHO: bool = Field(default=False, env="DATABASE_ECHO")

    # Scanner
    SCAN_INTERVAL_SECONDS: int = Field(default=30, env="SCAN_INTERVAL_SECONDS")
    MIN_VOLUME_USDT: float = Field(default=1_000_000.0, env="MIN_VOLUME_USDT")
    MIN_CONFIDENCE_SCORE: float = Field(default=90.0, env="MIN_CONFIDENCE_SCORE")
    MAX_PAIRS_TO_SCAN: int = Field(default=200, env="MAX_PAIRS_TO_SCAN")

    # Signal
    SIGNAL_COOLDOWN_MINUTES: int = Field(default=60, env="SIGNAL_COOLDOWN_MINUTES")
    MAX_SIGNALS_PER_HOUR: int = Field(default=10, env="MAX_SIGNALS_PER_HOUR")
    DEFAULT_RISK_PERCENT: float = Field(default=1.0, env="DEFAULT_RISK_PERCENT")
    DEFAULT_LEVERAGE: int = Field(default=10, env="DEFAULT_LEVERAGE")

    # Risk
    MAX_RISK_PER_TRADE: float = Field(default=2.0, env="MAX_RISK_PER_TRADE")
    MIN_RISK_REWARD: float = Field(default=2.0, env="MIN_RISK_REWARD")
    ATR_SL_MULTIPLIER: float = Field(default=1.5, env="ATR_SL_MULTIPLIER")
    ATR_TP1_MULTIPLIER: float = Field(default=1.5, env="ATR_TP1_MULTIPLIER")
    ATR_TP2_MULTIPLIER: float = Field(default=3.0, env="ATR_TP2_MULTIPLIER")
    ATR_TP3_MULTIPLIER: float = Field(default=5.0, env="ATR_TP3_MULTIPLIER")

    # API
    API_HOST: str = Field(default="0.0.0.0", env="API_HOST")
    API_PORT: int = Field(default=8000, env="API_PORT")
    API_SECRET_KEY: str = Field(default="nexara_secret_key", env="API_SECRET_KEY")
    API_WORKERS: int = Field(default=1, env="API_WORKERS")

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=60, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60, env="RATE_LIMIT_WINDOW_SECONDS")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: str = Field(default="logs/nexara.log", env="LOG_FILE")
    LOG_MAX_BYTES: int = Field(default=10_485_760, env="LOG_MAX_BYTES")
    LOG_BACKUP_COUNT: int = Field(default=5, env="LOG_BACKUP_COUNT")

    # External APIs
    COINGECKO_API_URL: str = Field(default="https://api.coingecko.com/api/v3", env="COINGECKO_API_URL")
    ALTERNATIVE_ME_API_URL: str = Field(default="https://api.alternative.me/fng/", env="ALTERNATIVE_ME_API_URL")
    CRYPTO_NEWS_API_KEY: str = Field(default="", env="CRYPTO_NEWS_API_KEY")
    CRYPTO_NEWS_API_URL: str = Field(default="https://cryptonews-api.com/api/v1", env="CRYPTO_NEWS_API_URL")

    # Environment
    ENVIRONMENT: str = Field(default="production", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")

    # Timeframes
    TIMEFRAMES: List[str] = ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"]
    PRIMARY_TIMEFRAMES: List[str] = ["15m", "1h", "4h"]

    # Indicators
    EMA_FAST: int = 20
    EMA_MID: int = 50
    EMA_SLOW: int = 100
    EMA_TREND: int = 200
    RSI_PERIOD: int = 14
    RSI_OVERBOUGHT: float = 70.0
    RSI_OVERSOLD: float = 30.0
    MACD_FAST: int = 12
    MACD_SLOW: int = 26
    MACD_SIGNAL: int = 9
    ADX_PERIOD: int = 14
    ADX_THRESHOLD: float = 25.0
    ATR_PERIOD: int = 14
    BB_PERIOD: int = 20
    BB_STD: float = 2.0
    STOCH_RSI_PERIOD: int = 14
    CCI_PERIOD: int = 20
    MFI_PERIOD: int = 14
    OBV_EMA_PERIOD: int = 21
    SUPERTREND_PERIOD: int = 10
    SUPERTREND_MULTIPLIER: float = 3.0

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_debug(self) -> bool:
        return self.DEBUG

    def get_binance_config(self) -> dict:
        return {
            "apiKey": self.BINANCE_API_KEY,
            "secret": self.BINANCE_API_SECRET,
            "enableRateLimit": True,
            "options": {
                "defaultType": "future",
                "adjustForTimeDifference": True,
            },
            "sandbox": self.BINANCE_TESTNET,
        }


settings = Settings()

os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

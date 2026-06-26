import json
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, Text, ForeignKey, Index, BigInteger
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    language_code = Column(String(10), default="en")
    is_active = Column(Boolean, default=True)
    is_banned = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    signals_received = Column(Integer, default=0)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)

    premium = relationship("Premium", back_populates="user", uselist=False)
    settings = relationship("Setting", back_populates="user", uselist=False)
    trades = relationship("Trade", back_populates="user")

    __table_args__ = (
        Index("idx_users_telegram_id", "telegram_id"),
        Index("idx_users_is_active", "is_active"),
    )

    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pair = Column(String(20), nullable=False, index=True)
    direction = Column(String(10), nullable=False)
    timeframe = Column(String(10), nullable=False)
    entry = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    tp1 = Column(Float, nullable=False)
    tp2 = Column(Float, nullable=False)
    tp3 = Column(Float, nullable=False)
    risk_reward = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    trend = Column(String(20), nullable=False)
    reasons = Column(Text, nullable=True)
    indicators_passed = Column(Text, nullable=True)
    smc_confirmation = Column(Text, nullable=True)
    estimated_win_rate = Column(Float, default=0.0)
    trade_duration = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    is_sent = Column(Boolean, default=False)
    result = Column(String(20), nullable=True)
    profit_loss = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    closed_at = Column(DateTime, nullable=True)
    close_price = Column(Float, nullable=True)

    trades = relationship("Trade", back_populates="signal")

    __table_args__ = (
        Index("idx_signals_pair", "pair"),
        Index("idx_signals_created_at", "created_at"),
        Index("idx_signals_confidence", "confidence"),
        Index("idx_signals_is_active", "is_active"),
    )

    def get_reasons(self) -> list:
        if self.reasons:
            try:
                return json.loads(self.reasons)
            except Exception:
                return []
        return []

    def set_reasons(self, reasons: list) -> None:
        self.reasons = json.dumps(reasons)

    def get_indicators_passed(self) -> list:
        if self.indicators_passed:
            try:
                return json.loads(self.indicators_passed)
            except Exception:
                return []
        return []

    def set_indicators_passed(self, indicators: list) -> None:
        self.indicators_passed = json.dumps(indicators)

    def get_smc_confirmation(self) -> list:
        if self.smc_confirmation:
            try:
                return json.loads(self.smc_confirmation)
            except Exception:
                return []
        return []

    def set_smc_confirmation(self, smc: list) -> None:
        self.smc_confirmation = json.dumps(smc)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pair": self.pair,
            "direction": self.direction,
            "timeframe": self.timeframe,
            "entry": self.entry,
            "stop_loss": self.stop_loss,
            "tp1": self.tp1,
            "tp2": self.tp2,
            "tp3": self.tp3,
            "risk_reward": self.risk_reward,
            "confidence": self.confidence,
            "trend": self.trend,
            "reasons": self.get_reasons(),
            "indicators_passed": self.get_indicators_passed(),
            "smc_confirmation": self.get_smc_confirmation(),
            "estimated_win_rate": self.estimated_win_rate,
            "trade_duration": self.trade_duration,
            "is_active": self.is_active,
            "result": self.result,
            "profit_loss": self.profit_loss,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }

    def __repr__(self):
        return f"<Signal(pair={self.pair}, direction={self.direction}, confidence={self.confidence})>"


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True, index=True)
    pair = Column(String(20), nullable=False)
    direction = Column(String(10), nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=False)
    tp1 = Column(Float, nullable=False)
    tp2 = Column(Float, nullable=False)
    tp3 = Column(Float, nullable=False)
    leverage = Column(Integer, default=10)
    position_size = Column(Float, nullable=True)
    risk_amount = Column(Float, nullable=True)
    status = Column(String(20), default="OPEN")
    result = Column(String(20), nullable=True)
    profit_loss = Column(Float, nullable=True)
    profit_loss_pct = Column(Float, nullable=True)
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    user = relationship("User", back_populates="trades")
    signal = relationship("Signal", back_populates="trades")

    __table_args__ = (
        Index("idx_trades_user_id", "user_id"),
        Index("idx_trades_status", "status"),
        Index("idx_trades_pair", "pair"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "signal_id": self.signal_id,
            "pair": self.pair,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "stop_loss": self.stop_loss,
            "tp1": self.tp1,
            "tp2": self.tp2,
            "tp3": self.tp3,
            "leverage": self.leverage,
            "position_size": self.position_size,
            "status": self.status,
            "result": self.result,
            "profit_loss": self.profit_loss,
            "profit_loss_pct": self.profit_loss_pct,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }

    def __repr__(self):
        return f"<Trade(pair={self.pair}, status={self.status}, pl={self.profit_loss})>"


class Premium(Base):
    __tablename__ = "premium"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    plan = Column(String(50), default="free")
    is_active = Column(Boolean, default=False)
    started_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    payment_method = Column(String(50), nullable=True)
    payment_id = Column(String(255), nullable=True)
    amount_paid = Column(Float, nullable=True)
    currency = Column(String(10), nullable=True)
    auto_renew = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="premium")

    __table_args__ = (
        Index("idx_premium_user_id", "user_id"),
        Index("idx_premium_is_active", "is_active"),
    )

    def is_valid(self) -> bool:
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "plan": self.plan,
            "is_active": self.is_active,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "auto_renew": self.auto_renew,
        }

    def __repr__(self):
        return f"<Premium(user_id={self.user_id}, plan={self.plan}, active={self.is_active})>"


class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(20), nullable=False, index=True)
    module = Column(String(100), nullable=True)
    message = Column(Text, nullable=False)
    extra = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_logs_level", "level"),
        Index("idx_logs_created_at", "created_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "level": self.level,
            "module": self.module,
            "message": self.message,
            "extra": self.extra,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Log(level={self.level}, module={self.module})>"


class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    notifications_enabled = Column(Boolean, default=True)
    signal_notifications = Column(Boolean, default=True)
    min_confidence = Column(Float, default=90.0)
    preferred_timeframes = Column(Text, default='["15m","1h","4h"]')
    preferred_pairs = Column(Text, default="[]")
    risk_per_trade = Column(Float, default=1.0)
    leverage = Column(Integer, default=10)
    language = Column(String(10), default="en")
    theme = Column(String(20), default="dark")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="settings")

    def get_preferred_timeframes(self) -> list:
        try:
            return json.loads(self.preferred_timeframes)
        except Exception:
            return ["15m", "1h", "4h"]

    def get_preferred_pairs(self) -> list:
        try:
            return json.loads(self.preferred_pairs)
        except Exception:
            return []

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "notifications_enabled": self.notifications_enabled,
            "signal_notifications": self.signal_notifications,
            "min_confidence": self.min_confidence,
            "preferred_timeframes": self.get_preferred_timeframes(),
            "preferred_pairs": self.get_preferred_pairs(),
            "risk_per_trade": self.risk_per_trade,
            "leverage": self.leverage,
            "language": self.language,
        }

    def __repr__(self):
        return f"<Setting(user_id={self.user_id})>"


__all__ = [
    "Base",
    "User",
    "Signal",
    "Trade",
    "Premium",
    "Log",
    "Setting",
]

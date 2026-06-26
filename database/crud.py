import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_, desc
from database.models import User, Signal, Trade, Premium, Log, Setting
from utils.logger import logger


class UserCRUD:

    @staticmethod
    async def create(
        db: AsyncSession,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: str = "en",
    ) -> User:
        try:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code,
            )
            db.add(user)
            await db.flush()

            setting = Setting(user_id=user.id)
            db.add(setting)

            premium = Premium(user_id=user.id)
            db.add(premium)

            await db.commit()
            await db.refresh(user)
            logger.info(f"Created user: {telegram_id}")
            return user
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating user {telegram_id}: {e}")
            raise

    @staticmethod
    async def get_by_telegram_id(
        db: AsyncSession,
        telegram_id: int,
    ) -> Optional[User]:
        try:
            result = await db.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user {telegram_id}: {e}")
            return None

    @staticmethod
    async def get_or_create(
        db: AsyncSession,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: str = "en",
    ) -> tuple[User, bool]:
        user = await UserCRUD.get_by_telegram_id(db, telegram_id)
        if user:
            user.last_seen = datetime.utcnow()
            if username:
                user.username = username
            if first_name:
                user.first_name = first_name
            await db.commit()
            return user, False
        user = await UserCRUD.create(
            db, telegram_id, username, first_name, last_name, language_code
        )
        return user, True

    @staticmethod
    async def get_all_active(db: AsyncSession) -> List[User]:
        try:
            result = await db.execute(
                select(User).where(
                    and_(User.is_active == True, User.is_banned == False)
                )
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []

    @staticmethod
    async def get_all_admin(db: AsyncSession) -> List[User]:
        try:
            result = await db.execute(
                select(User).where(User.is_admin == True)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting admin users: {e}")
            return []

    @staticmethod
    async def update(
        db: AsyncSession,
        telegram_id: int,
        **kwargs,
    ) -> Optional[User]:
        try:
            await db.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(**kwargs, last_seen=datetime.utcnow())
            )
            await db.commit()
            return await UserCRUD.get_by_telegram_id(db, telegram_id)
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating user {telegram_id}: {e}")
            return None

    @staticmethod
    async def increment_signals(db: AsyncSession, telegram_id: int) -> None:
        try:
            await db.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(signals_received=User.signals_received + 1)
            )
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Error incrementing signals for {telegram_id}: {e}")

    @staticmethod
    async def count_all(db: AsyncSession) -> int:
        try:
            result = await db.execute(select(func.count(User.id)))
            return result.scalar_one()
        except Exception as e:
            logger.error(f"Error counting users: {e}")
            return 0

    @staticmethod
    async def ban(db: AsyncSession, telegram_id: int) -> bool:
        try:
            await db.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(is_banned=True, is_active=False)
            )
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            logger.error(f"Error banning user {telegram_id}: {e}")
            return False


class SignalCRUD:

    @staticmethod
    async def create(
        db: AsyncSession,
        signal_data: Dict[str, Any],
    ) -> Signal:
        try:
            signal = Signal(
                pair=signal_data["pair"],
                direction=signal_data["direction"],
                timeframe=signal_data["timeframe"],
                entry=signal_data["entry"],
                stop_loss=signal_data["stop_loss"],
                tp1=signal_data["tp1"],
                tp2=signal_data["tp2"],
                tp3=signal_data["tp3"],
                risk_reward=signal_data["risk_reward"],
                confidence=signal_data["confidence"],
                trend=signal_data["trend"],
                estimated_win_rate=signal_data.get("estimated_win_rate", 0.0),
                trade_duration=signal_data.get("trade_duration", ""),
            )
            signal.set_reasons(signal_data.get("reasons", []))
            signal.set_indicators_passed(signal_data.get("indicators_passed", []))
            signal.set_smc_confirmation(signal_data.get("smc_confirmation", []))
            db.add(signal)
            await db.commit()
            await db.refresh(signal)
            logger.info(f"Created signal: {signal.pair} {signal.direction} conf={signal.confidence}")
            return signal
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating signal: {e}")
            raise

    @staticmethod
    async def get_by_id(db: AsyncSession, signal_id: int) -> Optional[Signal]:
        try:
            result = await db.execute(
                select(Signal).where(Signal.id == signal_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting signal {signal_id}: {e}")
            return None

    @staticmethod
    async def get_recent(
        db: AsyncSession,
        limit: int = 10,
        min_confidence: float = 90.0,
    ) -> List[Signal]:
        try:
            result = await db.execute(
                select(Signal)
                .where(Signal.confidence >= min_confidence)
                .order_by(desc(Signal.created_at))
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting recent signals: {e}")
            return []

    @staticmethod
    async def get_top(
        db: AsyncSession,
        limit: int = 10,
        hours: int = 24,
    ) -> List[Signal]:
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            result = await db.execute(
                select(Signal)
                .where(
                    and_(
                        Signal.created_at >= since,
                        Signal.is_active == True,
                    )
                )
                .order_by(desc(Signal.confidence))
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting top signals: {e}")
            return []

    @staticmethod
    async def get_active(db: AsyncSession) -> List[Signal]:
        try:
            result = await db.execute(
                select(Signal)
                .where(Signal.is_active == True)
                .order_by(desc(Signal.created_at))
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting active signals: {e}")
            return []

    @staticmethod
    async def get_by_pair(
        db: AsyncSession,
        pair: str,
        limit: int = 5,
    ) -> List[Signal]:
        try:
            result = await db.execute(
                select(Signal)
                .where(Signal.pair == pair)
                .order_by(desc(Signal.created_at))
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting signals for {pair}: {e}")
            return []

    @staticmethod
    async def check_cooldown(
        db: AsyncSession,
        pair: str,
        timeframe: str,
        cooldown_minutes: int = 60,
    ) -> bool:
        try:
            since = datetime.utcnow() - timedelta(minutes=cooldown_minutes)
            result = await db.execute(
                select(Signal)
                .where(
                    and_(
                        Signal.pair == pair,
                        Signal.timeframe == timeframe,
                        Signal.created_at >= since,
                    )
                )
                .limit(1)
            )
            existing = result.scalar_one_or_none()
            return existing is None
        except Exception as e:
            logger.error(f"Error checking cooldown for {pair}: {e}")
            return True

    @staticmethod
    async def mark_sent(db: AsyncSession, signal_id: int) -> None:
        try:
            await db.execute(
                update(Signal)
                .where(Signal.id == signal_id)
                .values(is_sent=True)
            )
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Error marking signal {signal_id} as sent: {e}")

    @staticmethod
    async def close_signal(
        db: AsyncSession,
        signal_id: int,
        result: str,
        close_price: float,
        profit_loss: float,
    ) -> None:
        try:
            await db.execute(
                update(Signal)
                .where(Signal.id == signal_id)
                .values(
                    is_active=False,
                    result=result,
                    close_price=close_price,
                    profit_loss=profit_loss,
                    closed_at=datetime.utcnow(),
                )
            )
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Error closing signal {signal_id}: {e}")

    @staticmethod
    async def count_today(db: AsyncSession) -> int:
        try:
            since = datetime.utcnow().replace(hour=0, minute=0, second=0)
            result = await db.execute(
                select(func.count(Signal.id))
                .where(Signal.created_at >= since)
            )
            return result.scalar_one()
        except Exception as e:
            logger.error(f"Error counting today signals: {e}")
            return 0

    @staticmethod
    async def get_win_rate(db: AsyncSession) -> float:
        try:
            result = await db.execute(
                select(func.count(Signal.id))
                .where(Signal.result.in_(["WIN", "LOSS"]))
            )
            total = result.scalar_one()
            if total == 0:
                return 0.0
            result = await db.execute(
                select(func.count(Signal.id))
                .where(Signal.result == "WIN")
            )
            wins = result.scalar_one()
            return (wins / total) * 100
        except Exception as e:
            logger.error(f"Error calculating win rate: {e}")
            return 0.0


class TradeCRUD:

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: int,
        trade_data: Dict[str, Any],
    ) -> Trade:
        try:
            trade = Trade(
                user_id=user_id,
                signal_id=trade_data.get("signal_id"),
                pair=trade_data["pair"],
                direction=trade_data["direction"],
                entry_price=trade_data["entry_price"],
                stop_loss=trade_data["stop_loss"],
                tp1=trade_data["tp1"],
                tp2=trade_data["tp2"],
                tp3=trade_data["tp3"],
                leverage=trade_data.get("leverage", 10),
                position_size=trade_data.get("position_size"),
                risk_amount=trade_data.get("risk_amount"),
            )
            db.add(trade)
            await db.commit()
            await db.refresh(trade)
            return trade
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating trade: {e}")
            raise

    @staticmethod
    async def get_by_user(
        db: AsyncSession,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> List[Trade]:
        try:
            query = select(Trade).where(Trade.user_id == user_id)
            if status:
                query = query.where(Trade.status == status)
            query = query.order_by(desc(Trade.opened_at)).limit(limit)
            result = await db.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting trades for user {user_id}: {e}")
            return []

    @staticmethod
    async def close_trade(
        db: AsyncSession,
        trade_id: int,
        exit_price: float,
        result: str,
        profit_loss: float,
        profit_loss_pct: float,
    ) -> None:
        try:
            await db.execute(
                update(Trade)
                .where(Trade.id == trade_id)
                .values(
                    exit_price=exit_price,
                    status="CLOSED",
                    result=result,
                    profit_loss=profit_loss,
                    profit_loss_pct=profit_loss_pct,
                    closed_at=datetime.utcnow(),
                )
            )
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Error closing trade {trade_id}: {e}")

    @staticmethod
    async def get_stats(db: AsyncSession, user_id: int) -> Dict[str, Any]:
        try:
            result = await db.execute(
                select(func.count(Trade.id))
                .where(Trade.user_id == user_id)
            )
            total = result.scalar_one()

            result = await db.execute(
                select(func.count(Trade.id))
                .where(and_(Trade.user_id == user_id, Trade.result == "WIN"))
            )
            wins = result.scalar_one()

            result = await db.execute(
                select(func.sum(Trade.profit_loss))
                .where(Trade.user_id == user_id)
            )
            total_pnl = result.scalar_one() or 0.0

            win_rate = (wins / total * 100) if total > 0 else 0.0

            return {
                "total_trades": total,
                "winning_trades": wins,
                "losing_trades": total - wins,
                "win_rate": round(win_rate, 2),
                "total_pnl": round(total_pnl, 2),
            }
        except Exception as e:
            logger.error(f"Error getting trade stats for user {user_id}: {e}")
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
            }


class PremiumCRUD:

    @staticmethod
    async def get_by_user_id(
        db: AsyncSession,
        user_id: int,
    ) -> Optional[Premium]:
        try:
            result = await db.execute(
                select(Premium).where(Premium.user_id == user_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting premium for user {user_id}: {e}")
            return None

    @staticmethod
    async def activate(
        db: AsyncSession,
        user_id: int,
        plan: str,
        days: int,
        payment_method: Optional[str] = None,
        amount_paid: Optional[float] = None,
    ) -> Optional[Premium]:
        try:
            now = datetime.utcnow()
            expires = now + timedelta(days=days)
            premium = await PremiumCRUD.get_by_user_id(db, user_id)
            if premium:
                await db.execute(
                    update(Premium)
                    .where(Premium.user_id == user_id)
                    .values(
                        plan=plan,
                        is_active=True,
                        started_at=now,
                        expires_at=expires,
                        payment_method=payment_method,
                        amount_paid=amount_paid,
                        updated_at=now,
                    )
                )
            else:
                premium = Premium(
                    user_id=user_id,
                    plan=plan,
                    is_active=True,
                    started_at=now,
                    expires_at=expires,
                    payment_method=payment_method,
                    amount_paid=amount_paid,
                )
                db.add(premium)
            await db.commit()
            return await PremiumCRUD.get_by_user_id(db, user_id)
        except Exception as e:
            await db.rollback()
            logger.error(f"Error activating premium for user {user_id}: {e}")
            return None

    @staticmethod
    async def is_premium(db: AsyncSession, user_id: int) -> bool:
        try:
            premium = await PremiumCRUD.get_by_user_id(db, user_id)
            if not premium:
                return False
            return premium.is_valid()
        except Exception as e:
            logger.error(f"Error checking premium for user {user_id}: {e}")
            return False


class LogCRUD:

    @staticmethod
    async def create(
        db: AsyncSession,
        level: str,
        message: str,
        module: Optional[str] = None,
        extra: Optional[Dict] = None,
    ) -> None:
        try:
            log = Log(
                level=level,
                message=message,
                module=module,
                extra=json.dumps(extra) if extra else None,
            )
            db.add(log)
            await db.commit()
        except Exception as e:
            logger.error(f"Error creating log entry: {e}")

    @staticmethod
    async def get_recent(
        db: AsyncSession,
        level: Optional[str] = None,
        limit: int = 100,
    ) -> List[Log]:
        try:
            query = select(Log)
            if level:
                query = query.where(Log.level == level)
            query = query.order_by(desc(Log.created_at)).limit(limit)
            result = await db.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            return []

    @staticmethod
    async def cleanup_old(db: AsyncSession, days: int = 30) -> int:
        try:
            since = datetime.utcnow() - timedelta(days=days)
            result = await db.execute(
                delete(Log).where(Log.created_at < since)
            )
            await db.commit()
            return result.rowcount
        except Exception as e:
            await db.rollback()
            logger.error(f"Error cleaning up logs: {e}")
            return 0


class SettingCRUD:

    @staticmethod
    async def get_by_user_id(
        db: AsyncSession,
        user_id: int,
    ) -> Optional[Setting]:
        try:
            result = await db.execute(
                select(Setting).where(Setting.user_id == user_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting settings for user {user_id}: {e}")
            return None

    @staticmethod
    async def update(
        db: AsyncSession,
        user_id: int,
        **kwargs,
    ) -> Optional[Setting]:
        try:
            if "preferred_timeframes" in kwargs and isinstance(kwargs["preferred_timeframes"], list):
                kwargs["preferred_timeframes"] = json.dumps(kwargs["preferred_timeframes"])
            if "preferred_pairs" in kwargs and isinstance(kwargs["preferred_pairs"], list):
                kwargs["preferred_pairs"] = json.dumps(kwargs["preferred_pairs"])
            await db.execute(
                update(Setting)
                .where(Setting.user_id == user_id)
                .values(**kwargs, updated_at=datetime.utcnow())
            )
            await db.commit()
            return await SettingCRUD.get_by_user_id(db, user_id)
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating settings for user {user_id}: {e}")
            return None

    @staticmethod
    async def get_min_confidence(db: AsyncSession, user_id: int) -> float:
        try:
            setting = await SettingCRUD.get_by_user_id(db, user_id)
            if setting:
                return setting.min_confidence
            return 90.0
        except Exception as e:
            logger.error(f"Error getting min confidence for user {user_id}: {e}")
            return 90.0


__all__ = [
    "UserCRUD",
    "SignalCRUD",
    "TradeCRUD",
    "PremiumCRUD",
    "LogCRUD",
    "SettingCRUD",
]

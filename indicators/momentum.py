import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from config.settings import settings
from utils.logger import logger


class MomentumIndicators:

    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        try:
            delta = series.diff()
            gain = delta.where(delta > 0, 0.0)
            loss = -delta.where(delta < 0, 0.0)
            avg_gain = gain.ewm(span=period, adjust=False).mean()
            avg_loss = loss.ewm(span=period, adjust=False).mean()
            rs = avg_gain / avg_loss.replace(0, np.nan)
            rsi_val = 100 - (100 / (1 + rs))
            return rsi_val
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return pd.Series(dtype=float)

    @staticmethod
    def calculate_rsi(df: pd.DataFrame) -> pd.DataFrame:
        try:
            df["rsi"] = MomentumIndicators.rsi(df["close"], settings.RSI_PERIOD)
            return df
        except Exception as e:
            logger.error(f"Error calculating RSI dataframe: {e}")
            return df

    @staticmethod
    def stochastic_rsi(
        series: pd.Series,
        rsi_period: int = 14,
        stoch_period: int = 14,
        k_period: int = 3,
        d_period: int = 3,
    ) -> Tuple[pd.Series, pd.Series]:
        try:
            rsi_vals = MomentumIndicators.rsi(series, rsi_period)
            rsi_min = rsi_vals.rolling(window=stoch_period).min()
            rsi_max = rsi_vals.rolling(window=stoch_period).max()
            stoch_rsi = (rsi_vals - rsi_min) / (rsi_max - rsi_min).replace(0, np.nan)
            k_line = stoch_rsi.rolling(window=k_period).mean() * 100
            d_line = k_line.rolling(window=d_period).mean()
            return k_line, d_line
        except Exception as e:
            logger.error(f"Error calculating Stochastic RSI: {e}")
            return pd.Series(dtype=float), pd.Series(dtype=float)

    @staticmethod
    def calculate_stochastic_rsi(df: pd.DataFrame) -> pd.DataFrame:
        try:
            k, d = MomentumIndicators.stochastic_rsi(
                df["close"],
                settings.STOCH_RSI_PERIOD,
                settings.STOCH_RSI_PERIOD,
            )
            df["stoch_rsi_k"] = k
            df["stoch_rsi_d"] = d
            return df
        except Exception as e:
            logger.error(f"Error calculating Stochastic RSI dataframe: {e}")
            return df

    @staticmethod
    def cci(
        df: pd.DataFrame,
        period: int = 20,
    ) -> pd.Series:
        try:
            typical_price = (df["high"] + df["low"] + df["close"]) / 3
            sma = typical_price.rolling(window=period).mean()
            mean_dev = typical_price.rolling(window=period).apply(
                lambda x: np.mean(np.abs(x - np.mean(x))), raw=True
            )
            cci_val = (typical_price - sma) / (0.015 * mean_dev.replace(0, np.nan))
            return cci_val
        except Exception as e:
            logger.error(f"Error calculating CCI: {e}")
            return pd.Series(dtype=float)

    @staticmethod
    def calculate_cci(df: pd.DataFrame) -> pd.DataFrame:
        try:
            df["cci"] = MomentumIndicators.cci(df, settings.CCI_PERIOD)
            return df
        except Exception as e:
            logger.error(f"Error calculating CCI dataframe: {e}")
            return df

    @staticmethod
    def get_rsi_signal(df: pd.DataFrame) -> Dict[str, Any]:
        try:
            last = df.iloc[-1]
            prev = df.iloc[-2]
            rsi = last.get("rsi", np.nan)
            prev_rsi = prev.get("rsi", np.nan)

            if pd.isna(rsi):
                return {
                    "signal": "NEUTRAL",
                    "overbought": False,
                    "oversold": False,
                    "value": 0.0,
                }

            overbought = rsi >= settings.RSI_OVERBOUGHT
            oversold = rsi <= settings.RSI_OVERSOLD
            bullish_div = rsi > prev_rsi and rsi < 50
            bearish_div = rsi < prev_rsi and rsi > 50

            crossing_up = prev_rsi <= 50 < rsi
            crossing_down = prev_rsi >= 50 > rsi

            if oversold:
                signal = "BULLISH"
            elif overbought:
                signal = "BEARISH"
            elif rsi > 50:
                signal = "BULLISH"
            elif rsi < 50:
                signal = "BEARISH"
            else:
                signal = "NEUTRAL"

            return {
                "signal": signal,
                "overbought": overbought,
                "oversold": oversold,
                "bullish_divergence": bullish_div,
                "bearish_divergence": bearish_div,
                "crossing_up_50": crossing_up,
                "crossing_down_50": crossing_down,
                "value": float(rsi),
                "prev_value": float(prev_rsi) if not pd.isna(prev_rsi) else 0.0,
            }
        except Exception as e:
            logger.error(f"Error getting RSI signal: {e}")
            return {"signal": "NEUTRAL", "overbought": False, "oversold": False, "value": 0.0}

    @staticmethod
    def get_stoch_rsi_signal(df: pd.DataFrame) -> Dict[str, Any]:
        try:
            last = df.iloc[-1]
            prev = df.iloc[-2]

            k = last.get("stoch_rsi_k", np.nan)
            d = last.get("stoch_rsi_d", np.nan)
            prev_k = prev.get("stoch_rsi_k", np.nan)
            prev_d = prev.get("stoch_rsi_d", np.nan)

            if pd.isna(k) or pd.isna(d):
                return {"signal": "NEUTRAL", "overbought": False, "oversold": False}

            overbought = k >= 80 and d >= 80
            oversold = k <= 20 and d <= 20

            bullish_cross = prev_k <= prev_d and k > d
            bearish_cross = prev_k >= prev_d and k < d

            bullish_cross_oversold = bullish_cross and k <= 20
            bearish_cross_overbought = bearish_cross and k >= 80

            if oversold or bullish_cross_oversold:
                signal = "BULLISH"
            elif overbought or bearish_cross_overbought:
                signal = "BEARISH"
            elif k > d:
                signal = "BULLISH"
            else:
                signal = "BEARISH"

            return {
                "signal": signal,
                "overbought": overbought,
                "oversold": oversold,
                "bullish_cross": bullish_cross,
                "bearish_cross": bearish_cross,
                "bullish_cross_oversold": bullish_cross_oversold,
                "bearish_cross_overbought": bearish_cross_overbought,
                "k": float(k),
                "d": float(d),
            }
        except Exception as e:
            logger.error(f"Error getting Stochastic RSI signal: {e}")
            return {"signal": "NEUTRAL", "overbought": False, "oversold": False}

    @staticmethod
    def get_cci_signal(df: pd.DataFrame) -> Dict[str, Any]:
        try:
            last = df.iloc[-1]
            prev = df.iloc[-2]

            cci = last.get("cci", np.nan)
            prev_cci = prev.get("cci", np.nan)

            if pd.isna(cci):
                return {"signal": "NEUTRAL", "overbought": False, "oversold": False, "value": 0.0}

            overbought = cci >= 100
            oversold = cci <= -100
            extreme_overbought = cci >= 200
            extreme_oversold = cci <= -200

            crossing_up_zero = prev_cci <= 0 < cci
            crossing_down_zero = prev_cci >= 0 > cci
            crossing_up_100 = prev_cci <= 100 < cci
            crossing_down_100 = prev_cci >= -100 > cci

            if oversold or crossing_up_zero:
                signal = "BULLISH"
            elif overbought or crossing_down_zero:
                signal = "BEARISH"
            elif cci > 0:
                signal = "BULLISH"
            else:
                signal = "BEARISH"

            return {
                "signal": signal,
                "overbought": overbought,
                "oversold": oversold,
                "extreme_overbought": extreme_overbought,
                "extreme_oversold": extreme_oversold,
                "crossing_up_zero": crossing_up_zero,
                "crossing_down_zero": crossing_down_zero,
                "crossing_up_100": crossing_up_100,
                "crossing_down_minus100": crossing_down_100,
                "value": float(cci),
            }
        except Exception as e:
            logger.error(f"Error getting CCI signal: {e}")
            return {"signal": "NEUTRAL", "overbought": False, "oversold": False, "value": 0.0}

    @staticmethod
    def detect_rsi_divergence(
        df: pd.DataFrame,
        lookback: int = 20,
    ) -> Dict[str, bool]:
        try:
            close = df["close"].iloc[-lookback:]
            rsi = df["rsi"].iloc[-lookback:]

            if rsi.isna().any():
                return {"bullish_divergence": False, "bearish_divergence": False}

            price_higher_high = close.iloc[-1] > close.iloc[:-1].max()
            rsi_lower_high = rsi.iloc[-1] < rsi.iloc[:-1].max()
            bearish_div = price_higher_high and rsi_lower_high

            price_lower_low = close.iloc[-1] < close.iloc[:-1].min()
            rsi_higher_low = rsi.iloc[-1] > rsi.iloc[:-1].min()
            bullish_div = price_lower_low and rsi_higher_low

            return {
                "bullish_divergence": bullish_div,
                "bearish_divergence": bearish_div,
            }
        except Exception as e:
            logger.error(f"Error detecting RSI divergence: {e}")
            return {"bullish_divergence": False, "bearish_divergence": False}

    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        try:
            df = MomentumIndicators.calculate_rsi(df)
            df = MomentumIndicators.calculate_stochastic_rsi(df)
            df = MomentumIndicators.calculate_cci(df)
            return df
        except Exception as e:
            logger.error(f"Error calculating all momentum indicators: {e}")
            return df

    @staticmethod
    def get_all_signals(df: pd.DataFrame) -> Dict[str, Any]:
        try:
            rsi_signal = MomentumIndicators.get_rsi_signal(df)
            stoch_signal = MomentumIndicators.get_stoch_rsi_signal(df)
            cci_signal = MomentumIndicators.get_cci_signal(df)
            divergence = MomentumIndicators.detect_rsi_divergence(df)

            bullish_count = sum([
                rsi_signal.get("signal") == "BULLISH",
                stoch_signal.get("signal") == "BULLISH",
                cci_signal.get("signal") == "BULLISH",
            ])
            bearish_count = sum([
                rsi_signal.get("signal") == "BEARISH",
                stoch_signal.get("signal") == "BEARISH",
                cci_signal.get("signal") == "BEARISH",
            ])

            overall = (
                "BULLISH" if bullish_count > bearish_count
                else "BEARISH" if bearish_count > bullish_count
                else "NEUTRAL"
            )

            return {
                "rsi": rsi_signal,
                "stoch_rsi": stoch_signal,
                "cci": cci_signal,
                "divergence": divergence,
                "overall": overall,
                "bullish_count": bullish_count,
                "bearish_count": bearish_count,
            }
        except Exception as e:
            logger.error(f"Error getting all momentum signals: {e}")
            return {"overall": "NEUTRAL"}


__all__ = ["MomentumIndicators"]

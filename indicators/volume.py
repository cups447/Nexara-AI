import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from config.settings import settings
from utils.logger import logger


class VolumeIndicators:

    @staticmethod
    def obv(df: pd.DataFrame) -> pd.Series:
        try:
            close = df["close"]
            volume = df["volume"]
            direction = np.sign(close.diff()).fillna(0)
            obv_vals = (direction * volume).cumsum()
            return obv_vals
        except Exception as e:
            logger.error(f"Error calculating OBV: {e}")
            return pd.Series(dtype=float)

    @staticmethod
    def calculate_obv(df: pd.DataFrame) -> pd.DataFrame:
        try:
            df["obv"] = VolumeIndicators.obv(df)
            df["obv_ema"] = df["obv"].ewm(
                span=settings.OBV_EMA_PERIOD, adjust=False
            ).mean()
            return df
        except Exception as e:
            logger.error(f"Error calculating OBV dataframe: {e}")
            return df

    @staticmethod
    def mfi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        try:
            typical_price = (df["high"] + df["low"] + df["close"]) / 3
            raw_money_flow = typical_price * df["volume"]

            positive_flow = pd.Series(0.0, index=df.index)
            negative_flow = pd.Series(0.0, index=df.index)

            tp_diff = typical_price.diff()
            positive_flow = raw_money_flow.where(tp_diff > 0, 0.0)
            negative_flow = raw_money_flow.where(tp_diff < 0, 0.0)

            pos_sum = positive_flow.rolling(window=period).sum()
            neg_sum = negative_flow.rolling(window=period).sum()

            money_ratio = pos_sum / neg_sum.replace(0, np.nan)
            mfi_val = 100 - (100 / (1 + money_ratio))
            return mfi_val
        except Exception as e:
            logger.error(f"Error calculating MFI: {e}")
            return pd.Series(dtype=float)

    @staticmethod
    def calculate_mfi(df: pd.DataFrame) -> pd.DataFrame:
        try:
            df["mfi"] = VolumeIndicators.mfi(df, settings.MFI_PERIOD)
            return df
        except Exception as e:
            logger.error(f"Error calculating MFI dataframe: {e}")
            return df

    @staticmethod
    def vwap(df: pd.DataFrame) -> pd.Series:
        try:
            typical_price = (df["high"] + df["low"] + df["close"]) / 3
            tp_vol = typical_price * df["volume"]
            cumulative_tp_vol = tp_vol.cumsum()
            cumulative_vol = df["volume"].cumsum()
            vwap_val = cumulative_tp_vol / cumulative_vol.replace(0, np.nan)
            return vwap_val
        except Exception as e:
            logger.error(f"Error calculating VWAP: {e}")
            return pd.Series(dtype=float)

    @staticmethod
    def calculate_vwap(df: pd.DataFrame) -> pd.DataFrame:
        try:
            df["vwap"] = VolumeIndicators.vwap(df)
            df["vwap_upper"] = df["vwap"] * 1.01
            df["vwap_lower"] = df["vwap"] * 0.99
            return df
        except Exception as e:
            logger.error(f"Error calculating VWAP dataframe: {e}")
            return df

    @staticmethod
    def volume_profile(
        df: pd.DataFrame,
        bins: int = 20,
    ) -> Dict[str, Any]:
        try:
            price_min = df["low"].min()
            price_max = df["high"].max()
            price_range = price_max - price_min

            if price_range == 0:
                return {"poc": df["close"].iloc[-1], "vah": df["close"].iloc[-1], "val": df["close"].iloc[-1], "levels": []}

            bin_size = price_range / bins
            levels = []

            for i in range(bins):
                bin_low = price_min + i * bin_size
                bin_high = bin_low + bin_size
                bin_mid = (bin_low + bin_high) / 2

                mask = (df["close"] >= bin_low) & (df["close"] < bin_high)
                bin_volume = df.loc[mask, "volume"].sum()
                levels.append({
                    "price": float(bin_mid),
                    "low": float(bin_low),
                    "high": float(bin_high),
                    "volume": float(bin_volume),
                })

            levels.sort(key=lambda x: x["volume"], reverse=True)
            poc = levels[0]["price"] if levels else df["close"].iloc[-1]

            total_volume = sum(l["volume"] for l in levels)
            target_volume = total_volume * 0.70

            levels_by_price = sorted(levels, key=lambda x: x["price"])
            poc_idx = next(
                (i for i, l in enumerate(levels_by_price) if l["price"] >= poc), 0
            )

            vah = poc
            val = poc
            accumulated = levels_by_price[poc_idx]["volume"] if levels_by_price else 0

            up_idx = poc_idx + 1
            down_idx = poc_idx - 1

            while accumulated < target_volume:
                up_vol = levels_by_price[up_idx]["volume"] if up_idx < len(levels_by_price) else 0
                down_vol = levels_by_price[down_idx]["volume"] if down_idx >= 0 else 0

                if up_vol >= down_vol and up_idx < len(levels_by_price):
                    accumulated += up_vol
                    vah = levels_by_price[up_idx]["price"]
                    up_idx += 1
                elif down_idx >= 0:
                    accumulated += down_vol
                    val = levels_by_price[down_idx]["price"]
                    down_idx -= 1
                else:
                    break

            return {
                "poc": float(poc),
                "vah": float(vah),
                "val": float(val),
                "levels": levels[:10],
                "total_volume": float(total_volume),
            }
        except Exception as e:
            logger.error(f"Error calculating Volume Profile: {e}")
            return {
                "poc": float(df["close"].iloc[-1]),
                "vah": float(df["close"].iloc[-1]),
                "val": float(df["close"].iloc[-1]),
                "levels": [],
            }

    @staticmethod
    def calculate_volume_profile(df: pd.DataFrame) -> pd.DataFrame:
        try:
            vp = VolumeIndicators.volume_profile(df)
            df["vp_poc"] = vp["poc"]
            df["vp_vah"] = vp["vah"]
            df["vp_val"] = vp["val"]
            return df
        except Exception as e:
            logger.error(f"Error calculating Volume Profile dataframe: {e}")
            return df

    @staticmethod
    def volume_sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
        try:
            return df["volume"].rolling(window=period).mean()
        except Exception as e:
            logger.error(f"Error calculating Volume SMA: {e}")
            return pd.Series(dtype=float)

    @staticmethod
    def get_obv_signal(df: pd.DataFrame) -> Dict[str, Any]:
        try:
            last = df.iloc[-1]
            prev = df.iloc[-2]

            obv = last.get("obv", np.nan)
            obv_ema = last.get("obv_ema", np.nan)
            prev_obv = prev.get("obv", np.nan)
            prev_obv_ema = prev.get("obv_ema", np.nan)

            if pd.isna(obv) or pd.isna(obv_ema):
                return {"signal": "NEUTRAL", "trending": False}

            above_ema = obv > obv_ema
            bullish_cross = prev_obv <= prev_obv_ema and obv > obv_ema
            bearish_cross = prev_obv >= prev_obv_ema and obv < obv_ema
            rising = obv > prev_obv

            signal = "BULLISH" if above_ema else "BEARISH"

            return {
                "signal": signal,
                "above_ema": above_ema,
                "bullish_cross": bullish_cross,
                "bearish_cross": bearish_cross,
                "rising": rising,
                "value": float(obv),
                "ema": float(obv_ema),
            }
        except Exception as e:
            logger.error(f"Error getting OBV signal: {e}")
            return {"signal": "NEUTRAL", "trending": False}

    @staticmethod
    def get_mfi_signal(df: pd.DataFrame) -> Dict[str, Any]:
        try:
            last = df.iloc[-1]
            prev = df.iloc[-2]

            mfi = last.get("mfi", np.nan)
            prev_mfi = prev.get("mfi", np.nan)

            if pd.isna(mfi):
                return {"signal": "NEUTRAL", "overbought": False, "oversold": False, "value": 0.0}

            overbought = mfi >= 80
            oversold = mfi <= 20
            rising = mfi > prev_mfi

            crossing_up_50 = prev_mfi <= 50 < mfi
            crossing_down_50 = prev_mfi >= 50 > mfi

            if oversold:
                signal = "BULLISH"
            elif overbought:
                signal = "BEARISH"
            elif mfi > 50:
                signal = "BULLISH"
            else:
                signal = "BEARISH"

            return {
                "signal": signal,
                "overbought": overbought,
                "oversold": oversold,
                "rising": rising,
                "crossing_up_50": crossing_up_50,
                "crossing_down_50": crossing_down_50,
                "value": float(mfi),
            }
        except Exception as e:
            logger.error(f"Error getting MFI signal: {e}")
            return {"signal": "NEUTRAL", "overbought": False, "oversold": False, "value": 0.0}

    @staticmethod
    def get_vwap_signal(df: pd.DataFrame) -> Dict[str, Any]:
        try:
            last = df.iloc[-1]
            close = last["close"]
            vwap = last.get("vwap", np.nan)
            vwap_upper = last.get("vwap_upper", np.nan)
            vwap_lower = last.get("vwap_lower", np.nan)

            if pd.isna(vwap):
                re

import math
from collections.abc import Mapping

import numpy as np
import pandas as pd

from app.analytics.performance import annualized_volatility, sharpe_ratio


REGIME_NAMES = (
    "bull_low_vol",
    "bull_high_vol",
    "bear_low_vol",
    "bear_high_vol",
)


def rolling_market_trend(returns: pd.Series, window: int = 63) -> pd.Series:
    """Trailing cumulative return using only observations through each date."""
    return (1.0 + returns).rolling(window=window, min_periods=window).apply(np.prod, raw=True) - 1.0


def rolling_realized_volatility(
    returns: pd.Series, window: int = 21, annualization_factor: int = 252
) -> pd.Series:
    """Trailing sample volatility annualized by the configured trading-day factor."""
    return returns.rolling(window=window, min_periods=window).std(ddof=1) * math.sqrt(annualization_factor)


def classify_regimes(
    trend: pd.Series, realized_volatility: pd.Series, volatility_threshold: float = 0.20
) -> pd.Series:
    aligned = pd.concat(
        [trend.rename("trend"), realized_volatility.rename("volatility")], axis=1
    )
    regimes = pd.Series(pd.NA, index=aligned.index, dtype="object", name="regime")
    eligible = aligned.notna().all(axis=1)
    bull = aligned["trend"] >= 0
    high_vol = aligned["volatility"] >= volatility_threshold
    regimes.loc[eligible & bull & ~high_vol] = "bull_low_vol"
    regimes.loc[eligible & bull & high_vol] = "bull_high_vol"
    regimes.loc[eligible & ~bull & ~high_vol] = "bear_low_vol"
    regimes.loc[eligible & ~bull & high_vol] = "bear_high_vol"
    return regimes


def contiguous_regime_periods(regimes: pd.Series) -> list[dict]:
    periods = []
    current = None
    start = None
    end = None
    observations = 0
    for index, regime in regimes.sort_index().items():
        if pd.isna(regime):
            if current is not None:
                periods.append({"regime":current, "start_date":start, "end_date":end, "observations":observations})
            current = start = end = None
            observations = 0
            continue
        if regime != current:
            if current is not None:
                periods.append({"regime":current, "start_date":start, "end_date":end, "observations":observations})
            current, start, observations = regime, index, 1
        else:
            observations += 1
        end = index
    if current is not None:
        periods.append({"regime":current, "start_date":start, "end_date":end, "observations":observations})
    return periods


def portfolio_performance_by_regime(
    portfolio_returns: pd.Series,
    regimes: pd.Series,
    risk_free_rate: float = 0.0,
    annualization_factor: int = 252,
) -> Mapping[str, dict]:
    aligned = pd.concat(
        [portfolio_returns.rename("portfolio"), regimes.rename("regime")], axis=1, join="inner"
    ).dropna()
    total = len(aligned)
    results = {}
    for regime in REGIME_NAMES:
        returns = aligned.loc[aligned["regime"] == regime, "portfolio"]
        observations = len(returns)
        results[regime] = {
            "regime": regime,
            "observations": observations,
            "percentage_of_classified_history": observations / total if total else 0.0,
            "average_daily_return": float(returns.mean()) if observations else None,
            "annualized_return": float(returns.mean() * annualization_factor) if observations else None,
            "annualized_volatility": annualized_volatility(returns, annualization_factor),
            "sharpe_ratio": sharpe_ratio(returns, risk_free_rate, annualization_factor),
            "positive_day_percentage": float((returns > 0).mean()) if observations else None,
            "compounded_conditional_return": float((1.0 + returns).prod() - 1.0) if observations else None,
        }
    return results

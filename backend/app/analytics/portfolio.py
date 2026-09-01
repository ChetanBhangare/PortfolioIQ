import math

import pandas as pd

from app.analytics import AnalyticsError


def align_returns(series_by_ticker: dict[str, pd.Series]) -> pd.DataFrame:
    if not series_by_ticker:
        raise AnalyticsError("At least one return series is required")
    aligned = pd.concat(series_by_ticker, axis=1, join="inner").dropna(how="any")
    aligned.columns = [str(column).upper() for column in aligned.columns]
    if aligned.empty:
        raise AnalyticsError("No common trading dates exist across the requested assets")
    return aligned.sort_index()


def portfolio_returns(asset_returns: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    normalized = {ticker.upper(): weight for ticker, weight in weights.items()}
    missing = sorted(set(normalized) - set(asset_returns.columns))
    if missing:
        raise AnalyticsError(f"Missing return series for: {', '.join(missing)}")
    if not math.isclose(sum(normalized.values()), 1.0, abs_tol=1e-6):
        raise AnalyticsError("Portfolio weights must sum to 1.0")
    weighted = asset_returns[list(normalized)].mul(pd.Series(normalized), axis="columns")
    return weighted.sum(axis=1).rename("portfolio")

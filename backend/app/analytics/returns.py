import pandas as pd

from app.analytics import AnalyticsError


def simple_returns(prices: pd.Series) -> pd.Series:
    """Close-to-close simple returns: P[t] / P[t-1] - 1."""
    clean = prices.dropna().sort_index()
    if len(clean) < 2:
        raise AnalyticsError("At least two prices are required to calculate returns")
    if clean.index.has_duplicates:
        raise AnalyticsError("Price dates must be unique")
    if (clean <= 0).any():
        raise AnalyticsError("Prices must be positive")
    return clean.pct_change(fill_method=None).dropna().rename(prices.name)


def wealth_index(returns: pd.Series, initial_value: float = 1.0) -> pd.Series:
    return (1.0 + returns).cumprod() * initial_value


def cumulative_return(returns: pd.Series) -> float:
    if returns.empty:
        raise AnalyticsError("At least one return is required")
    return float((1.0 + returns).prod() - 1.0)


def monthly_returns(returns: pd.Series) -> pd.Series:
    if not isinstance(returns.index, pd.DatetimeIndex):
        raise AnalyticsError("Returns must use a DatetimeIndex")
    return (1.0 + returns).resample("ME").prod() - 1.0


def annual_returns(returns: pd.Series) -> pd.Series:
    if not isinstance(returns.index, pd.DatetimeIndex):
        raise AnalyticsError("Returns must use a DatetimeIndex")
    return (1.0 + returns).resample("YE").prod() - 1.0

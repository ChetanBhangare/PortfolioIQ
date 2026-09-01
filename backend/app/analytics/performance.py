import math

import numpy as np
import pandas as pd

from app.analytics import AnalyticsError
from app.analytics.returns import annual_returns, cumulative_return, monthly_returns


def _finite_or_none(value):
    return float(value) if value is not None and math.isfinite(value) else None


def cagr(returns: pd.Series, annualization_factor: int = 252):
    if returns.empty:
        raise AnalyticsError("At least one return is required")
    ending = float((1.0 + returns).prod())
    if ending <= 0:
        return None
    return _finite_or_none(ending ** (annualization_factor / len(returns)) - 1.0)


def annualized_volatility(returns: pd.Series, annualization_factor: int = 252):
    if len(returns) < 2:
        return None
    return _finite_or_none(returns.std(ddof=1) * np.sqrt(annualization_factor))


def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0, annualization_factor: int = 252):
    if len(returns) < 2:
        return None
    excess = returns - risk_free_rate / annualization_factor
    volatility = excess.std(ddof=1)
    if np.isclose(volatility, 0.0):
        return None
    return _finite_or_none(excess.mean() / volatility * np.sqrt(annualization_factor))


def sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.0, annualization_factor: int = 252):
    if returns.empty:
        return None
    excess = returns - risk_free_rate / annualization_factor
    downside = np.minimum(excess.to_numpy(dtype=float), 0.0)
    downside_deviation = float(np.sqrt(np.mean(np.square(downside))))
    if np.isclose(downside_deviation, 0.0):
        return None
    return _finite_or_none(excess.mean() / downside_deviation * np.sqrt(annualization_factor))


def calmar_ratio(returns: pd.Series, maximum_drawdown: float, annualization_factor: int = 252):
    growth = cagr(returns, annualization_factor)
    if growth is None or np.isclose(maximum_drawdown, 0.0):
        return None
    return _finite_or_none(growth / abs(maximum_drawdown))


def period_extreme(returns: pd.Series, best: bool):
    if returns.empty:
        return {"date": None, "value": None}
    index = returns.idxmax() if best else returns.idxmin()
    return {"date": index.date().isoformat(), "value": float(returns.loc[index])}


def best_worst_periods(returns: pd.Series):
    months = monthly_returns(returns)
    years = annual_returns(returns)
    return {
        "best_day": period_extreme(returns, True),
        "worst_day": period_extreme(returns, False),
        "best_month": period_extreme(months, True),
        "worst_month": period_extreme(months, False),
        "best_year": period_extreme(years, True),
        "worst_year": period_extreme(years, False),
    }


def performance_metrics(returns: pd.Series, risk_free_rate: float, annualization_factor: int, maximum_drawdown: float):
    return {
        "total_return": cumulative_return(returns),
        "cagr": cagr(returns, annualization_factor),
        "annualized_volatility": annualized_volatility(returns, annualization_factor),
        "sharpe_ratio": sharpe_ratio(returns, risk_free_rate, annualization_factor),
        "sortino_ratio": sortino_ratio(returns, risk_free_rate, annualization_factor),
        "calmar_ratio": calmar_ratio(returns, maximum_drawdown, annualization_factor),
    }

import math

import numpy as np
import pandas as pd


def _finite_or_none(value):
    return float(value) if value is not None and math.isfinite(value) else None


def benchmark_metrics(portfolio: pd.Series, benchmark: pd.Series, risk_free_rate: float = 0.0, annualization_factor: int = 252):
    aligned = pd.concat({"portfolio": portfolio, "benchmark": benchmark}, axis=1, join="inner").dropna()
    if len(aligned) < 2:
        return {key: None for key in (
            "active_return", "beta", "alpha", "r_squared", "tracking_error",
            "information_ratio", "upside_capture", "downside_capture"
        )}
    p = aligned["portfolio"]
    b = aligned["benchmark"]
    benchmark_variance = b.var(ddof=1)
    beta = None if np.isclose(benchmark_variance, 0.0) else p.cov(b) / benchmark_variance
    rf_daily = risk_free_rate / annualization_factor
    alpha = None if beta is None else ((p.mean() - rf_daily) - beta * (b.mean() - rf_daily)) * annualization_factor
    correlation = None if np.isclose(p.std(ddof=1), 0.0) or np.isclose(b.std(ddof=1), 0.0) else p.corr(b)
    active = (p - b).mean() * annualization_factor
    tracking_error = (p - b).std(ddof=1) * np.sqrt(annualization_factor)
    information_ratio = None if np.isclose(tracking_error, 0.0) else active / tracking_error

    def capture(mask):
        if not mask.any():
            return None
        benchmark_period = float((1.0 + b[mask]).prod() - 1.0)
        if np.isclose(benchmark_period, 0.0):
            return None
        portfolio_period = float((1.0 + p[mask]).prod() - 1.0)
        return portfolio_period / benchmark_period

    return {
        "active_return": _finite_or_none(active),
        "beta": _finite_or_none(beta),
        "alpha": _finite_or_none(alpha),
        "r_squared": _finite_or_none(correlation ** 2 if correlation is not None else None),
        "tracking_error": _finite_or_none(tracking_error),
        "information_ratio": _finite_or_none(information_ratio),
        "upside_capture": _finite_or_none(capture(b > 0)),
        "downside_capture": _finite_or_none(capture(b < 0)),
    }

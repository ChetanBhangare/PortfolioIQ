from statistics import NormalDist

import numpy as np
import pandas as pd

from app.analytics import AnalyticsError

SUPPORTED_CONFIDENCE_LEVELS = (0.95, 0.99)


def _validate_frame(returns: pd.DataFrame, minimum_observations: int = 2):
    if len(returns) < minimum_observations:
        raise AnalyticsError(f"At least {minimum_observations} aligned observations are required")
    if returns.empty or returns.shape[1] == 0:
        raise AnalyticsError("At least one asset return series is required")
    if returns.isna().any().any():
        raise AnalyticsError("Aligned returns must not contain missing observations")


def _validate_confidence(confidence: float):
    if confidence not in SUPPORTED_CONFIDENCE_LEVELS:
        raise AnalyticsError("Confidence level must be 0.95 or 0.99")


def covariance_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    _validate_frame(returns)
    return returns.cov(ddof=1)


def annualized_covariance_matrix(returns: pd.DataFrame, annualization_factor: int = 252) -> pd.DataFrame:
    if annualization_factor <= 0:
        raise AnalyticsError("Annualization factor must be positive")
    return covariance_matrix(returns) * annualization_factor


def correlation_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    _validate_frame(returns)
    return returns.corr()


def portfolio_variance(covariance: pd.DataFrame, weights: dict[str, float]) -> float:
    tickers = list(weights)
    if set(tickers) - set(covariance.index) or set(tickers) - set(covariance.columns):
        raise AnalyticsError("Covariance matrix does not contain every portfolio ticker")
    matrix = covariance.loc[tickers, tickers].to_numpy(dtype=float)
    vector = np.array([weights[ticker] for ticker in tickers], dtype=float)
    variance = float(vector @ matrix @ vector)
    if variance < -1e-12:
        raise AnalyticsError("Portfolio variance is materially negative")
    return max(0.0, variance)


def portfolio_volatility(covariance: pd.DataFrame, weights: dict[str, float]) -> float:
    return float(np.sqrt(portfolio_variance(covariance, weights)))


def historical_var(returns: pd.Series, confidence: float) -> float:
    _validate_confidence(confidence)
    if len(returns) < 2:
        raise AnalyticsError("At least two returns are required for historical VaR")
    return max(0.0, float(-returns.quantile(1.0 - confidence)))


def parametric_var(expected_return: float, volatility: float, confidence: float) -> float:
    _validate_confidence(confidence)
    if volatility < 0:
        raise AnalyticsError("Volatility cannot be negative")
    z_score = NormalDist().inv_cdf(confidence)
    return max(0.0, float(z_score * volatility - expected_return))


def historical_cvar(returns: pd.Series, confidence: float):
    _validate_confidence(confidence)
    if len(returns) < 2:
        raise AnalyticsError("At least two returns are required for historical CVaR")
    cutoff = float(returns.quantile(1.0 - confidence))
    tail = returns[returns <= cutoff]
    if tail.empty:
        return None
    return max(0.0, float(-tail.mean()))


def concentration_metrics(weights: dict[str, float]):
    values = sorted(weights.values(), reverse=True)
    hhi = float(sum(weight ** 2 for weight in values))
    return {
        "largest_position_weight": float(values[0]),
        "top_3_concentration": float(sum(values[:3])),
        "top_5_concentration": float(sum(values[:5])),
        "hhi": hhi,
        "effective_number_of_holdings": float(1.0 / hhi),
    }


def matrix_to_dict(matrix: pd.DataFrame):
    return {
        str(row): {
            str(column): float(matrix.loc[row, column]) if np.isfinite(matrix.loc[row, column]) else None
            for column in matrix.columns
        }
        for row in matrix.index
    }

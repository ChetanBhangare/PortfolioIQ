import numpy as np
import pandas as pd

from app.analytics import AnalyticsError
from app.analytics.risk import portfolio_volatility
from app.analytics.returns import cumulative_return


def risk_contributions(annualized_covariance: pd.DataFrame, weights: dict[str, float]):
    tickers = list(weights)
    sigma = portfolio_volatility(annualized_covariance, weights)
    if np.isclose(sigma, 0.0):
        return [
            {
                "ticker": ticker,
                "weight": float(weights[ticker]),
                "marginal_risk_contribution": None,
                "component_risk_contribution": None,
                "percent_risk_contribution": None,
            }
            for ticker in tickers
        ]
    vector = np.array([weights[ticker] for ticker in tickers], dtype=float)
    matrix = annualized_covariance.loc[tickers, tickers].to_numpy(dtype=float)
    marginal = matrix @ vector / sigma
    component = vector * marginal
    return [
        {
            "ticker": ticker,
            "weight": float(vector[index]),
            "marginal_risk_contribution": float(marginal[index]),
            "component_risk_contribution": float(component[index]),
            "percent_risk_contribution": float(component[index] / sigma),
        }
        for index, ticker in enumerate(tickers)
    ]


def return_contributions(asset_returns: pd.DataFrame, weights: dict[str, float]):
    tickers = list(weights)
    if set(tickers) - set(asset_returns.columns):
        raise AnalyticsError("Return frame does not contain every portfolio ticker")
    daily_contributions = asset_returns[tickers].mul(pd.Series(weights), axis="columns")
    portfolio_returns = daily_contributions.sum(axis=1)
    future_growth = (1.0 + portfolio_returns).iloc[::-1].cumprod().iloc[::-1].shift(-1, fill_value=1.0)
    linked = daily_contributions.mul(future_growth, axis="index").sum(axis=0)
    rows = [
        {
            "ticker": ticker,
            "weight": float(weights[ticker]),
            "asset_period_return": cumulative_return(asset_returns[ticker]),
            "weighted_return_contribution": float(linked[ticker]),
        }
        for ticker in tickers
    ]
    return rows, float(linked.sum())

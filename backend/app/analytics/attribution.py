import pandas as pd

from app.analytics.contribution import return_contributions


def benchmark_relative_contributions(asset_returns: pd.DataFrame, weights: dict[str, float], benchmark_ticker: str):
    universe = list(dict.fromkeys(list(weights) + [benchmark_ticker]))
    portfolio_weights = {ticker: weights.get(ticker, 0.0) for ticker in universe}
    benchmark_weights = {ticker: 1.0 if ticker == benchmark_ticker else 0.0 for ticker in universe}
    portfolio_rows, portfolio_total = return_contributions(asset_returns[universe], portfolio_weights)
    benchmark_rows, benchmark_total = return_contributions(asset_returns[universe], benchmark_weights)
    portfolio_by_ticker = {row["ticker"]: row for row in portfolio_rows}
    benchmark_by_ticker = {row["ticker"]: row for row in benchmark_rows}
    rows = []
    for ticker in universe:
        portfolio_contribution = portfolio_by_ticker[ticker]["weighted_return_contribution"]
        benchmark_contribution = benchmark_by_ticker[ticker]["weighted_return_contribution"]
        rows.append({
            "ticker": ticker,
            "portfolio_weight": float(portfolio_weights[ticker]),
            "benchmark_equivalent_weight": float(benchmark_weights[ticker]),
            "active_weight": float(portfolio_weights[ticker] - benchmark_weights[ticker]),
            "asset_period_return": portfolio_by_ticker[ticker]["asset_period_return"],
            "portfolio_contribution": portfolio_contribution,
            "benchmark_contribution": benchmark_contribution,
            "active_contribution": float(portfolio_contribution - benchmark_contribution),
        })
    return rows, float(portfolio_total - benchmark_total)

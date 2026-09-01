from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from app.analytics import AnalyticsError
from app.analytics.benchmark import benchmark_metrics
from app.analytics.drawdown import maximum_drawdown_details
from app.analytics.performance import best_worst_periods, performance_metrics
from app.analytics.portfolio import align_returns, portfolio_returns
from app.analytics.returns import simple_returns
from app.analytics.schemas import PortfolioAnalyticsRequest, PortfolioAnalyticsResponse
from app.data.query import load_prices


@dataclass
class PreparedReturns:
    aligned: pd.DataFrame
    portfolio: pd.Series
    benchmark: pd.Series
    weights: dict[str, float]


class PortfolioAnalyticsService:
    def __init__(self, price_loader: Callable[[str], pd.DataFrame] = load_prices):
        self.price_loader = price_loader

    def _load_returns(self, ticker, start_date, end_date):
        frame = self.price_loader(ticker)
        if frame.empty:
            raise AnalyticsError(f"No stored price data is available for {ticker}")
        if not {"date", "close"}.issubset(frame.columns):
            raise AnalyticsError(f"Stored price data for {ticker} lacks date or close")
        prices = frame[["date", "close"]].copy()
        prices["date"] = pd.to_datetime(prices["date"])
        prices = prices.sort_values("date").set_index("date")["close"].rename(ticker)
        returns = simple_returns(prices)
        return returns.loc[
            (returns.index.date >= start_date) & (returns.index.date <= end_date)
        ]

    def prepare_returns(self, request: PortfolioAnalyticsRequest) -> PreparedReturns:
        tickers = list(dict.fromkeys(
            [holding.ticker for holding in request.holdings] + [request.benchmark_ticker]
        ))
        returns_by_ticker = {
            ticker: self._load_returns(ticker, request.start_date, request.end_date)
            for ticker in tickers
        }
        aligned = align_returns(returns_by_ticker)
        if len(aligned) < 2:
            raise AnalyticsError("At least two aligned return observations are required")

        weights = {holding.ticker: holding.weight for holding in request.holdings}
        portfolio = portfolio_returns(aligned, weights)
        benchmark = aligned[request.benchmark_ticker].rename("benchmark")
        return PreparedReturns(aligned, portfolio, benchmark, weights)

    def analyze(self, request: PortfolioAnalyticsRequest) -> PortfolioAnalyticsResponse:
        prepared = self.prepare_returns(request)
        aligned = prepared.aligned
        portfolio = prepared.portfolio
        benchmark = prepared.benchmark
        drawdown = maximum_drawdown_details(portfolio)
        response = {
            "portfolio_name": request.portfolio_name,
            "benchmark_ticker": request.benchmark_ticker,
            "holdings": request.holdings,
            "period": {
                "requested_start_date": request.start_date,
                "requested_end_date": request.end_date,
                "first_return_date": aligned.index.min().date(),
                "last_return_date": aligned.index.max().date(),
                "observations": len(aligned),
            },
            "risk_free_rate": request.risk_free_rate,
            "annualization_factor": request.annualization_factor,
            "performance": performance_metrics(
                portfolio,
                request.risk_free_rate,
                request.annualization_factor,
                drawdown["maximum_drawdown"],
            ),
            "benchmark": benchmark_metrics(
                portfolio,
                benchmark,
                request.risk_free_rate,
                request.annualization_factor,
            ),
            "drawdown": drawdown,
            "best_worst_periods": best_worst_periods(portfolio),
            "assumptions": [
                "Close-to-close simple returns use adjusted close prices.",
                "Static target weights are applied to every aligned daily return.",
                "Only dates shared by every holding and the benchmark are used; returns are never forward-filled.",
                "Annualized statistics use the configured trading-day factor and a linearly converted daily risk-free rate.",
            ],
        }
        return PortfolioAnalyticsResponse.model_validate(response)

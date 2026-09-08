from app.analytics import AnalyticsError
from app.analytics.regime import (
    classify_regimes,
    contiguous_regime_periods,
    portfolio_performance_by_regime,
    rolling_market_trend,
    rolling_realized_volatility,
)
from app.analytics.schemas import (
    PortfolioAnalyticsRequest,
    PortfolioRegimeRequest,
    PortfolioRegimeResponse,
)
from app.analytics.service import PortfolioAnalyticsService


class PortfolioRegimeService:
    def __init__(self, price_loader=None):
        self.analytics_service = PortfolioAnalyticsService(price_loader) if price_loader else PortfolioAnalyticsService()

    def analyze(self, request: PortfolioRegimeRequest) -> PortfolioRegimeResponse:
        preparation_request = PortfolioAnalyticsRequest.model_validate({
            **request.model_dump(),
            "benchmark_ticker": request.market_proxy,
        })
        prepared = self.analytics_service.prepare_returns(preparation_request)
        minimum = max(request.trend_window, request.volatility_window)
        if len(prepared.aligned) < minimum:
            raise AnalyticsError(
                f"At least {minimum} aligned return observations are required for regime classification"
            )

        proxy_returns = prepared.aligned[request.market_proxy]
        trend = rolling_market_trend(proxy_returns, request.trend_window)
        volatility = rolling_realized_volatility(
            proxy_returns, request.volatility_window, request.annualization_factor
        )
        regimes = classify_regimes(trend, volatility, request.volatility_threshold)
        classified = regimes.dropna()
        if classified.empty:
            raise AnalyticsError("No dates were eligible for regime classification")

        history = [
            {
                "date": index.date(),
                "regime": regime,
                "rolling_trend": float(trend.loc[index]),
                "realized_volatility": float(volatility.loc[index]),
            }
            for index, regime in classified.items()
        ]
        payload = {
            "analysis_start": classified.index.min().date(),
            "analysis_end": classified.index.max().date(),
            "market_proxy": request.market_proxy,
            "current_regime": classified.iloc[-1],
            "classified_observations": len(classified),
            "omitted_warmup_observations": len(regimes) - len(classified),
            "methodology": {
                "trend_window": request.trend_window,
                "volatility_window": request.volatility_window,
                "volatility_threshold": request.volatility_threshold,
                "annualization_factor": request.annualization_factor,
                "trend_definition": "Trailing compounded market-proxy return over the configured trading-day window.",
                "volatility_definition": "Trailing sample standard deviation of daily market-proxy returns, annualized by the square root of the annualization factor.",
            },
            "regime_history": history,
            "regime_periods": contiguous_regime_periods(regimes),
            "regime_performance": list(portfolio_performance_by_regime(
                prepared.portfolio,
                regimes,
                request.risk_free_rate,
                request.annualization_factor,
            ).values()),
            "assumptions": [
                "Regimes are historical classifications and are not forecasts or investment advice.",
                "Bull and bear states use a zero threshold for trailing compounded market-proxy return.",
                "High volatility begins at the configured annualized realized-volatility threshold.",
                "Dates without both rolling measures are omitted and regime labels are never forward-filled.",
                "Compounded conditional return compounds non-contiguous daily returns assigned to the same regime.",
            ],
        }
        return PortfolioRegimeResponse.model_validate(payload)

from app.analytics.attribution import benchmark_relative_contributions
from app.analytics.contribution import return_contributions, risk_contributions
from app.analytics.risk import (
    annualized_covariance_matrix,
    concentration_metrics,
    correlation_matrix,
    historical_cvar,
    historical_var,
    matrix_to_dict,
    parametric_var,
    portfolio_variance,
    portfolio_volatility,
)
from app.analytics.schemas import PortfolioRiskRequest, PortfolioRiskResponse
from app.analytics.service import PortfolioAnalyticsService
from app.analytics.stress import HISTORICAL_STRESS_SCENARIOS, custom_stress_scenario, stress_window


class PortfolioRiskService:
    def __init__(self, analytics_service=None):
        self.analytics_service = analytics_service or PortfolioAnalyticsService()

    def analyze(self, request: PortfolioRiskRequest) -> PortfolioRiskResponse:
        prepared = self.analytics_service.prepare_returns(request)
        asset_returns = prepared.aligned[list(prepared.weights)]
        annual_covariance = annualized_covariance_matrix(asset_returns, request.annualization_factor)
        correlation = correlation_matrix(asset_returns)
        variance = portfolio_variance(annual_covariance, prepared.weights)
        volatility = portfolio_volatility(annual_covariance, prepared.weights)
        risk_rows = risk_contributions(annual_covariance, prepared.weights)
        return_rows, total_contribution = return_contributions(asset_returns, prepared.weights)
        attribution_rows, total_active = benchmark_relative_contributions(
            prepared.aligned, prepared.weights, request.benchmark_ticker
        )

        confidence_keys = {confidence: f"{int(confidence * 100)}" for confidence in request.confidence_levels}
        stress_scenarios = list(HISTORICAL_STRESS_SCENARIOS)
        if request.custom_stress_window:
            stress_scenarios.append(custom_stress_scenario(
                request.custom_stress_window.start_date,
                request.custom_stress_window.end_date,
            ))
        stresses = [
            stress_window(
                prepared.portfolio,
                prepared.benchmark,
                scenario,
                request.start_date,
                request.end_date,
                request.annualization_factor,
            )
            for scenario in stress_scenarios
        ]
        payload = {
            "portfolio_name": request.portfolio_name,
            "benchmark_ticker": request.benchmark_ticker,
            "period": {
                "requested_start_date": request.start_date,
                "requested_end_date": request.end_date,
                "first_return_date": prepared.aligned.index.min().date(),
                "last_return_date": prepared.aligned.index.max().date(),
                "observations": len(prepared.aligned),
            },
            "annualization_factor": request.annualization_factor,
            "confidence_levels": request.confidence_levels,
            "risk": {
                "portfolio_variance": variance,
                "portfolio_volatility": volatility,
                "historical_var": {confidence_keys[c]: historical_var(prepared.portfolio, c) for c in request.confidence_levels},
                "parametric_var": {confidence_keys[c]: parametric_var(prepared.portfolio.mean(), prepared.portfolio.std(ddof=1), c) for c in request.confidence_levels},
                "historical_cvar": {confidence_keys[c]: historical_cvar(prepared.portfolio, c) for c in request.confidence_levels},
            },
            "concentration": concentration_metrics(prepared.weights),
            "covariance": matrix_to_dict(annual_covariance),
            "correlation": matrix_to_dict(correlation),
            "risk_contribution": risk_rows,
            "return_contribution": return_rows,
            "portfolio_total_contribution": total_contribution,
            "attribution": attribution_rows,
            "total_active_contribution": total_active,
            "stress_tests": stresses,
            "assumptions": [
                "VaR and CVaR are positive one-day loss magnitudes.",
                "Parametric VaR assumes normally distributed daily returns.",
                "Risk contribution uses the annualized sample covariance matrix.",
                "Return contribution uses exact geometric linking of daily static-weight contributions.",
                "Attribution is benchmark-relative contribution analysis, not Brinson attribution.",
            ],
        }
        return PortfolioRiskResponse.model_validate(payload)

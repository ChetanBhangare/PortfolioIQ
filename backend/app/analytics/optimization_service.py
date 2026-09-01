import numpy as np

from app.analytics.constraints import OptimizationError, turnover, validate_weight_constraints
from app.analytics.optimization import (
    efficient_frontier,
    equal_weight_portfolio,
    expected_annual_returns,
    feasible_return_range,
    maximum_sharpe_portfolio,
    minimum_variance_portfolio,
    risk_parity_portfolio,
    strategy_metrics,
)
from app.analytics.risk import annualized_covariance_matrix
from app.analytics.scenarios import ILLUSTRATIVE_HYPOTHETICAL_SCENARIOS, hypothetical_shock
from app.analytics.schemas import PortfolioOptimizationRequest, PortfolioOptimizationResponse
from app.analytics.service import PortfolioAnalyticsService


class PortfolioOptimizationService:
    def __init__(self, analytics_service=None):
        self.analytics_service=analytics_service or PortfolioAnalyticsService()

    def analyze(self, request: PortfolioOptimizationRequest) -> PortfolioOptimizationResponse:
        prepared=self.analytics_service.prepare_returns(request)
        tickers=list(prepared.weights); asset_returns=prepared.aligned[tickers]
        expected=expected_annual_returns(asset_returns,request.annualization_factor)
        covariance=annualized_covariance_matrix(asset_returns,request.annualization_factor)
        current_vector=np.array([prepared.weights[ticker] for ticker in tickers])
        validate_weight_constraints(len(tickers),request.minimum_asset_weight,request.maximum_asset_weight,request.long_only,current_vector,request.turnover_constraint)
        low,high=feasible_return_range(expected,covariance,current_vector,request.minimum_asset_weight,request.maximum_asset_weight,request.turnover_constraint)
        if request.target_return is not None and not low-1e-8<=request.target_return<=high+1e-8:
            raise OptimizationError(f"target_return is outside the feasible range [{low:.6f}, {high:.6f}]")

        current=strategy_metrics("current",prepared.weights,expected,covariance,request.risk_free_rate,current_vector)
        results={}; requested=set(request.requested_strategies)
        if "equal_weight" in requested:
            equal=equal_weight_portfolio(expected,covariance,request.risk_free_rate,current_vector)
            if request.turnover_constraint is not None and equal["turnover"]>request.turnover_constraint+1e-8:
                raise OptimizationError("Equal-weight portfolio violates turnover_constraint")
            results["equal_weight"]=equal
        if "minimum_variance" in requested:
            results["minimum_variance"]=minimum_variance_portfolio(expected,covariance,request.risk_free_rate,current_vector,request.minimum_asset_weight,request.maximum_asset_weight,request.turnover_constraint,request.target_return)
        if "maximum_sharpe" in requested:
            results["maximum_sharpe"]=maximum_sharpe_portfolio(expected,covariance,request.risk_free_rate,current_vector,request.minimum_asset_weight,request.maximum_asset_weight,request.turnover_constraint)
        if "risk_parity" in requested:
            results["risk_parity"]=risk_parity_portfolio(expected,covariance,request.risk_free_rate,current_vector,request.minimum_asset_weight,request.maximum_asset_weight,request.turnover_constraint)

        frontier=[]; skipped=[]
        if "efficient_frontier" in requested:
            anchors=[result["expected_annual_return"] for result in results.values()]
            frontier,skipped,_=efficient_frontier(expected,covariance,request.risk_free_rate,current_vector,request.minimum_asset_weight,request.maximum_asset_weight,request.turnover_constraint,request.frontier_point_count,anchors)

        comparison=[current]+[results[name] for name in ("equal_weight","minimum_variance","maximum_sharpe","risk_parity") if name in results]
        shocks=[]
        for name in request.hypothetical_scenarios:
            if name not in ILLUSTRATIVE_HYPOTHETICAL_SCENARIOS:
                raise OptimizationError(f"Unknown hypothetical scenario: {name}")
            scenario_shocks={ticker:shock for ticker,shock in ILLUSTRATIVE_HYPOTHETICAL_SCENARIOS[name].items() if ticker in prepared.weights}
            shocks.append(hypothetical_shock(prepared.weights,scenario_shocks,name))
        if request.custom_asset_shocks is not None:
            shocks.append(hypothetical_shock(prepared.weights,request.custom_asset_shocks))
        min_frontier=min(frontier,key=lambda point:point["annualized_volatility"]) if frontier else None
        sharpe_frontier=[point for point in frontier if point["sharpe_ratio"] is not None]
        max_frontier=max(sharpe_frontier,key=lambda point:point["sharpe_ratio"]) if sharpe_frontier else None
        recommended=results[request.objective]
        payload={
            "portfolio_name":request.portfolio_name,
            "period":{"requested_start_date":request.start_date,"requested_end_date":request.end_date,"first_return_date":prepared.aligned.index.min().date(),"last_return_date":prepared.aligned.index.max().date(),"observations":len(prepared.aligned)},
            "expected_returns":{ticker:float(value) for ticker,value in expected.items()},
            "current":current,
            "equal_weight":results.get("equal_weight"),"minimum_variance":results.get("minimum_variance"),"maximum_sharpe":results.get("maximum_sharpe"),"risk_parity":results.get("risk_parity"),
            "efficient_frontier":frontier,"frontier_skipped":skipped,"frontier_minimum_volatility":min_frontier,"frontier_maximum_sharpe":max_frontier,
            "recommended_strategy":recommended,"comparison":comparison,"hypothetical_stress":shocks,
            "solver_diagnostics":{name:result["solver"] for name,result in results.items()},
            "assumptions":["Expected returns are arithmetic daily means annualized by the configured factor.","Covariance is the annualized sample covariance of aligned daily returns.","Optimization is long-only, fully invested, and unlevered.","Turnover is one-way turnover: 0.5 × sum(abs(new weight - current weight)).","Hypothetical scenarios are illustrative asset shocks, not historical estimates or factor models."],
        }
        return PortfolioOptimizationResponse.model_validate(payload)

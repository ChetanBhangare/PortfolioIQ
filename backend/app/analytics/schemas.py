import math
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.settings import DEFAULT_ASSET_UNIVERSE


class Holding(BaseModel):
    ticker: str
    weight: float = Field(ge=0.0, le=1.0)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value):
        ticker = value.strip().upper()
        if ticker not in DEFAULT_ASSET_UNIVERSE:
            raise ValueError(f"Ticker {ticker} is not in the configured universe")
        return ticker


class PortfolioAnalyticsRequest(BaseModel):
    portfolio_name: str = Field(min_length=1, max_length=100)
    benchmark_ticker: str
    holdings: list[Holding] = Field(min_length=1)
    start_date: date
    end_date: date
    risk_free_rate: float = 0.0
    annualization_factor: int = Field(default=252, gt=0)

    @field_validator("benchmark_ticker")
    @classmethod
    def normalize_benchmark(cls, value):
        ticker = value.strip().upper()
        if ticker not in DEFAULT_ASSET_UNIVERSE:
            raise ValueError(f"Benchmark {ticker} is not in the configured universe")
        return ticker

    @model_validator(mode="after")
    def validate_contract(self):
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        tickers = [holding.ticker for holding in self.holdings]
        if len(tickers) != len(set(tickers)):
            raise ValueError("Duplicate holding tickers are not allowed")
        if not math.isclose(sum(holding.weight for holding in self.holdings), 1.0, abs_tol=1e-6):
            raise ValueError("Holding weights must sum to 1.0")
        return self


class AnalysisPeriod(BaseModel):
    requested_start_date: date
    requested_end_date: date
    first_return_date: date
    last_return_date: date
    observations: int


class PerformanceMetrics(BaseModel):
    total_return: float
    cagr: float | None
    annualized_volatility: float | None
    sharpe_ratio: float | None
    sortino_ratio: float | None
    calmar_ratio: float | None


class DrawdownMetrics(BaseModel):
    maximum_drawdown: float
    start_date: date
    trough_date: date
    recovery_date: date | None
    drawdown_duration_days: int
    recovery_duration_days: int | None


class BenchmarkMetrics(BaseModel):
    active_return: float | None
    beta: float | None
    alpha: float | None
    r_squared: float | None
    tracking_error: float | None
    information_ratio: float | None
    upside_capture: float | None
    downside_capture: float | None


class PeriodExtreme(BaseModel):
    date: date | None
    value: float | None


class GrowthPoint(BaseModel):
    date: date
    portfolio: float
    benchmark: float


class DrawdownPoint(BaseModel):
    date: date
    value: float


class PeriodReturnPoint(BaseModel):
    date: date
    value: float


class PortfolioAnalyticsResponse(BaseModel):
    model_config = ConfigDict(ser_json_inf_nan="null")

    portfolio_name: str
    benchmark_ticker: str
    holdings: list[Holding]
    period: AnalysisPeriod
    risk_free_rate: float
    annualization_factor: int
    performance: PerformanceMetrics
    benchmark: BenchmarkMetrics
    drawdown: DrawdownMetrics
    best_worst_periods: dict[str, PeriodExtreme]
    cumulative_growth: list[GrowthPoint] = Field(default_factory=list)
    drawdown_series: list[DrawdownPoint] = Field(default_factory=list)
    monthly_returns: list[PeriodReturnPoint] = Field(default_factory=list)
    annual_returns: list[PeriodReturnPoint] = Field(default_factory=list)
    assumptions: list[str]


class CustomStressWindow(BaseModel):
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date > self.end_date:
            raise ValueError("Custom stress start_date must be on or before end_date")
        return self


class PortfolioRiskRequest(PortfolioAnalyticsRequest):
    confidence_levels: list[float] = Field(default=[0.95, 0.99], min_length=1)
    custom_stress_window: CustomStressWindow | None = None

    @field_validator("confidence_levels")
    @classmethod
    def validate_confidence_levels(cls, values):
        if len(values) != len(set(values)):
            raise ValueError("Confidence levels must be unique")
        if any(value not in {0.95, 0.99} for value in values):
            raise ValueError("Confidence levels must be 0.95 or 0.99")
        return values


class RiskSummary(BaseModel):
    portfolio_variance: float
    portfolio_volatility: float
    historical_var: dict[str, float]
    parametric_var: dict[str, float]
    historical_cvar: dict[str, float | None]


class ConcentrationMetrics(BaseModel):
    largest_position_weight: float
    top_3_concentration: float
    top_5_concentration: float
    hhi: float
    effective_number_of_holdings: float


class RiskContribution(BaseModel):
    ticker: str
    weight: float
    marginal_risk_contribution: float | None
    component_risk_contribution: float | None
    percent_risk_contribution: float | None


class ReturnContribution(BaseModel):
    ticker: str
    weight: float
    asset_period_return: float
    weighted_return_contribution: float


class AttributionContribution(BaseModel):
    ticker: str
    portfolio_weight: float
    benchmark_equivalent_weight: float
    active_weight: float
    asset_period_return: float
    portfolio_contribution: float
    benchmark_contribution: float
    active_contribution: float


class StressResult(BaseModel):
    name: str
    start_date: date
    end_date: date
    available: bool
    reason: str | None = None
    observations: int | None = None
    portfolio_cumulative_return: float | None = None
    benchmark_cumulative_return: float | None = None
    active_return: float | None = None
    maximum_drawdown: float | None = None
    worst_day: PeriodExtreme | None = None
    annualized_volatility: float | None = None


class PortfolioRiskResponse(BaseModel):
    model_config = ConfigDict(ser_json_inf_nan="null")

    portfolio_name: str
    benchmark_ticker: str
    period: AnalysisPeriod
    annualization_factor: int
    confidence_levels: list[float]
    risk: RiskSummary
    concentration: ConcentrationMetrics
    covariance: dict[str, dict[str, float | None]]
    correlation: dict[str, dict[str, float | None]]
    risk_contribution: list[RiskContribution]
    return_contribution: list[ReturnContribution]
    portfolio_total_contribution: float
    attribution: list[AttributionContribution]
    total_active_contribution: float
    stress_tests: list[StressResult]
    assumptions: list[str]


OptimizationStrategyName = Literal["equal_weight", "minimum_variance", "maximum_sharpe", "risk_parity", "efficient_frontier"]


class PortfolioOptimizationRequest(PortfolioAnalyticsRequest):
    objective: Literal["minimum_variance", "maximum_sharpe", "risk_parity"] = "maximum_sharpe"
    minimum_asset_weight: float = Field(default=0.0, ge=0.0, le=1.0)
    maximum_asset_weight: float = Field(default=1.0, ge=0.0, le=1.0)
    target_return: float | None = None
    turnover_constraint: float | None = Field(default=None, ge=0.0, le=1.0)
    long_only: bool = True
    frontier_point_count: int = Field(default=30, ge=5, le=100)
    requested_strategies: list[OptimizationStrategyName] = Field(default=["equal_weight", "minimum_variance", "maximum_sharpe", "risk_parity", "efficient_frontier"], min_length=1)
    hypothetical_scenarios: list[str] = Field(default=[])
    custom_asset_shocks: dict[str, float] | None = None

    @field_validator("requested_strategies")
    @classmethod
    def unique_strategies(cls, values):
        if len(values) != len(set(values)):
            raise ValueError("requested_strategies must be unique")
        return values

    @field_validator("custom_asset_shocks")
    @classmethod
    def normalize_shock_tickers(cls, value):
        return None if value is None else {ticker.strip().upper(): shock for ticker, shock in value.items()}

    @model_validator(mode="after")
    def validate_optimization_contract(self):
        if self.minimum_asset_weight > self.maximum_asset_weight:
            raise ValueError("minimum_asset_weight cannot exceed maximum_asset_weight")
        if not self.long_only:
            raise ValueError("R2.3 supports long-only optimization only")
        if self.objective not in self.requested_strategies:
            raise ValueError("objective must be included in requested_strategies")
        return self


class SolverDiagnostics(BaseModel):
    success: bool
    status: int
    message: str
    iterations: int | None


class OptimizationRiskContribution(BaseModel):
    ticker: str
    weight: float
    marginal_risk_contribution: float | None
    component_risk_contribution: float | None
    percent_risk_contribution: float | None


class OptimizationStrategy(BaseModel):
    strategy: str
    weights: dict[str, float]
    expected_annual_return: float
    annualized_volatility: float
    sharpe_ratio: float | None
    largest_position_weight: float
    top_3_concentration: float
    top_5_concentration: float
    hhi: float
    effective_number_of_holdings: float
    turnover: float
    objective_value: float | None
    solver: SolverDiagnostics
    target_return: float | None = None
    risk_contribution: list[OptimizationRiskContribution] | None = None


class FrontierSkippedPoint(BaseModel):
    target_return: float
    reason: str


class HypotheticalShockAsset(BaseModel):
    ticker: str
    portfolio_weight: float
    assumed_shock: float
    shock_contribution: float


class HypotheticalShockResult(BaseModel):
    name: str
    type: Literal["illustrative_hypothetical_shock"]
    asset_shocks: list[HypotheticalShockAsset]
    total_portfolio_shock: float


class PortfolioOptimizationResponse(BaseModel):
    model_config = ConfigDict(ser_json_inf_nan="null")

    portfolio_name: str
    period: AnalysisPeriod
    expected_returns: dict[str, float]
    current: OptimizationStrategy
    equal_weight: OptimizationStrategy | None = None
    minimum_variance: OptimizationStrategy | None = None
    maximum_sharpe: OptimizationStrategy | None = None
    risk_parity: OptimizationStrategy | None = None
    efficient_frontier: list[OptimizationStrategy]
    frontier_skipped: list[FrontierSkippedPoint]
    frontier_minimum_volatility: OptimizationStrategy | None
    frontier_maximum_sharpe: OptimizationStrategy | None
    recommended_strategy: OptimizationStrategy
    comparison: list[OptimizationStrategy]
    hypothetical_stress: list[HypotheticalShockResult]
    solver_diagnostics: dict[str, SolverDiagnostics]
    assumptions: list[str]

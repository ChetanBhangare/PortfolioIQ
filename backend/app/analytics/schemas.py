import math
from datetime import date

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

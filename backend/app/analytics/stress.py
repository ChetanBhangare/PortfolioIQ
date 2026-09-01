from dataclasses import dataclass
from datetime import date

import pandas as pd

from app.analytics import AnalyticsError
from app.analytics.drawdown import maximum_drawdown_details
from app.analytics.performance import annualized_volatility, period_extreme
from app.analytics.returns import cumulative_return


@dataclass(frozen=True)
class StressScenario:
    name: str
    start_date: date
    end_date: date


HISTORICAL_STRESS_SCENARIOS = (
    StressScenario("COVID Crash", date(2020, 2, 19), date(2020, 3, 23)),
    StressScenario("2022 Rate Shock", date(2022, 1, 3), date(2022, 10, 14)),
    StressScenario("2023 Banking Stress", date(2023, 3, 8), date(2023, 3, 24)),
)


def stress_window(portfolio: pd.Series, benchmark: pd.Series, scenario: StressScenario, requested_start: date, requested_end: date, annualization_factor: int = 252):
    base = {"name": scenario.name, "start_date": scenario.start_date, "end_date": scenario.end_date}
    if requested_start > scenario.start_date or requested_end < scenario.end_date:
        return {**base, "available": False, "reason": "Scenario is outside the requested analysis period"}
    aligned = pd.concat({"portfolio": portfolio, "benchmark": benchmark}, axis=1, join="inner").dropna()
    window = aligned.loc[
        (aligned.index.date >= scenario.start_date) & (aligned.index.date <= scenario.end_date)
    ]
    if len(window) < 2:
        return {**base, "available": False, "reason": "Insufficient aligned observations in scenario window"}
    portfolio_return = cumulative_return(window["portfolio"])
    benchmark_return = cumulative_return(window["benchmark"])
    return {
        **base,
        "available": True,
        "reason": None,
        "observations": len(window),
        "portfolio_cumulative_return": portfolio_return,
        "benchmark_cumulative_return": benchmark_return,
        "active_return": float(portfolio_return - benchmark_return),
        "maximum_drawdown": maximum_drawdown_details(window["portfolio"])["maximum_drawdown"],
        "worst_day": period_extreme(window["portfolio"], False),
        "annualized_volatility": annualized_volatility(window["portfolio"], annualization_factor),
    }


def custom_stress_scenario(start_date: date, end_date: date):
    if start_date > end_date:
        raise AnalyticsError("Custom stress start_date must be on or before end_date")
    return StressScenario("Custom Stress Window", start_date, end_date)

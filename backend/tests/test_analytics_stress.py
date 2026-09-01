from datetime import date

import pandas as pd
import pytest

from app.analytics import AnalyticsError
from app.analytics.stress import StressScenario, custom_stress_scenario, stress_window


def test_historical_stress_metrics_use_observed_window_returns():
    index=pd.to_datetime(["2026-01-01","2026-01-02","2026-01-05"])
    portfolio=pd.Series([.10,-.20,.10],index=index)
    benchmark=pd.Series([.05,-.10,.05],index=index)
    scenario=StressScenario("Synthetic",date(2026,1,1),date(2026,1,5))
    result=stress_window(portfolio,benchmark,scenario,date(2025,12,1),date(2026,2,1))
    assert result["available"] is True
    assert result["portfolio_cumulative_return"]==pytest.approx(1.1*.8*1.1-1)
    assert result["benchmark_cumulative_return"]==pytest.approx(1.05*.9*1.05-1)
    assert result["maximum_drawdown"]==pytest.approx(-.20)
    assert result["worst_day"]=={"date":"2026-01-02","value":-.20}


def test_scenario_outside_request_is_unavailable():
    series=pd.Series([.01,.02],index=pd.to_datetime(["2026-01-01","2026-01-02"]))
    scenario=StressScenario("Earlier",date(2025,1,1),date(2025,1,31))
    result=stress_window(series,series,scenario,date(2026,1,1),date(2026,1,31))
    assert result["available"] is False
    assert "outside" in result["reason"]


def test_stress_window_with_insufficient_observations_is_unavailable():
    series=pd.Series([.01],index=pd.to_datetime(["2026-01-02"]))
    scenario=StressScenario("Sparse",date(2026,1,1),date(2026,1,5))
    result=stress_window(series,series,scenario,date(2026,1,1),date(2026,1,5))
    assert result["available"] is False
    assert "Insufficient" in result["reason"]


def test_custom_stress_window_validation():
    with pytest.raises(AnalyticsError,match="on or before"):
        custom_stress_scenario(date(2026,2,1),date(2026,1,1))

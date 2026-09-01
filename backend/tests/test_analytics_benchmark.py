import numpy as np
import pandas as pd
import pytest

from app.analytics.benchmark import benchmark_metrics


def test_benchmark_regression_and_active_metrics():
    benchmark=pd.Series([.01,-.01,.02,-.02],index=pd.date_range("2026-01-01",periods=4))
    portfolio=2*benchmark+.001
    result=benchmark_metrics(portfolio,benchmark,risk_free_rate=0,annualization_factor=252)
    active=(portfolio-benchmark).to_numpy()
    expected_active=np.mean(active)*252
    expected_te=np.std(active,ddof=1)*np.sqrt(252)
    assert result["beta"]==pytest.approx(2.0)
    assert result["alpha"]==pytest.approx(.001*252)
    assert result["r_squared"]==pytest.approx(1.0)
    assert result["active_return"]==pytest.approx(expected_active)
    assert result["tracking_error"]==pytest.approx(expected_te)
    assert result["information_ratio"]==pytest.approx(expected_active/expected_te)


def test_upside_and_downside_capture_use_compounded_conditional_returns():
    benchmark=pd.Series([.10,-.10,.20,-.20],index=pd.date_range("2026-01-01",periods=4))
    portfolio=pd.Series([.05,-.05,.10,-.10],index=benchmark.index)
    result=benchmark_metrics(portfolio,benchmark)
    expected_up=((1.05*1.10)-1)/((1.10*1.20)-1)
    expected_down=((.95*.90)-1)/((.90*.80)-1)
    assert result["upside_capture"]==pytest.approx(expected_up)
    assert result["downside_capture"]==pytest.approx(expected_down)


def test_insufficient_history_and_zero_benchmark_variance_are_clean():
    one=pd.Series([.01],index=pd.to_datetime(["2026-01-01"]))
    assert all(value is None for value in benchmark_metrics(one,one).values())
    flat=pd.Series([.01,.01,.01],index=pd.date_range("2026-01-01",periods=3))
    result=benchmark_metrics(flat,flat)
    assert result["beta"] is None
    assert result["alpha"] is None
    assert result["r_squared"] is None

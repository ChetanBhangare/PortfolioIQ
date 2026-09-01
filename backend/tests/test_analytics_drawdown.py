import pandas as pd
import pytest

from app.analytics.drawdown import drawdown_series, maximum_drawdown_details
from app.analytics.performance import best_worst_periods


def test_drawdown_series_and_dates():
    index=pd.to_datetime(["2026-01-01","2026-01-02","2026-01-05","2026-01-06"])
    returns=pd.Series([.10,-.20,-.10,.40],index=index)
    frame=drawdown_series(returns)
    assert frame.loc["2026-01-05","wealth_index"]==pytest.approx(.792)
    assert frame.loc["2026-01-05","running_peak"]==pytest.approx(1.10)
    assert frame.loc["2026-01-05","drawdown"]==pytest.approx(-.28)
    result=maximum_drawdown_details(returns)
    assert result=={
        "maximum_drawdown":pytest.approx(-.28),
        "start_date":"2026-01-01",
        "trough_date":"2026-01-05",
        "recovery_date":"2026-01-06",
        "drawdown_duration_days":4,
        "recovery_duration_days":1,
    }


def test_unrecovered_drawdown_has_null_recovery():
    returns=pd.Series([.10,-.20,-.10],index=pd.to_datetime(["2026-01-01","2026-01-02","2026-01-05"]))
    result=maximum_drawdown_details(returns)
    assert result["recovery_date"] is None
    assert result["recovery_duration_days"] is None


def test_best_and_worst_periods():
    returns=pd.Series([.05,-.10,.02],index=pd.to_datetime(["2025-01-02","2025-02-03","2026-01-02"]))
    result=best_worst_periods(returns)
    assert result["best_day"]=={"date":"2025-01-02","value":.05}
    assert result["worst_day"]=={"date":"2025-02-03","value":-.10}
    assert result["best_month"]["value"]==pytest.approx(.05)
    assert result["worst_year"]["value"]==pytest.approx(1.05*.9-1)

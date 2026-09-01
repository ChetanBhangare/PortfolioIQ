from fastapi.testclient import TestClient
from unittest.mock import Mock

from app.main import app
from app.analytics.schemas import PortfolioAnalyticsResponse
import app.api.analytics as analytics_api


def test_analytics_endpoint_enforces_request_contract_before_loading_data():
    client=TestClient(app)
    response=client.post("/api/analytics/portfolio",json={
        "portfolio_name":"Invalid",
        "benchmark_ticker":"SPY",
        "holdings":[{"ticker":"SPY","weight":.8}],
        "start_date":"2026-01-01",
        "end_date":"2026-01-31",
    })
    assert response.status_code==422
    assert "sum to 1.0" in response.text


def test_analytics_endpoint_returns_typed_json_without_loading_aws(monkeypatch):
    expected=PortfolioAnalyticsResponse.model_validate({
        "portfolio_name":"Synthetic","benchmark_ticker":"SPY",
        "holdings":[{"ticker":"SPY","weight":1.0}],
        "period":{"requested_start_date":"2026-01-01","requested_end_date":"2026-01-31","first_return_date":"2026-01-02","last_return_date":"2026-01-30","observations":20},
        "risk_free_rate":0.0,"annualization_factor":252,
        "performance":{"total_return":.02,"cagr":.28,"annualized_volatility":.1,"sharpe_ratio":2.0,"sortino_ratio":3.0,"calmar_ratio":1.4},
        "benchmark":{"active_return":0.0,"beta":1.0,"alpha":0.0,"r_squared":1.0,"tracking_error":0.0,"information_ratio":None,"upside_capture":1.0,"downside_capture":1.0},
        "drawdown":{"maximum_drawdown":-.02,"start_date":"2026-01-10","trough_date":"2026-01-12","recovery_date":"2026-01-15","drawdown_duration_days":2,"recovery_duration_days":3},
        "best_worst_periods":{"best_day":{"date":"2026-01-05","value":.01},"worst_day":{"date":"2026-01-12","value":-.01}},
        "assumptions":["synthetic"],
    })
    fake=Mock(); fake.analyze.return_value=expected
    monkeypatch.setattr(analytics_api,"service",fake)
    response=TestClient(app).post("/api/analytics/portfolio",json={
        "portfolio_name":"Synthetic","benchmark_ticker":"SPY",
        "holdings":[{"ticker":"SPY","weight":1.0}],
        "start_date":"2026-01-01","end_date":"2026-01-31",
    })
    assert response.status_code==200
    assert response.json()["performance"]["total_return"]==.02
    fake.analyze.assert_called_once()

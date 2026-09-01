import json
from collections import Counter
from unittest.mock import Mock

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import app.api.analytics as analytics_api
from app.analytics.constraints import OptimizationError
from app.analytics.optimization_service import PortfolioOptimizationService
from app.analytics.schemas import PortfolioOptimizationRequest
from app.analytics.service import PortfolioAnalyticsService
from app.main import app


def frame(ticker,values):
    return pd.DataFrame({"date":pd.date_range("2026-01-01",periods=len(values)),"ticker":ticker,"close":values})


def payload(**overrides):
    data={
        "portfolio_name":"Optimization synthetic","benchmark_ticker":"SPY",
        "holdings":[{"ticker":"SPY","weight":.5},{"ticker":"QQQ","weight":.3},{"ticker":"TLT","weight":.2}],
        "start_date":"2026-01-02","end_date":"2026-01-12","risk_free_rate":0,
        "minimum_asset_weight":.01,"maximum_asset_weight":.8,"frontier_point_count":8,
        "objective":"maximum_sharpe",
        "requested_strategies":["equal_weight","minimum_variance","maximum_sharpe","risk_parity","efficient_frontier"],
        "hypothetical_scenarios":["Equity Selloff"],
        "custom_asset_shocks":{"SPY":-.2,"QQQ":-.25,"TLT":.08},
    }
    data.update(overrides); return data


@pytest.fixture
def service_setup():
    frames={
        "SPY":frame("SPY",[100,101,100,103,102,105,104,107,108,106,109,111]),
        "QQQ":frame("QQQ",[200,204,202,207,206,210,208,213,215,212,217,220]),
        "TLT":frame("TLT",[100,100.5,101,100.8,101.2,101.5,101.8,102,101.9,102.2,102.5,102.7]),
    }
    calls=Counter()
    def loader(ticker): calls[ticker]+=1; return frames[ticker]
    service=PortfolioOptimizationService(PortfolioAnalyticsService(loader))
    return service,calls


def test_optimization_service_loads_once_reconciles_and_serializes(service_setup):
    service,calls=service_setup
    result=service.analyze(PortfolioOptimizationRequest.model_validate(payload()))
    assert calls==Counter({"SPY":1,"QQQ":1,"TLT":1})
    assert result.recommended_strategy.strategy=="maximum_sharpe"
    assert all(sum(strategy.weights.values())==pytest.approx(1,abs=1e-7) for strategy in result.comparison)
    # The low-volatility bond cannot reach one-third risk contribution under the
    # configured 80% cap, so the constrained optimum must bind at that cap.
    assert result.risk_parity.weights["TLT"]==pytest.approx(.8,abs=1e-6)
    assert result.risk_parity.solver.success
    assert len(result.efficient_frontier)>=6
    assert result.hypothetical_stress[0].type=="illustrative_hypothetical_shock"
    assert sum(row.shock_contribution for row in result.hypothetical_stress[-1].asset_shocks)==pytest.approx(result.hypothetical_stress[-1].total_portfolio_shock)
    encoded=result.model_dump_json(); json.loads(encoded)
    assert "NaN" not in encoded and "Infinity" not in encoded


def test_infeasible_target_return_is_clear(service_setup):
    service,_=service_setup
    request=PortfolioOptimizationRequest.model_validate(payload(target_return=99.0))
    with pytest.raises(OptimizationError,match="outside the feasible range"):
        service.analyze(request)


def test_optimization_api_success_and_validation_error(monkeypatch,service_setup):
    service,_=service_setup
    request=PortfolioOptimizationRequest.model_validate(payload())
    expected=service.analyze(request)
    fake=Mock(); fake.analyze.return_value=expected
    monkeypatch.setattr(analytics_api,"optimization_service",fake)
    client=TestClient(app)
    response=client.post("/api/analytics/portfolio/optimize",json=payload())
    assert response.status_code==200
    assert "efficient_frontier" in response.json()
    invalid=client.post("/api/analytics/portfolio/optimize",json=payload(minimum_asset_weight=.5,maximum_asset_weight=.1))
    assert invalid.status_code==422

import json
from collections import Counter
from unittest.mock import Mock

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import app.api.analytics as analytics_api
from app.analytics.risk_service import PortfolioRiskService
from app.analytics.schemas import PortfolioRiskRequest
from app.analytics.service import PortfolioAnalyticsService
from app.main import app


def frame(ticker,closes):
    return pd.DataFrame({"date":pd.date_range("2026-01-01",periods=len(closes)),"ticker":ticker,"close":closes})


def request_payload(**overrides):
    payload={
        "portfolio_name":"Risk synthetic","benchmark_ticker":"SPY",
        "holdings":[{"ticker":"SPY","weight":.6},{"ticker":"QQQ","weight":.4}],
        "start_date":"2026-01-02","end_date":"2026-01-08",
        "confidence_levels":[.95,.99],
        "custom_stress_window":{"start_date":"2026-01-02","end_date":"2026-01-05"},
    }
    payload.update(overrides); return payload


def test_risk_service_reuses_loaded_returns_and_serializes_json():
    frames={"SPY":frame("SPY",[100,101,99,103,102,105,104,106]),"QQQ":frame("QQQ",[200,203,201,205,207,204,208,210])}
    calls=Counter()
    def loader(ticker): calls[ticker]+=1; return frames[ticker]
    request=PortfolioRiskRequest.model_validate(request_payload())
    result=PortfolioRiskService(PortfolioAnalyticsService(loader)).analyze(request)
    assert calls==Counter({"SPY":1,"QQQ":1})
    assert result.risk.portfolio_volatility>=0
    assert sum(row.component_risk_contribution for row in result.risk_contribution)==pytest.approx(result.risk.portfolio_volatility)
    assert result.portfolio_total_contribution==pytest.approx(sum(row.weighted_return_contribution for row in result.return_contribution))
    encoded=result.model_dump_json(); json.loads(encoded)
    assert "NaN" not in encoded and "Infinity" not in encoded


def test_risk_api_success_and_validation_failure(monkeypatch):
    frames={"SPY":frame("SPY",[100,101,99,103,102,105,104,106]),"QQQ":frame("QQQ",[200,203,201,205,207,204,208,210])}
    request=PortfolioRiskRequest.model_validate(request_payload())
    expected=PortfolioRiskService(PortfolioAnalyticsService(lambda ticker:frames[ticker])).analyze(request)
    fake=Mock(); fake.analyze.return_value=expected
    monkeypatch.setattr(analytics_api,"risk_service",fake)
    client=TestClient(app)
    response=client.post("/api/analytics/portfolio/risk",json=request_payload())
    assert response.status_code==200
    assert "risk_contribution" in response.json()
    invalid=client.post("/api/analytics/portfolio/risk",json=request_payload(confidence_levels=[.90]))
    assert invalid.status_code==422

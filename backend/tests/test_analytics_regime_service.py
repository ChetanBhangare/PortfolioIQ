import json
from collections import Counter

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import app.api.analytics as analytics_api
from app.analytics import AnalyticsError
from app.analytics.regime_service import PortfolioRegimeService
from app.analytics.schemas import PortfolioRegimeRequest
from app.main import app


def frame(ticker, values):
    return pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=len(values), freq="B"),
        "ticker": ticker,
        "close": values,
    })


def payload(**overrides):
    data = {
        "portfolio_name":"Regime synthetic", "benchmark_ticker":"SPY",
        "holdings":[{"ticker":"SPY","weight":0.6},{"ticker":"QQQ","weight":0.4}],
        "start_date":"2025-01-02", "end_date":"2025-05-30",
        "risk_free_rate":0.0, "annualization_factor":252,
        "market_proxy":"SPY", "trend_window":5, "volatility_window":3,
        "volatility_threshold":0.20,
    }
    data.update(overrides)
    return data


@pytest.fixture
def service_setup():
    spy = [100.0]
    qqq = [200.0]
    for index in range(99):
        spy.append(spy[-1] * (1 + (0.012 if index % 5 else -0.009)))
        qqq.append(qqq[-1] * (1 + (0.015 if index % 4 else -0.011)))
    frames = {"SPY":frame("SPY", spy), "QQQ":frame("QQQ", qqq)}
    calls = Counter()
    def loader(ticker):
        calls[ticker] += 1
        return frames[ticker]
    return PortfolioRegimeService(loader), calls


def test_service_uses_injected_loader_once_and_is_deterministic(service_setup):
    service, calls = service_setup
    request = PortfolioRegimeRequest.model_validate(payload())
    first = service.analyze(request)
    assert calls == Counter({"SPY":1, "QQQ":1})
    calls.clear()
    second = service.analyze(request)
    assert calls == Counter({"SPY":1, "QQQ":1})
    assert first.model_dump() == second.model_dump()
    assert first.classified_observations == len(first.regime_history)
    assert first.regime_history[0].date >= first.analysis_start
    encoded = first.model_dump_json()
    json.loads(encoded)
    assert "NaN" not in encoded and "Infinity" not in encoded


def test_service_market_proxy_alignment_and_insufficient_history(service_setup):
    service, _ = service_setup
    result = service.analyze(PortfolioRegimeRequest.model_validate(payload()))
    assert result.omitted_warmup_observations == 4
    assert result.analysis_start == result.regime_history[0].date
    short = PortfolioRegimeRequest.model_validate(payload(trend_window=120))
    with pytest.raises(AnalyticsError, match="120 aligned"):
        service.analyze(short)


def test_regime_request_validation():
    with pytest.raises(ValidationError):
        PortfolioRegimeRequest.model_validate(payload(trend_window=1))
    with pytest.raises(ValidationError):
        PortfolioRegimeRequest.model_validate(payload(volatility_threshold=0))


def test_regime_api_success_validation_and_insufficient_history(monkeypatch, service_setup):
    service, _ = service_setup
    monkeypatch.setattr(analytics_api, "regime_service", service)
    client = TestClient(app)
    response = client.post("/api/analytics/portfolio/regime", json=payload())
    assert response.status_code == 200
    assert response.json()["market_proxy"] == "SPY"
    assert len(response.json()["regime_performance"]) == 4
    assert "NaN" not in response.text and "Infinity" not in response.text
    assert client.post("/api/analytics/portfolio/regime", json=payload(trend_window=1)).status_code == 422
    insufficient = client.post("/api/analytics/portfolio/regime", json=payload(trend_window=120))
    assert insufficient.status_code == 422
    assert "120 aligned" in insufficient.text

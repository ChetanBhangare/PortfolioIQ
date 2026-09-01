import json
from collections import Counter
from datetime import date

import pandas as pd
import pytest
from pydantic import ValidationError

from app.analytics import AnalyticsError
from app.analytics.schemas import PortfolioAnalyticsRequest
from app.analytics.service import PortfolioAnalyticsService


def request_payload(**overrides):
    payload={
        "portfolio_name":"Synthetic portfolio",
        "benchmark_ticker":"SPY",
        "holdings":[{"ticker":"spy","weight":.5},{"ticker":"QQQ","weight":.5}],
        "start_date":"2026-01-02",
        "end_date":"2026-01-08",
        "risk_free_rate":.02,
    }
    payload.update(overrides)
    return payload


def price_frame(ticker,dates,closes):
    return pd.DataFrame({"date":pd.to_datetime(dates),"ticker":ticker,"close":closes})


def test_portfolio_contract_normalizes_and_validates_weights():
    request=PortfolioAnalyticsRequest.model_validate(request_payload())
    assert request.holdings[0].ticker=="SPY"
    with pytest.raises(ValidationError,match="sum to 1.0"):
        PortfolioAnalyticsRequest.model_validate(request_payload(holdings=[{"ticker":"SPY","weight":.8}]))
    with pytest.raises(ValidationError,match="greater than or equal to 0"):
        PortfolioAnalyticsRequest.model_validate(request_payload(holdings=[{"ticker":"SPY","weight":1.1},{"ticker":"QQQ","weight":-.1}]))


def test_portfolio_contract_rejects_duplicate_holdings_and_invalid_universe():
    with pytest.raises(ValidationError,match="Duplicate"):
        PortfolioAnalyticsRequest.model_validate(request_payload(holdings=[{"ticker":"SPY","weight":.5},{"ticker":"spy","weight":.5}]))
    with pytest.raises(ValidationError,match="configured universe"):
        PortfolioAnalyticsRequest.model_validate(request_payload(benchmark_ticker="INVALID"))


def test_service_loads_unique_tickers_once_aligns_dates_and_serializes_json():
    frames={
        "SPY":price_frame("SPY",["2026-01-01","2026-01-02","2026-01-05","2026-01-06","2026-01-07"],[100,101,102,101,103]),
        "QQQ":price_frame("QQQ",["2026-01-01","2026-01-02","2026-01-06","2026-01-07"],[200,202,204,208]),
    }
    calls=Counter()
    def loader(ticker):
        calls[ticker]+=1
        return frames[ticker]
    request=PortfolioAnalyticsRequest.model_validate(request_payload())
    response=PortfolioAnalyticsService(loader).analyze(request)
    assert calls==Counter({"SPY":1,"QQQ":1})
    assert response.period.observations==3
    assert response.period.first_return_date==date(2026,1,2)
    encoded=response.model_dump_json()
    decoded=json.loads(encoded)
    assert decoded["portfolio_name"]=="Synthetic portfolio"
    assert decoded["performance"]["total_return"] is not None
    assert len(decoded["cumulative_growth"])==response.period.observations
    assert len(decoded["drawdown_series"])==response.period.observations
    assert decoded["cumulative_growth"][-1]["portfolio"]-1==pytest.approx(response.performance.total_return)
    assert min(point["value"] for point in decoded["drawdown_series"])==pytest.approx(response.drawdown.maximum_drawdown)
    assert decoded["monthly_returns"] and decoded["annual_returns"]
    assert "NaN" not in encoded and "Infinity" not in encoded


def test_service_handles_missing_data_and_insufficient_history():
    request=PortfolioAnalyticsRequest.model_validate(request_payload())
    with pytest.raises(AnalyticsError,match="No stored price data"):
        PortfolioAnalyticsService(lambda _:pd.DataFrame()).analyze(request)

    frames={
        "SPY":price_frame("SPY",["2026-01-01","2026-01-02"],[100,101]),
        "QQQ":price_frame("QQQ",["2026-01-01","2026-01-02"],[200,201]),
    }
    with pytest.raises(AnalyticsError,match="two aligned"):
        PortfolioAnalyticsService(lambda ticker:frames[ticker]).analyze(request)

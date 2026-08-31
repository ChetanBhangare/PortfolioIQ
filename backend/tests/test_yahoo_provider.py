from datetime import date
from unittest.mock import Mock

import pandas as pd

from app.data.providers.yahoo import YahooFinanceProvider


def test_yahoo_provider_retries_temporary_exception(monkeypatch):
    raw=pd.DataFrame(
        {"Open":[100.],"High":[102.],"Low":[99.],"Close":[101.],"Volume":[1000]},
        index=pd.to_datetime(["2026-01-02"]),
    )
    raw.index.name="Date"
    download=Mock(side_effect=[RuntimeError("temporary"),raw])
    sleep=Mock()
    monkeypatch.setattr("app.data.providers.yahoo.yf.download",download)
    monkeypatch.setattr("app.data.providers.yahoo.time.sleep",sleep)

    result=YahooFinanceProvider(max_attempts=3,backoff_seconds=.25).get_daily_prices(
        "SPY",date(2026,1,1),date(2026,1,2)
    )

    assert len(result)==1
    assert download.call_count==2
    sleep.assert_called_once_with(.25)


def test_yahoo_provider_stops_after_bounded_attempts(monkeypatch):
    download=Mock(side_effect=RuntimeError("temporary"))
    monkeypatch.setattr("app.data.providers.yahoo.yf.download",download)
    monkeypatch.setattr("app.data.providers.yahoo.time.sleep",Mock())

    try:
        YahooFinanceProvider(max_attempts=3,backoff_seconds=0).get_daily_prices(
            "SPY",date(2026,1,1),date(2026,1,2)
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("provider should propagate the final failure")
    assert download.call_count==3

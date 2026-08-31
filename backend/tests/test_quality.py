import pandas as pd
from app.data.quality import validate_prices
def test_valid():
    df=pd.DataFrame({"date":pd.to_datetime(["2026-01-02","2026-01-05"]),"ticker":["SPY","SPY"],"close":[101.0,102.0]})
    r=validate_prices(df,"SPY"); assert r.passed and r.rows==2
def test_duplicate_fails():
    df=pd.DataFrame({"date":pd.to_datetime(["2026-01-02","2026-01-02"]),"ticker":["SPY","SPY"],"close":[101.0,101.0]})
    assert validate_prices(df,"SPY").passed is False


def test_ohlc_and_negative_volume_are_hard_failures():
    df=pd.DataFrame({
        "date":pd.to_datetime(["2026-01-02"]),"ticker":["SPY"],
        "open":[100.],"high":[99.],"low":[98.],"close":[101.],"volume":[-1]
    })
    report=validate_prices(df,"SPY")
    assert report.passed is False
    assert "ohlc_inconsistency" in report.failures
    assert "negative_volume" in report.failures


def test_extreme_move_is_warning_not_failure():
    df=pd.DataFrame({"date":pd.to_datetime(["2026-08-28","2026-08-31"]),"ticker":["SPY","SPY"],"close":[100.,200.]})
    report=validate_prices(df,"SPY")
    assert report.passed is True
    assert report.status=="passed_with_warnings"
    assert "extreme_daily_move" in report.warnings


def test_ohlc_check_allows_floating_point_noise():
    df=pd.DataFrame({
        "date":pd.to_datetime(["2021-04-22"]),"ticker":["TLT"],
        "open":[117.02639252074782],"high":[117.35239410400389],
        "low":[116.3576677267992],"close":[117.3523941040039],"volume":[1]
    })
    assert validate_prices(df,"TLT").passed is True

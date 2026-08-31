import pandas as pd
from unittest.mock import Mock
from app.data.ingestion import ingest_ticker,merge_price_history
def test_merge():
    e=pd.DataFrame({"date":pd.to_datetime(["2026-01-02"]),"ticker":["SPY"],"close":[100.]})
    i=pd.DataFrame({"date":pd.to_datetime(["2026-01-02","2026-01-05"]),"ticker":["SPY","SPY"],"close":[101.,102.]})
    r=merge_price_history(e,i); assert len(r)==2 and float(r.iloc[0]["close"])==101.


def test_incremental_ingestion_skips_download_and_parquet_rewrite_when_current(monkeypatch,caplog):
    caplog.set_level("INFO",logger="portfolioiq.ingestion")
    existing=pd.DataFrame({"date":[pd.Timestamp.today().normalize()],"ticker":["SPY"],"close":[100.]})
    storage=Mock(); storage.read_parquet.return_value=existing
    provider=Mock()
    settings=Mock(default_start_date="2016-01-01",market_data_provider="yahoo",storage_mode="s3")
    monkeypatch.setattr("app.data.ingestion.get_settings",lambda:settings)
    monkeypatch.setattr("app.data.ingestion.get_storage",lambda _:storage)
    monkeypatch.setattr("app.data.ingestion.get_market_provider",lambda _:provider)

    result=ingest_ticker("SPY")

    provider.get_daily_prices.assert_not_called()
    storage.write_parquet.assert_not_called()
    assert storage.write_json.call_count==2
    assert result["passed"] is True
    assert "already_current=true" in caplog.text


def test_manifest_contains_auditable_dataset_metadata():
    from types import SimpleNamespace
    from app.data.ingestion import build_market_price_manifest
    from app.data.quality import validate_prices

    frame=pd.DataFrame({"date":pd.to_datetime(["2026-01-02"]),"ticker":["SPY"],"close":[101.]})
    report=validate_prices(frame,"SPY")
    settings=SimpleNamespace(market_data_provider="Yahoo")
    manifest=build_market_price_manifest("spy",settings,report,"raw/market_prices/SPY.parquet")
    assert manifest["ticker"]=="SPY"
    assert manifest["provider"]=="yahoo"
    assert manifest["row_count"]==1
    assert manifest["schema_version"]=="1.0"
    assert manifest["quality_status"]==report.status

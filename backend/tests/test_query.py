from types import SimpleNamespace
from unittest.mock import Mock

from app.data.query import dataset_status


def test_dataset_status_uses_manifest_without_reading_parquet(monkeypatch):
    storage=Mock()
    storage.read_json.return_value={
        "row_count":2679,"min_date":"2016-01-04","max_date":"2026-08-31",
        "schema_version":"1.0","quality_status":"passed",
        "last_refresh_timestamp":"2026-08-31T17:00:00+00:00",
    }
    monkeypatch.setattr("app.data.query.get_settings",lambda:SimpleNamespace())
    monkeypatch.setattr("app.data.query.get_storage",lambda _:storage)

    result=dataset_status("spy")

    assert result["available"] is True
    assert result["rows"]==2679
    storage.read_parquet.assert_not_called()

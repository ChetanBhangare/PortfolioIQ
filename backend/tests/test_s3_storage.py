import json
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd
import pytest
from botocore.exceptions import ClientError

from app.data.storage import S3Storage


def client_error(code, operation):
    return ClientError({"Error": {"Code": code, "Message": code}}, operation)


@pytest.fixture
def s3_storage():
    client = Mock()
    settings = SimpleNamespace(
        s3_bucket="portfolioiq-test", s3_prefix="/portfolioiq/", aws_region="us-east-1",
        aws_profile="portfolioiq",
    )
    session=Mock(); session.client.return_value=client
    with patch("app.data.storage.boto3.Session", return_value=session) as make_session:
        storage = S3Storage(settings)
    make_session.assert_called_once_with(profile_name="portfolioiq",region_name="us-east-1")
    session.client.assert_called_once_with("s3")
    return storage, client


def test_s3_key_construction(s3_storage):
    storage, _ = s3_storage
    assert storage._key("/raw/market_prices/SPY.parquet") == "portfolioiq/raw/market_prices/SPY.parquet"


def test_s3_write_and_read_parquet(s3_storage):
    storage, client = s3_storage
    expected = pd.DataFrame(
        {"date": pd.to_datetime(["2026-01-02"]), "ticker": ["SPY"], "close": [101.0]}
    )

    storage.write_parquet("raw/market_prices/SPY.parquet", expected)
    upload = client.put_object.call_args.kwargs
    assert upload["Bucket"] == "portfolioiq-test"
    assert upload["Key"] == "portfolioiq/raw/market_prices/SPY.parquet"
    assert upload["ContentType"] == "application/vnd.apache.parquet"

    client.get_object.return_value = {"Body": BytesIO(upload["Body"])}
    actual = storage.read_parquet("raw/market_prices/SPY.parquet")
    pd.testing.assert_frame_equal(actual, expected)


def test_s3_exists(s3_storage):
    storage, client = s3_storage
    assert storage.exists("raw/example.parquet") is True
    client.head_object.assert_called_once_with(
        Bucket="portfolioiq-test", Key="portfolioiq/raw/example.parquet"
    )


def test_s3_exists_returns_false_for_missing_key(s3_storage):
    storage, client = s3_storage
    client.head_object.side_effect = client_error("404", "HeadObject")
    assert storage.exists("raw/missing.parquet") is False


def test_s3_read_missing_key_returns_empty_frame(s3_storage):
    storage, client = s3_storage
    client.get_object.side_effect = client_error("NoSuchKey", "GetObject")
    assert storage.read_parquet("raw/missing.parquet").empty


def test_s3_permission_errors_are_not_hidden(s3_storage):
    storage, client = s3_storage
    client.head_object.side_effect = client_error("AccessDenied", "HeadObject")
    with pytest.raises(ClientError):
        storage.exists("raw/private.parquet")


def test_s3_write_json(s3_storage):
    storage, client = s3_storage
    storage.write_json("reports/data_quality/SPY.json", {"ticker": "SPY", "passed": True})
    upload = client.put_object.call_args.kwargs
    assert upload["Key"] == "portfolioiq/reports/data_quality/SPY.json"
    assert upload["ContentType"] == "application/json"
    assert json.loads(upload["Body"].decode()) == {"ticker": "SPY", "passed": True}


def test_s3_read_json_and_missing_json(s3_storage):
    storage, client = s3_storage
    client.get_object.return_value={"Body":BytesIO(b'{"schema_version":"1.0"}')}
    assert storage.read_json("metadata/market_prices/SPY.json")=={"schema_version":"1.0"}
    client.get_object.side_effect=client_error("NoSuchKey","GetObject")
    assert storage.read_json("metadata/market_prices/MISSING.json") is None

from app.core.settings import get_settings
from app.data.keys import market_price_key, market_price_metadata_key
from app.data.storage import get_storage


def load_prices(ticker):
    settings = get_settings()
    return get_storage(settings).read_parquet(market_price_key(ticker.upper()))


def dataset_status(ticker, storage=None):
    ticker = ticker.upper()
    if storage is None:
        storage = get_storage(get_settings())
    metadata = storage.read_json(market_price_metadata_key(ticker))
    if metadata is None:
        return {
            "ticker": ticker,
            "available": False,
            "rows": 0,
            "min_date": None,
            "max_date": None,
            "schema_version": None,
            "quality_status": None,
            "last_refresh_timestamp": None,
        }
    return {
        "ticker": ticker,
        "available": True,
        "rows": metadata["row_count"],
        "min_date": metadata["min_date"],
        "max_date": metadata["max_date"],
        "schema_version": metadata["schema_version"],
        "quality_status": metadata["quality_status"],
        "last_refresh_timestamp": metadata["last_refresh_timestamp"],
    }

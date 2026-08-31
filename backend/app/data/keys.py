"""Logical data-lake keys, independent of local or S3 storage backends."""

def market_price_key(ticker):
    return f"raw/market_prices/{ticker.upper()}.parquet"


def market_price_quality_key(ticker):
    return f"reports/data_quality/{ticker.upper()}.json"


def market_price_metadata_key(ticker):
    return f"metadata/market_prices/{ticker.upper()}.json"

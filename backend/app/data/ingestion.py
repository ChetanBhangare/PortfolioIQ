import argparse
import logging
from datetime import date, datetime, timedelta, timezone
from time import perf_counter

import pandas as pd

from app.core.settings import DEFAULT_ASSET_UNIVERSE, get_settings
from app.data.keys import (
    market_price_key,
    market_price_metadata_key,
    market_price_quality_key,
)
from app.data.providers.factory import get_market_provider
from app.data.quality import validate_prices
from app.data.schema import MARKET_PRICE_SCHEMA_VERSION
from app.data.storage import get_storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("portfolioiq.ingestion")

# Backward-compatible names for callers that imported these helpers directly.
price_key = market_price_key
quality_key = market_price_quality_key


def latest_date(df):
    return None if df.empty else pd.to_datetime(df["date"]).max().date()


def merge_price_history(existing, incoming):
    if existing.empty:
        combined = incoming.copy()
    elif incoming.empty:
        combined = existing.copy()
    else:
        combined = pd.concat([existing, incoming], ignore_index=True)
    if combined.empty:
        return combined
    combined["date"] = pd.to_datetime(combined["date"])
    return (
        combined.drop_duplicates(["ticker", "date"], keep="last")
        .sort_values(["ticker", "date"])
        .reset_index(drop=True)
    )


def build_market_price_manifest(ticker, settings, report, storage_key):
    return {
        "ticker": ticker.upper(),
        "provider": settings.market_data_provider.lower(),
        "row_count": report.rows,
        "min_date": report.min_date,
        "max_date": report.max_date,
        "last_refresh_timestamp": datetime.now(timezone.utc).isoformat(),
        "schema_version": MARKET_PRICE_SCHEMA_VERSION,
        "quality_status": report.status,
        "storage_key": storage_key,
    }


def ingest_ticker(ticker, full_refresh=False, settings=None, storage=None, provider=None):
    started = perf_counter()
    ticker = ticker.upper()
    settings = settings or get_settings()
    storage = storage or get_storage(settings)
    provider = provider or get_market_provider(settings)
    key = market_price_key(ticker)
    existing = pd.DataFrame() if full_refresh else storage.read_parquet(key)
    configured = datetime.strptime(settings.default_start_date, "%Y-%m-%d").date()
    last = latest_date(existing)
    start = configured if full_refresh or not last else max(configured, last + timedelta(days=1))
    end = date.today()
    incoming = pd.DataFrame()

    log.info(
        "ticker=%s provider=%s storage=%s existing_rows=%s full_refresh=%s",
        ticker,
        settings.market_data_provider,
        settings.storage_mode,
        len(existing),
        full_refresh,
    )
    if start <= end:
        log.info("ticker=%s requested_range=%s..%s", ticker, start, end)
        incoming = provider.get_daily_prices(ticker, start, end)
        combined = merge_price_history(existing, incoming)
        if incoming.empty and last:
            log.info("ticker=%s no_new_rows=true stored_through=%s", ticker, last)
    else:
        log.info("ticker=%s already_current=true stored_through=%s", ticker, last)
        combined = existing

    report = validate_prices(combined, ticker)
    data_changed = full_refresh or not incoming.empty
    wrote_parquet = False
    if not combined.empty and data_changed and report.passed:
        storage.write_parquet(key, combined)
        wrote_parquet = True
    elif data_changed and not report.passed:
        log.error("ticker=%s parquet_write_blocked=true failures=%s", ticker, report.failures)

    storage.write_json(market_price_quality_key(ticker), report.to_dict())
    if report.passed and not combined.empty:
        storage.write_json(
            market_price_metadata_key(ticker),
            build_market_price_manifest(ticker, settings, report, key),
        )

    log.info(
        "ticker=%s incoming_rows=%s final_rows=%s parquet_written=%s quality=%s elapsed_seconds=%.3f",
        ticker,
        len(incoming),
        len(combined),
        wrote_parquet,
        report.status,
        perf_counter() - started,
    )
    return report.to_dict()


def run_ingestion(tickers, full_refresh=False):
    results = []
    settings = get_settings()
    storage = get_storage(settings)
    provider = get_market_provider(settings)
    for ticker in tickers:
        try:
            results.append(
                ingest_ticker(ticker, full_refresh, settings, storage, provider)
            )
        except Exception as error:
            log.exception("ticker=%s ingestion_failed=true", ticker)
            results.append({"ticker": ticker, "passed": False, "error": str(error)})
    return results


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="*", default=DEFAULT_ASSET_UNIVERSE)
    parser.add_argument("--full-refresh", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    results = run_ingestion(args.tickers, args.full_refresh)
    log.info(
        "ingestion_complete=true passed=%s total=%s",
        sum(1 for result in results if result.get("passed")),
        len(results),
    )

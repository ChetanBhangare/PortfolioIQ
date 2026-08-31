from dataclasses import asdict, dataclass, field
from datetime import date

import pandas as pd


@dataclass
class QualityReport:
    ticker: str
    rows: int
    min_date: str | None
    max_date: str | None
    duplicate_rows: int
    missing_close: int
    nonpositive_close: int
    non_monotonic_dates: int = 0
    ohlc_inconsistencies: int = 0
    negative_volume: int = 0
    extreme_daily_moves: int = 0
    suspicious_gaps: int = 0
    stale_days: int | None = None
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    passed: bool = False

    @property
    def status(self):
        if not self.passed:
            return "failed"
        return "passed_with_warnings" if self.warnings else "passed"

    def to_dict(self):
        result = asdict(self)
        result["status"] = self.status
        return result


def validate_prices(df, ticker):
    if df.empty:
        return QualityReport(
            ticker=ticker,
            rows=0,
            min_date=None,
            max_date=None,
            duplicate_rows=0,
            missing_close=0,
            nonpositive_close=0,
            failures=["empty_dataset"],
            passed=False,
        )

    dates = pd.to_datetime(df["date"])
    duplicate_rows = int(df.duplicated(["ticker", "date"]).sum())
    missing_close = int(df["close"].isna().sum())
    nonpositive_close = int((df["close"].dropna() <= 0).sum())
    non_monotonic_dates = int(not dates.is_monotonic_increasing)

    ohlc_inconsistencies = 0
    if {"open", "high", "low", "close"}.issubset(df.columns):
        complete = df[["open", "high", "low", "close"]].dropna()
        tolerance = 1e-8
        invalid = (
            (complete["high"] + tolerance < complete[["open", "close"]].max(axis=1))
            | (complete["low"] - tolerance > complete[["open", "close"]].min(axis=1))
            | (complete["high"] + tolerance < complete["low"])
        )
        ohlc_inconsistencies = int(invalid.sum())

    negative_volume = 0
    if "volume" in df.columns:
        negative_volume = int((df["volume"].dropna() < 0).sum())

    sorted_close = df.assign(_date=dates).sort_values("_date")["close"]
    extreme_daily_moves = int((sorted_close.pct_change().abs() > 0.50).sum())
    sorted_dates = dates.sort_values()
    suspicious_gaps = int((sorted_dates.diff().dt.days > 10).sum())
    max_date = dates.max().date()
    stale_days = max(0, (date.today() - max_date).days)

    failures = []
    for count, name in (
        (duplicate_rows, "duplicate_ticker_date"),
        (missing_close, "missing_close"),
        (nonpositive_close, "nonpositive_close"),
        (non_monotonic_dates, "non_monotonic_dates"),
        (negative_volume, "negative_volume"),
    ):
        if count:
            failures.append(name)

    if ohlc_inconsistencies > 5 or ohlc_inconsistencies / len(df) > 0.001:
        failures.append("excessive_ohlc_inconsistency")

    warnings = []
    if ohlc_inconsistencies:
        warnings.append("ohlc_inconsistency")
    if extreme_daily_moves:
        warnings.append("extreme_daily_move")
    if suspicious_gaps:
        warnings.append("suspicious_date_gap")
    if stale_days > 7:
        warnings.append("stale_dataset")

    return QualityReport(
        ticker=ticker,
        rows=len(df),
        min_date=str(dates.min().date()),
        max_date=str(max_date),
        duplicate_rows=duplicate_rows,
        missing_close=missing_close,
        nonpositive_close=nonpositive_close,
        non_monotonic_dates=non_monotonic_dates,
        ohlc_inconsistencies=ohlc_inconsistencies,
        negative_volume=negative_volume,
        extreme_daily_moves=extreme_daily_moves,
        suspicious_gaps=suspicious_gaps,
        stale_days=stale_days,
        failures=failures,
        warnings=warnings,
        passed=not failures,
    )

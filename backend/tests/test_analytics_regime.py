import json

import numpy as np
import pandas as pd
import pytest

from app.analytics.regime import (
    classify_regimes,
    contiguous_regime_periods,
    portfolio_performance_by_regime,
    rolling_market_trend,
    rolling_realized_volatility,
)


def series(values):
    return pd.Series(values, index=pd.date_range("2026-01-01", periods=len(values)), dtype=float)


@pytest.mark.parametrize(
    ("trend", "volatility", "expected"),
    [
        (0.01, 0.10, "bull_low_vol"),
        (0.01, 0.20, "bull_high_vol"),
        (-0.01, 0.10, "bear_low_vol"),
        (-0.01, 0.20, "bear_high_vol"),
        (0.0, 0.10, "bull_low_vol"),
    ],
)
def test_classification_boundaries(trend, volatility, expected):
    result = classify_regimes(series([trend]), series([volatility]), 0.20)
    assert result.iloc[0] == expected


def test_rolling_measures_leave_warmup_unclassified_and_do_not_forward_fill():
    returns = series([0.01, 0.02, np.nan, -0.01, 0.01, 0.02])
    trend = rolling_market_trend(returns, 2)
    volatility = rolling_realized_volatility(returns, 2)
    regimes = classify_regimes(trend, volatility)
    assert regimes.iloc[0] is pd.NA
    assert regimes.iloc[2] is pd.NA
    assert regimes.iloc[3] is pd.NA
    assert regimes.iloc[4] == "bear_high_vol"


def test_rolling_calculations_use_no_future_information():
    original = series([0.01, 0.02, -0.01, 0.03, 0.01])
    changed_future = original.copy()
    changed_future.iloc[-1] = -0.90
    original_trend = rolling_market_trend(original, 3)
    changed_trend = rolling_market_trend(changed_future, 3)
    original_volatility = rolling_realized_volatility(original, 3)
    changed_volatility = rolling_realized_volatility(changed_future, 3)
    pd.testing.assert_series_equal(original_trend.iloc[:-1], changed_trend.iloc[:-1])
    pd.testing.assert_series_equal(original_volatility.iloc[:-1], changed_volatility.iloc[:-1])


def test_contiguous_periods_split_repeated_regime_after_missing_row():
    regimes = pd.Series(
        ["bull_low_vol", "bull_low_vol", "bear_high_vol", pd.NA, "bull_low_vol"],
        index=pd.date_range("2026-01-01", periods=5),
        dtype="object",
    )
    periods = contiguous_regime_periods(regimes)
    assert [(row["regime"], row["observations"]) for row in periods] == [
        ("bull_low_vol", 2), ("bear_high_vol", 1), ("bull_low_vol", 1)
    ]
    assert periods[0]["start_date"] == pd.Timestamp("2026-01-01")
    assert periods[0]["end_date"] == pd.Timestamp("2026-01-02")


def test_regime_performance_statistics_are_correct_and_json_safe():
    returns = series([0.01, -0.02, 0.03, 0.04])
    regimes = pd.Series(
        ["bull_low_vol", "bull_low_vol", "bear_high_vol", "bear_high_vol"],
        index=returns.index,
    )
    rows = portfolio_performance_by_regime(returns, regimes, annualization_factor=252)
    bull = rows["bull_low_vol"]
    assert bull["observations"] == 2
    assert bull["percentage_of_classified_history"] == 0.5
    assert bull["positive_day_percentage"] == 0.5
    assert bull["annualized_volatility"] == pytest.approx(returns.iloc[:2].std(ddof=1) * np.sqrt(252))
    assert bull["compounded_conditional_return"] == pytest.approx(1.01 * 0.98 - 1)
    assert rows["bear_low_vol"]["annualized_return"] is None
    encoded = json.dumps(rows, allow_nan=False)
    assert "NaN" not in encoded and "Infinity" not in encoded

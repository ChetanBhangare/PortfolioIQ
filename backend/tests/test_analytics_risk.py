from statistics import NormalDist

import numpy as np
import pandas as pd
import pytest

from app.analytics import AnalyticsError
from app.analytics.performance import annualized_volatility
from app.analytics.portfolio import portfolio_returns
from app.analytics.risk import (
    annualized_covariance_matrix,
    concentration_metrics,
    correlation_matrix,
    covariance_matrix,
    historical_cvar,
    historical_var,
    parametric_var,
    portfolio_variance,
    portfolio_volatility,
)


@pytest.fixture
def asset_returns():
    return pd.DataFrame(
        {"A":[.01,-.02,.03,.00],"B":[.02,.01,-.01,.04]},
        index=pd.date_range("2026-01-01",periods=4),
    )


def test_covariance_correlation_and_annualization_preserve_labels(asset_returns):
    expected=np.cov(asset_returns.to_numpy(),rowvar=False,ddof=1)
    covariance=covariance_matrix(asset_returns)
    np.testing.assert_allclose(covariance.to_numpy(),expected)
    assert list(covariance.index)==["A","B"]
    np.testing.assert_allclose(annualized_covariance_matrix(asset_returns,252),expected*252)
    np.testing.assert_allclose(correlation_matrix(asset_returns),np.corrcoef(asset_returns.to_numpy(),rowvar=False))


def test_portfolio_variance_volatility_and_direct_series_identity(asset_returns):
    weights={"A":.6,"B":.4}
    covariance=annualized_covariance_matrix(asset_returns)
    vector=np.array([.6,.4])
    expected_variance=float(vector@covariance.to_numpy()@vector)
    expected_volatility=np.sqrt(expected_variance)
    assert portfolio_variance(covariance,weights)==pytest.approx(expected_variance)
    assert portfolio_volatility(covariance,weights)==pytest.approx(expected_volatility)
    direct=annualized_volatility(portfolio_returns(asset_returns,weights))
    assert expected_volatility==pytest.approx(direct)


def test_historical_parametric_var_and_cvar_are_positive_loss_magnitudes():
    returns=pd.Series([-.05,-.03,-.01,.01,.02,.03])
    for confidence in (.95,.99):
        cutoff=float(returns.quantile(1-confidence))
        assert historical_var(returns,confidence)==pytest.approx(max(0,-cutoff))
        assert historical_cvar(returns,confidence)==pytest.approx(max(0,-returns[returns<=cutoff].mean()))
        expected=max(0,NormalDist().inv_cdf(confidence)*.02-.001)
        assert parametric_var(.001,.02,confidence)==pytest.approx(expected)


def test_concentration_metrics():
    result=concentration_metrics({"A":.4,"B":.3,"C":.2,"D":.1})
    assert result["largest_position_weight"]==pytest.approx(.4)
    assert result["top_3_concentration"]==pytest.approx(.9)
    assert result["top_5_concentration"]==pytest.approx(1.0)
    assert result["hhi"]==pytest.approx(.4**2+.3**2+.2**2+.1**2)
    assert result["effective_number_of_holdings"]==pytest.approx(1/result["hhi"])


def test_invalid_confidence_missing_data_and_insufficient_observations(asset_returns):
    with pytest.raises(AnalyticsError,match="0.95 or 0.99"):
        historical_var(asset_returns["A"],.90)
    missing=asset_returns.copy(); missing.iloc[0,0]=np.nan
    with pytest.raises(AnalyticsError,match="missing"):
        covariance_matrix(missing)
    with pytest.raises(AnalyticsError,match="At least 2"):
        covariance_matrix(asset_returns.iloc[:1])


def test_singular_covariance_and_zero_volatility_are_handled():
    returns=pd.DataFrame({"A":[.01,.01,.01],"B":[.01,.01,.01]})
    covariance=annualized_covariance_matrix(returns)
    assert portfolio_variance(covariance,{"A":.5,"B":.5})==pytest.approx(0.0)
    assert portfolio_volatility(covariance,{"A":.5,"B":.5})==pytest.approx(0.0)

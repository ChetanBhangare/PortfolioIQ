import numpy as np
import pandas as pd
import pytest

from app.analytics.performance import annualized_volatility, cagr, calmar_ratio, sharpe_ratio, sortino_ratio
from app.analytics.returns import cumulative_return


@pytest.fixture
def returns():
    return pd.Series([.01,-.02,.03,-.01],index=pd.date_range("2026-01-01",periods=4))


def test_total_return_and_cagr(returns):
    ending=1.01*.98*1.03*.99
    assert cumulative_return(returns)==pytest.approx(ending-1)
    assert cagr(returns,252)==pytest.approx(ending**(252/4)-1)


def test_volatility_sharpe_and_sortino_use_documented_conventions(returns):
    rf=.05; daily_rf=rf/252
    expected_vol=np.std(returns.to_numpy(),ddof=1)*np.sqrt(252)
    excess=returns.to_numpy()-daily_rf
    expected_sharpe=np.mean(excess)/np.std(excess,ddof=1)*np.sqrt(252)
    downside=np.minimum(excess,0)
    expected_sortino=np.mean(excess)/np.sqrt(np.mean(downside**2))*np.sqrt(252)
    assert annualized_volatility(returns)==pytest.approx(expected_vol)
    assert sharpe_ratio(returns,rf)==pytest.approx(expected_sharpe)
    assert sortino_ratio(returns,rf)==pytest.approx(expected_sortino)


def test_calmar_uses_cagr_over_absolute_maximum_drawdown(returns):
    assert calmar_ratio(returns,-.25)==pytest.approx(cagr(returns)/.25)


def test_zero_volatility_and_zero_downside_return_none():
    constant=pd.Series([.01,.01,.01],index=pd.date_range("2026-01-01",periods=3))
    assert sharpe_ratio(constant)==None
    assert sortino_ratio(constant)==None
    assert calmar_ratio(constant,0.0)==None

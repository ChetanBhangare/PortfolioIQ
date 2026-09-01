import numpy as np
import pandas as pd
import pytest

from app.analytics import AnalyticsError
from app.analytics.portfolio import align_returns, portfolio_returns
from app.analytics.returns import annual_returns, cumulative_return, monthly_returns, simple_returns, wealth_index


def test_daily_returns_wealth_and_cumulative_return():
    prices=pd.Series([100.,110.,99.],index=pd.to_datetime(["2026-01-01","2026-01-02","2026-01-05"]),name="SPY")
    returns=simple_returns(prices)
    np.testing.assert_allclose(returns.to_numpy(),[.10,-.10])
    np.testing.assert_allclose(wealth_index(returns).to_numpy(),[1.10,.99])
    assert cumulative_return(returns)==pytest.approx(-.01)


def test_monthly_and_annual_returns_compound_daily_returns():
    returns=pd.Series([.10,-.10,.20],index=pd.to_datetime(["2025-01-02","2025-01-31","2026-01-02"]))
    assert monthly_returns(returns).iloc[0]==pytest.approx((1.1*.9)-1)
    assert annual_returns(returns).iloc[0]==pytest.approx((1.1*.9)-1)
    assert annual_returns(returns).iloc[1]==pytest.approx(.20)


def test_alignment_uses_intersection_without_forward_fill():
    a=pd.Series([.01,.02],index=pd.to_datetime(["2026-01-02","2026-01-05"]),name="A")
    b=pd.Series([.03,.04],index=pd.to_datetime(["2026-01-05","2026-01-06"]),name="B")
    aligned=align_returns({"A":a,"B":b})
    assert list(aligned.index)==[pd.Timestamp("2026-01-05")]
    assert aligned.loc["2026-01-05","A"]==pytest.approx(.02)
    assert aligned.loc["2026-01-05","B"]==pytest.approx(.03)


def test_static_weight_portfolio_return():
    returns=pd.DataFrame({"SPY":[.10,-.10],"TLT":[.02,.04]},index=pd.to_datetime(["2026-01-02","2026-01-05"]))
    result=portfolio_returns(returns,{"SPY":.6,"TLT":.4})
    np.testing.assert_allclose(result.to_numpy(),[.068,-.044])


def test_returns_reject_insufficient_prices():
    with pytest.raises(AnalyticsError,match="two prices"):
        simple_returns(pd.Series([100.],index=pd.to_datetime(["2026-01-02"])))

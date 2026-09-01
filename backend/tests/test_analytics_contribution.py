import numpy as np
import pandas as pd
import pytest

from app.analytics.attribution import benchmark_relative_contributions
from app.analytics.contribution import return_contributions, risk_contributions
from app.analytics.portfolio import portfolio_returns
from app.analytics.risk import annualized_covariance_matrix, portfolio_volatility
from app.analytics.returns import cumulative_return


def test_marginal_component_and_percent_risk_contribution_identities():
    returns=pd.DataFrame({"A":[.01,-.02,.03,.00],"B":[.02,.01,-.01,.04]})
    weights={"A":.6,"B":.4}
    covariance=annualized_covariance_matrix(returns)
    volatility=portfolio_volatility(covariance,weights)
    rows=risk_contributions(covariance,weights)
    assert sum(row["component_risk_contribution"] for row in rows)==pytest.approx(volatility)
    assert sum(row["percent_risk_contribution"] for row in rows)==pytest.approx(1.0)
    expected_marginal=covariance.to_numpy()@np.array([.6,.4])/volatility
    np.testing.assert_allclose([row["marginal_risk_contribution"] for row in rows],expected_marginal)


def test_zero_volatility_contributions_are_null():
    covariance=pd.DataFrame(np.zeros((2,2)),index=["A","B"],columns=["A","B"])
    rows=risk_contributions(covariance,{"A":.5,"B":.5})
    assert all(row["component_risk_contribution"] is None for row in rows)
    assert all(row["percent_risk_contribution"] is None for row in rows)


def test_geometrically_linked_return_contributions_reconcile():
    returns=pd.DataFrame({"A":[.10,-.05,.02],"B":[.00,.04,-.01]})
    weights={"A":.6,"B":.4}
    rows,total=return_contributions(returns,weights)
    expected=cumulative_return(portfolio_returns(returns,weights))
    assert total==pytest.approx(expected)
    assert sum(row["weighted_return_contribution"] for row in rows)==pytest.approx(expected)
    assert rows[0]["asset_period_return"]==pytest.approx(1.1*.95*1.02-1)


def test_benchmark_relative_contribution_reconciles_active_difference():
    returns=pd.DataFrame({"SPY":[.02,-.01,.03],"QQQ":[.03,-.02,.04]})
    weights={"SPY":.4,"QQQ":.6}
    rows,total_active=benchmark_relative_contributions(returns,weights,"SPY")
    portfolio_total=cumulative_return(portfolio_returns(returns,weights))
    benchmark_total=cumulative_return(returns["SPY"])
    assert total_active==pytest.approx(portfolio_total-benchmark_total)
    assert sum(row["active_contribution"] for row in rows)==pytest.approx(total_active)
    spy=next(row for row in rows if row["ticker"]=="SPY")
    assert spy["benchmark_equivalent_weight"]==1.0
    assert spy["active_weight"]==pytest.approx(-.6)

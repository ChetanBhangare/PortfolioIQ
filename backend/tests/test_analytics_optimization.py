from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from app.analytics.constraints import OptimizationError, turnover, validate_weight_constraints
from app.analytics.optimization import (
    efficient_frontier,
    equal_weight_portfolio,
    expected_annual_returns,
    maximum_sharpe_portfolio,
    minimum_variance_portfolio,
    risk_parity_portfolio,
)
from app.analytics.risk import annualized_covariance_matrix, portfolio_variance


@pytest.fixture
def inputs():
    returns=pd.DataFrame({
        "A":[.010,.012,-.006,.008,.011,-.004,.009,.006],
        "B":[.004,.003,.005,.002,.006,.004,.003,.005],
        "C":[-.003,.015,.002,.010,-.005,.012,.001,.008],
    })
    expected=expected_annual_returns(returns,252)
    covariance=annualized_covariance_matrix(returns,252)
    current=np.array([.5,.3,.2])
    return returns,expected,covariance,current


def test_expected_return_annualization_preserves_labels(inputs):
    returns,expected,_,_=inputs
    pd.testing.assert_series_equal(expected,returns.mean()*252)


def test_equal_weight_and_turnover(inputs):
    _,expected,covariance,current=inputs
    result=equal_weight_portfolio(expected,covariance,0,current)
    assert sum(result["weights"].values())==pytest.approx(1)
    assert all(weight==pytest.approx(1/3) for weight in result["weights"].values())
    assert result["turnover"]==pytest.approx(.5*sum(abs(np.repeat(1/3,3)-current)))
    assert turnover(current,current)==0


def test_minimum_variance_respects_bounds_and_variance_identity(inputs):
    _,expected,covariance,current=inputs
    result=minimum_variance_portfolio(expected,covariance,0,current,.05,.8)
    weights=np.array(list(result["weights"].values()))
    assert weights.sum()==pytest.approx(1,abs=1e-8)
    assert np.all(weights>=.05-1e-8) and np.all(weights<=.8+1e-8)
    assert result["objective_value"]==pytest.approx(portfolio_variance(covariance,result["weights"]))
    equal=equal_weight_portfolio(expected,covariance,0,current)
    assert result["annualized_volatility"]<=equal["annualized_volatility"]+1e-8


def test_maximum_sharpe_improves_on_equal_weight(inputs):
    _,expected,covariance,current=inputs
    optimized=maximum_sharpe_portfolio(expected,covariance,0,current,0,.9)
    equal=equal_weight_portfolio(expected,covariance,0,current)
    assert optimized["solver"]["success"]
    assert optimized["sharpe_ratio"]>=equal["sharpe_ratio"]-1e-7
    assert sum(optimized["weights"].values())==pytest.approx(1)
    assert min(optimized["weights"].values())>=-1e-9


def test_maximum_sharpe_respects_turnover_limit(inputs):
    _,expected,covariance,current=inputs
    optimized=maximum_sharpe_portfolio(expected,covariance,0,current,.01,.9,.05)
    assert optimized["turnover"]<=.05+1e-7


def test_risk_parity_produces_equal_percent_contributions(inputs):
    _,expected,covariance,current=inputs
    result=risk_parity_portfolio(expected,covariance,0,current,.01,.9)
    percentages=np.array([row["percent_risk_contribution"] for row in result["risk_contribution"]])
    np.testing.assert_allclose(percentages,np.repeat(1/3,3),atol=2e-4)


def test_efficient_frontier_has_valid_points_and_reconciles_anchors(inputs):
    _,expected,covariance,current=inputs
    minimum=minimum_variance_portfolio(expected,covariance,0,current,0,.9)
    maximum=maximum_sharpe_portfolio(expected,covariance,0,current,0,.9)
    points,skipped,_=efficient_frontier(expected,covariance,0,current,0,.9,None,12,[minimum["expected_annual_return"],maximum["expected_annual_return"]])
    assert len(points)>=10
    assert all(point["solver"]["success"] for point in points)
    assert all(sum(point["weights"].values())==pytest.approx(1,abs=1e-7) for point in points)
    frontier_min=min(points,key=lambda point:point["annualized_volatility"])
    assert frontier_min["annualized_volatility"]==pytest.approx(minimum["annualized_volatility"],rel=1e-5)
    frontier_max=max(points,key=lambda point:point["sharpe_ratio"])
    assert frontier_max["sharpe_ratio"]==pytest.approx(maximum["sharpe_ratio"],rel=1e-5)
    assert isinstance(skipped,list)


def test_infeasible_bounds_and_turnover_are_rejected():
    with pytest.raises(OptimizationError,match="minimum"):
        validate_weight_constraints(3,.5,.4,True,np.array([1/3]*3))
    with pytest.raises(OptimizationError,match="exceeds 1"):
        validate_weight_constraints(3,.4,.8,True,np.array([1/3]*3))
    with pytest.raises(OptimizationError,match="below 1"):
        validate_weight_constraints(3,0,.3,True,np.array([1/3]*3))
    with pytest.raises(OptimizationError,match="Zero turnover"):
        validate_weight_constraints(3,.2,.6,True,np.array([.8,.1,.1]),0)


def test_solver_failure_is_not_silently_returned(monkeypatch,inputs):
    _,expected,covariance,current=inputs
    failed=SimpleNamespace(success=False,status=9,message="iteration limit",nit=1000,x=current,fun=0.0)
    monkeypatch.setattr("app.analytics.optimization.minimize",lambda *args,**kwargs:failed)
    with pytest.raises(OptimizationError,match="iteration limit"):
        minimum_variance_portfolio(expected,covariance,0,current)

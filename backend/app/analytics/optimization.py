import math
import warnings

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from app.analytics.constraints import OptimizationError, scipy_constraints, turnover, validate_weight_constraints
from app.analytics.contribution import risk_contributions
from app.analytics.risk import concentration_metrics, portfolio_variance, portfolio_volatility


STRATEGIES = ("equal_weight", "minimum_variance", "maximum_sharpe", "risk_parity")


def expected_annual_returns(returns: pd.DataFrame, annualization_factor: int = 252) -> pd.Series:
    if returns.empty or len(returns) < 2:
        raise OptimizationError("At least two aligned observations are required for expected returns")
    if returns.isna().any().any():
        raise OptimizationError("Expected-return input must not contain missing observations")
    return returns.mean() * annualization_factor


def _diagnostics(result):
    return {
        "success": bool(result.success),
        "status": int(result.status),
        "message": str(result.message),
        "iterations": int(result.nit) if getattr(result, "nit", None) is not None else None,
    }


def _run_solver(objective, initial, bounds, constraints, name):
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore",message="Values in x were outside bounds during a minimize step",category=RuntimeWarning)
        result = minimize(objective, initial, method="SLSQP", bounds=bounds, constraints=constraints, options={"maxiter": 1000, "ftol": 1e-12})
    diagnostics = _diagnostics(result)
    if not result.success or not np.all(np.isfinite(result.x)):
        raise OptimizationError(f"{name} optimization failed: {diagnostics['message']}")
    if abs(np.sum(result.x) - 1.0) > 1e-6:
        raise OptimizationError(f"{name} optimization returned unstable weights")
    return result.x, float(result.fun), diagnostics


def _metrics(name, vector, tickers, expected_returns, covariance, risk_free_rate, current_weights, objective_value, diagnostics):
    weights = {ticker: float(vector[index]) for index, ticker in enumerate(tickers)}
    expected = float(np.dot(vector, expected_returns.loc[tickers]))
    volatility = portfolio_volatility(covariance, weights)
    sharpe = None if np.isclose(volatility, 0.0) else float((expected - risk_free_rate) / volatility)
    return {
        "strategy": name,
        "weights": weights,
        "expected_annual_return": expected,
        "annualized_volatility": volatility,
        "sharpe_ratio": sharpe,
        **concentration_metrics(weights),
        "turnover": turnover(vector, current_weights),
        "objective_value": objective_value,
        "solver": diagnostics,
    }


def strategy_metrics(name, weights, expected_returns, covariance, risk_free_rate, current_weights):
    tickers = list(expected_returns.index)
    vector = np.array([weights[ticker] for ticker in tickers])
    return _metrics(name, vector, tickers, expected_returns, covariance, risk_free_rate, current_weights, None, {"success": True,"status": 0,"message": "Analytical portfolio; no numerical solve required","iterations": 0})


def equal_weight_portfolio(expected_returns, covariance, risk_free_rate, current_weights):
    tickers = list(expected_returns.index); vector = np.repeat(1.0 / len(tickers), len(tickers))
    return _metrics("equal_weight", vector, tickers, expected_returns, covariance, risk_free_rate, current_weights, None, {"success": True,"status": 0,"message": "Analytical equal weights","iterations": 0})


def _setup(expected_returns, minimum_weight, maximum_weight, current_weights, turnover_limit):
    n = len(expected_returns); current = np.asarray(current_weights,dtype=float)
    validate_weight_constraints(n,minimum_weight,maximum_weight,True,current,turnover_limit)
    bounds=[(minimum_weight,maximum_weight)]*n
    initial=current.copy() if np.all((current>=minimum_weight)&(current<=maximum_weight)) else np.repeat(1/n,n)
    return list(expected_returns.index),current,bounds,initial


def minimum_variance_portfolio(expected_returns,covariance,risk_free_rate,current_weights,minimum_weight=0,maximum_weight=1,turnover_limit=None,target_return=None):
    tickers,current,bounds,initial=_setup(expected_returns,minimum_weight,maximum_weight,current_weights,turnover_limit)
    matrix=covariance.loc[tickers,tickers].to_numpy()
    constraints=scipy_constraints(current,turnover_limit,target_return,expected_returns.loc[tickers].to_numpy())
    vector,value,diagnostics=_run_solver(lambda w:float(w@matrix@w),initial,bounds,constraints,"Minimum variance")
    return _metrics("minimum_variance",vector,tickers,expected_returns,covariance,risk_free_rate,current,value,diagnostics)


def maximum_sharpe_portfolio(expected_returns,covariance,risk_free_rate,current_weights,minimum_weight=0,maximum_weight=1,turnover_limit=None):
    tickers,current,bounds,initial=_setup(expected_returns,minimum_weight,maximum_weight,current_weights,turnover_limit)
    matrix=covariance.loc[tickers,tickers].to_numpy(); means=expected_returns.loc[tickers].to_numpy()
    def objective(weights):
        volatility=np.sqrt(max(0,float(weights@matrix@weights)))
        return 1e9 if volatility<1e-12 else -float((weights@means-risk_free_rate)/volatility)
    vector,value,diagnostics=_run_solver(objective,initial,bounds,scipy_constraints(current,turnover_limit),"Maximum Sharpe")
    return _metrics("maximum_sharpe",vector,tickers,expected_returns,covariance,risk_free_rate,current,value,diagnostics)


def risk_parity_portfolio(expected_returns,covariance,risk_free_rate,current_weights,minimum_weight=0,maximum_weight=1,turnover_limit=None):
    tickers,current,bounds,initial=_setup(expected_returns,minimum_weight,maximum_weight,current_weights,turnover_limit)
    equal=np.repeat(1.0/len(tickers),len(tickers))
    if turnover_limit is None or turnover(equal,current)<=turnover_limit+1e-12:
        initial=equal
    target=1.0/len(tickers); matrix=covariance.loc[tickers,tickers].to_numpy()
    def objective(vector):
        weights={ticker:float(vector[i]) for i,ticker in enumerate(tickers)}
        rows=risk_contributions(covariance,weights)
        percentages=[row["percent_risk_contribution"] for row in rows]
        if any(value is None for value in percentages): return 1e9
        return float(sum((value-target)**2 for value in percentages))
    constraints=scipy_constraints(current,turnover_limit)
    candidates=[initial,current,equal]
    inverse_volatility=1/np.sqrt(np.diag(matrix)); candidates.append(inverse_volatility/inverse_volatility.sum())
    candidates.extend(np.random.default_rng(0).dirichlet(np.ones(len(tickers)),30))
    solutions=[]
    for candidate in candidates:
        if np.any(candidate<minimum_weight) or np.any(candidate>maximum_weight): continue
        if turnover_limit is not None and turnover(candidate,current)>turnover_limit+1e-12: continue
        try:
            solutions.append(_run_solver(objective,candidate,bounds,constraints,"Risk parity"))
        except OptimizationError:
            continue
    if not solutions:
        raise OptimizationError("Risk parity optimization failed for all feasible starting portfolios")
    vector,value,diagnostics=min(solutions,key=lambda solution:solution[1])
    result=_metrics("risk_parity",vector,tickers,expected_returns,covariance,risk_free_rate,current,value,diagnostics)
    result["risk_contribution"]=risk_contributions(covariance,result["weights"])
    return result


def feasible_return_range(expected_returns,covariance,current_weights,minimum_weight,maximum_weight,turnover_limit):
    tickers,current,bounds,initial=_setup(expected_returns,minimum_weight,maximum_weight,current_weights,turnover_limit)
    means=expected_returns.loc[tickers].to_numpy(); constraints=scipy_constraints(current,turnover_limit)
    low,_,_=_run_solver(lambda w:float(w@means),initial,bounds,constraints,"Minimum feasible return")
    high,_,_=_run_solver(lambda w:-float(w@means),initial,bounds,constraints,"Maximum feasible return")
    return float(low@means),float(high@means)


def efficient_frontier(expected_returns,covariance,risk_free_rate,current_weights,minimum_weight,maximum_weight,turnover_limit,point_count,anchor_returns=()):
    low,high=feasible_return_range(expected_returns,covariance,current_weights,minimum_weight,maximum_weight,turnover_limit)
    targets=np.linspace(low,high,point_count)
    reserved=set()
    for anchor in anchor_returns:
        if low-1e-9<=anchor<=high+1e-9:
            candidates=np.argsort(np.abs(targets-anchor))
            index=next((int(candidate) for candidate in candidates if int(candidate) not in reserved),None)
            if index is not None:
                targets[index]=anchor; reserved.add(index)
    points=[]; skipped=[]
    for target in sorted(set(float(value) for value in targets)):
        try:
            point=minimum_variance_portfolio(expected_returns,covariance,risk_free_rate,current_weights,minimum_weight,maximum_weight,turnover_limit,target)
            point["strategy"]="efficient_frontier"; point["target_return"]=target
            points.append(point)
        except OptimizationError as error:
            skipped.append({"target_return":target,"reason":str(error)})
    return points,skipped,(low,high)

import math

import numpy as np

from app.analytics import AnalyticsError


class OptimizationError(AnalyticsError):
    """Raised for infeasible constraints or failed numerical optimization."""


def validate_weight_constraints(asset_count, minimum_weight, maximum_weight, long_only, current_weights, turnover_limit=None):
    if not long_only:
        raise OptimizationError("R2.3 supports long-only optimization only")
    if minimum_weight < 0 or maximum_weight < 0:
        raise OptimizationError("Long-only weight bounds cannot be negative")
    if minimum_weight > maximum_weight:
        raise OptimizationError("minimum_asset_weight cannot exceed maximum_asset_weight")
    if asset_count * minimum_weight > 1.0 + 1e-12:
        raise OptimizationError("Infeasible bounds: asset_count × minimum_asset_weight exceeds 1")
    if asset_count * maximum_weight < 1.0 - 1e-12:
        raise OptimizationError("Infeasible bounds: asset_count × maximum_asset_weight is below 1")
    if len(current_weights) != asset_count or not math.isclose(float(np.sum(current_weights)), 1.0, abs_tol=1e-6):
        raise OptimizationError("Current weights must contain every asset and sum to 1")
    if turnover_limit is not None and not 0 <= turnover_limit <= 1:
        raise OptimizationError("turnover_constraint must be between 0 and 1")
    if turnover_limit is not None and np.isclose(turnover_limit, 0.0):
        if np.any(current_weights < minimum_weight - 1e-12) or np.any(current_weights > maximum_weight + 1e-12):
            raise OptimizationError("Zero turnover is impossible because current weights violate bounds")


def turnover(new_weights, current_weights):
    return float(0.5 * np.abs(np.asarray(new_weights) - np.asarray(current_weights)).sum())


def scipy_constraints(current_weights, turnover_limit=None, target_return=None, expected_returns=None):
    constraints = [{"type": "eq", "fun": lambda weights: float(np.sum(weights) - 1.0)}]
    if turnover_limit is not None:
        constraints.append({
            "type": "ineq",
            "fun": lambda weights: float(turnover_limit - turnover(weights, current_weights)),
        })
    if target_return is not None:
        constraints.append({
            "type": "eq",
            "fun": lambda weights: float(np.dot(weights, expected_returns) - target_return),
        })
    return constraints

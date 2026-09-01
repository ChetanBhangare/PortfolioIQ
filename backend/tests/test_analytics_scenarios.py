import pytest

from app.analytics import AnalyticsError
from app.analytics.scenarios import ILLUSTRATIVE_HYPOTHETICAL_SCENARIOS,hypothetical_shock


def test_hypothetical_shock_contributions_reconcile():
    weights={"SPY":.6,"TLT":.4}; shocks={"SPY":-.20,"TLT":.10}
    result=hypothetical_shock(weights,shocks)
    assert result["type"]=="illustrative_hypothetical_shock"
    assert result["total_portfolio_shock"]==pytest.approx(.6*-.2+.4*.1)
    assert sum(row["shock_contribution"] for row in result["asset_shocks"])==pytest.approx(result["total_portfolio_shock"])


def test_unknown_custom_shock_ticker_is_rejected():
    with pytest.raises(AnalyticsError,match="not portfolio holdings"):
        hypothetical_shock({"SPY":1.0},{"QQQ":-.2})


def test_predefined_scenarios_are_explicitly_illustrative():
    assert {"Equity Selloff","Rate Shock","Risk-Off","Inflation Shock"}==set(ILLUSTRATIVE_HYPOTHETICAL_SCENARIOS)

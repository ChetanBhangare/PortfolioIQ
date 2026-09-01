from app.analytics import AnalyticsError


ILLUSTRATIVE_HYPOTHETICAL_SCENARIOS = {
    "Equity Selloff": {"SPY": -0.20, "QQQ": -0.25, "VNQ": -0.18, "TLT": 0.06, "GLD": 0.08},
    "Rate Shock": {"SPY": -0.08, "QQQ": -0.12, "VNQ": -0.14, "TLT": -0.15, "GLD": -0.05},
    "Risk-Off": {"SPY": -0.15, "QQQ": -0.20, "VNQ": -0.12, "TLT": 0.10, "GLD": 0.12},
    "Inflation Shock": {"SPY": -0.08, "QQQ": -0.12, "VNQ": -0.10, "TLT": -0.12, "GLD": 0.10},
}


def hypothetical_shock(weights, shocks, name="Custom Hypothetical Shock"):
    unknown=sorted(set(shocks)-set(weights))
    if unknown:
        raise AnalyticsError(f"Shock tickers are not portfolio holdings: {', '.join(unknown)}")
    rows=[]
    for ticker,weight in weights.items():
        shock=float(shocks.get(ticker,0.0)); contribution=float(weight*shock)
        rows.append({"ticker":ticker,"portfolio_weight":float(weight),"assumed_shock":shock,"shock_contribution":contribution})
    return {"name":name,"type":"illustrative_hypothetical_shock","asset_shocks":rows,"total_portfolio_shock":float(sum(row["shock_contribution"] for row in rows))}

"""Read-only smoke checks for a deployed PortfolioIQ frontend and backend."""
import argparse
import json
import urllib.request


PORTFOLIO = {
    "portfolio_name":"Production smoke", "benchmark_ticker":"SPY",
    "holdings":[
        {"ticker":"SPY","weight":.4}, {"ticker":"QQQ","weight":.25},
        {"ticker":"TLT","weight":.15}, {"ticker":"GLD","weight":.1},
        {"ticker":"VNQ","weight":.1},
    ],
    "start_date":"2021-01-01", "end_date":"2026-09-01",
    "risk_free_rate":0, "annualization_factor":252,
}


def get(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        if response.status != 200: raise RuntimeError(f"GET {url} returned {response.status}")
        return response.read()


def post(url, payload):
    request=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(request, timeout=120) as response:
        if response.status != 200: raise RuntimeError(f"POST {url} returned {response.status}")
        return json.load(response)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--frontend",required=True); parser.add_argument("--backend",required=True)
    args=parser.parse_args(); frontend=args.frontend.rstrip("/"); backend=args.backend.rstrip("/")
    get(frontend); health=json.loads(get(f"{backend}/health")); assert health["status"]=="ok"
    performance=post(f"{backend}/api/analytics/portfolio",PORTFOLIO)
    risk=post(f"{backend}/api/analytics/portfolio/risk",{**PORTFOLIO,"confidence_levels":[.95,.99]})
    optimization=post(f"{backend}/api/analytics/portfolio/optimize",{**PORTFOLIO,"objective":"maximum_sharpe","frontier_point_count":30,"requested_strategies":["equal_weight","minimum_variance","maximum_sharpe","risk_parity","efficient_frontier"],"hypothetical_scenarios":["Equity Selloff","Rate Shock","Risk-Off","Inflation Shock"]})
    assert performance["performance"]["total_return"] is not None
    assert len(risk["risk_contribution"])==5
    assert len(optimization["comparison"])==5 and optimization["efficient_frontier"]
    print(json.dumps({"frontend":"ok","health":health,"performance":"ok","risk":"ok","optimization":"ok"}))


if __name__=="__main__": main()

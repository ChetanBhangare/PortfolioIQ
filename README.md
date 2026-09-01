# PortfolioIQ
## Cloud-Native Portfolio Analytics, Risk & Investment Intelligence Platform

PortfolioIQ is an end-to-end financial analytics platform. Release 1 builds the cloud data foundation: incremental market-data ingestion, validation, AWS S3 Parquet storage, DuckDB-ready datasets, FastAPI, Next.js, Docker, tests, and CI.

### Releases
1. Cloud Data Platform
2. Portfolio Analytics
3. Quant Intelligence
4. Full Web Application
5. Production Deployment

### Architecture
External APIs -> Python ETL -> AWS S3 (Parquet) -> DuckDB/Python -> Analytics/ML -> FastAPI -> Next.js

### Setup
1. Copy `.env.example` to `.env`.
2. In `backend/`: create a Python 3.11 venv and `pip install -r requirements.txt`.
3. Run `uvicorn app.main:app --reload --port 8000`.
4. In `frontend/`: run `npm install` then `npm run dev`.
5. For local storage set `STORAGE_MODE=local`; for AWS set `STORAGE_MODE=s3` and fill `S3_BUCKET`.
6. Run `python -m app.data.ingestion --full-refresh` once, then `python -m app.data.ingestion` for incremental updates.

Never commit AWS credentials. Prefer AWS CLI/SSO or GitHub OIDC.

## AWS S3 setup on macOS

PortfolioIQ uses boto3's standard credential provider chain. Do not add
`AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` to source code or commit them to
`.env`. The bucket must have a globally unique name.

Install the AWS CLI if needed:

```bash
brew install awscli
aws --version
```

### Option A: AWS CLI credentials

Use credentials issued through your AWS account; do not paste them into project
files:

```bash
aws configure
aws sts get-caller-identity
aws s3 ls
```

`aws configure` stores credentials in the AWS CLI's user-level configuration,
outside this repository. Environment-based credentials and IAM roles also work
because boto3 discovers them automatically.

### Option B: AWS SSO (recommended for managed or college AWS accounts)

Your AWS administrator must provide the SSO start URL, SSO region, account, and
permission set. Configure and log in with a named profile:

```bash
aws configure sso --profile portfolioiq
aws sso login --profile portfolioiq
aws sts get-caller-identity --profile portfolioiq
aws s3 ls --profile portfolioiq
export AWS_PROFILE=portfolioiq
```

The SSO session expires periodically; rerun `aws sso login --profile portfolioiq`
when needed. Neither authentication option requires credentials in this repository.

### Configure and secure the bucket

Copy `.env.example` to `.env` and set only your own region and globally unique
private bucket name:

```dotenv
STORAGE_MODE=s3
AWS_REGION=<your-region>
S3_BUCKET=<your-globally-unique-private-bucket>
S3_PREFIX=portfolioiq
```

For a named CLI profile, also set `AWS_PROFILE=portfolioiq`. PortfolioIQ passes
that profile to a boto3 session. Without it, boto3 uses the default profile or the
next available source in its standard credential chain.

From the repository root, using the backend virtual environment, create or
re-secure the bucket and verify write/read/delete access:

```bash
backend/.venv/bin/python scripts/create_s3_bucket.py
backend/.venv/bin/python scripts/test_s3_connection.py
```

The bucket helper handles `us-east-1` correctly, is safe to rerun, blocks all
public access, and enables versioning. It does not create or store credentials.
The connectivity helper prints the caller account and ARN, but never credentials;
its temporary object is deleted after the read-back check.

## S3 migration and incremental-refresh proof

Keep the existing local Parquet files as a fallback. With the S3 environment
values above and a valid AWS CLI or SSO session, run from `backend/`:

```bash
python -m app.data.ingestion --tickers SPY QQQ GLD TLT --full-refresh
aws s3 ls "s3://$S3_BUCKET/$S3_PREFIX/raw/market_prices/" --recursive
aws s3 ls "s3://$S3_BUCKET/$S3_PREFIX/reports/data_quality/" --recursive
```

If the variables are stored only in `.env`, substitute the bucket and prefix in
the `aws s3 ls` commands; the AWS CLI does not load `.env` automatically. Confirm
these objects exist:

```text
portfolioiq/raw/market_prices/SPY.parquet
portfolioiq/raw/market_prices/QQQ.parquet
portfolioiq/raw/market_prices/GLD.parquet
portfolioiq/raw/market_prices/TLT.parquet
portfolioiq/reports/data_quality/SPY.json
portfolioiq/reports/data_quality/QQQ.json
portfolioiq/reports/data_quality/GLD.json
portfolioiq/reports/data_quality/TLT.json
```

Start the API from `backend/` in the same authenticated shell:

```bash
uvicorn app.main:app --reload --port 8000
curl http://localhost:8000/api/data/status
curl "http://localhost:8000/api/data/prices/SPY?limit=5"
```

The status response should mark SPY, QQQ, GLD, and TLT as available, and the price
endpoint should return S3-backed rows. Then prove the incremental path:

```bash
python -m app.data.ingestion --tickers SPY QQQ GLD TLT
```

For each ticker, the pipeline reads the stored S3 Parquet file, finds its latest
date, and requests only dates after it. If it is current, the log says no download
is needed. If the date range contains only non-trading days, Yahoo may be queried
for that small missing range and the log says no new rows were returned. In both
cases, unchanged Parquet data is not uploaded again.

Run the offline test suite (it uses mocks and requires no AWS credentials):

```bash
pytest
```

## Scheduled refresh with GitHub OIDC

The `Daily Market Data Refresh` workflow runs at 23:30 UTC Monday through Friday
and can also be started manually from the Actions tab. It assumes
`PortfolioIQGitHubActionsRole` through GitHub OIDC, verifies the resulting AWS
identity and S3 prefix, installs only the ingestion dependencies, and runs the
default configured ticker universe incrementally. It never uses `--full-refresh`.

The repository must define these Actions variables:

- `AWS_ROLE_ARN`: full ARN of the GitHub Actions IAM role
- `AWS_REGION`: bucket region
- `S3_BUCKET`: private data-lake bucket
- `S3_PREFIX`: PortfolioIQ object prefix

No `AWS_PROFILE`, access-key ID, secret access key, or local `.env` is used in
GitHub Actions. `aws-actions/configure-aws-credentials@v4` exchanges GitHub's OIDC
token for temporary role credentials. The AWS role trust policy must restrict
`repo:ChetanBhangare/PortfolioIQ` and the intended branch/event subjects.

## Release 1 freeze snapshot

Release 1 is the cloud data foundation. Yahoo Finance supplies adjusted daily
market bars through a provider abstraction; incremental Python ingestion validates
and stores one Parquet object per ticker in private, versioned S3. Compact schema
`1.0` manifests support API status reads without opening analytical objects.

The configured universe is:

```text
SPY QQQ IWM DIA XLF XLE XLK XLV XLY XLP XLI XLU XLB XLRE EFA EEM VEA VWO
TLT IEF SHY LQD HYG TIP GLD SLV DBC VNQ MTUM QUAL VLUE USMV VIG
```

As of 2026-08-31, all 33 configured datasets are present under:

```text
portfolioiq/raw/market_prices/<TICKER>.parquet
portfolioiq/metadata/market_prices/<TICKER>.json
portfolioiq/reports/data_quality/<TICKER>.json
```

The inventory contains 88,436 rows from 2016-01-04 through 2026-08-31,
33 Parquet objects, 33 manifests, and 33 quality reports. Thirty-two datasets pass
without warnings. VLUE passes with one recorded Yahoo OHLC inconsistency on
2026-08-31; widespread OHLC inconsistency remains a hard failure.

Incremental runs load each stored maximum date and request only a missing range.
When current, they refresh metadata and quality reports but do not rewrite
Parquet. A measured 33-ticker current run rewrote zero Parquet objects and took
11.813 seconds locally. GitHub Actions uses OIDC to assume a bucket-scoped role
and runs at 23:30 UTC Monday through Friday, with manual dispatch available.

Release 1 has 20 deterministic backend tests. Tests mock AWS and do not require
cloud credentials. Local boto3 authentication uses the normal credential chain;
GitHub uses temporary OIDC credentials. `.env` and credentials are untracked,
the S3 bucket is private with public access blocked and versioning enabled, and
application responses do not expose secrets.

Known limitations: Yahoo Finance is an external best-effort source; the platform
currently stores daily adjusted bars rather than intraday data; availability is
limited to the configured ETF universe; isolated provider anomalies require
quality-report review; and one-object-per-ticker should be reconsidered only if
the platform grows to intraday or multi-million-row ticker datasets.

## Release 2.1 portfolio analytics API

`POST /api/analytics/portfolio` accepts a named long-only portfolio, benchmark,
date range, annual risk-free rate, and static target weights. Tickers must belong
to the configured universe, holdings must be unique and nonnegative, and weights
must sum to 1.0 within `1e-6`.

```json
{
  "portfolio_name": "Core multi-asset portfolio",
  "benchmark_ticker": "SPY",
  "holdings": [
    {"ticker": "SPY", "weight": 0.40},
    {"ticker": "QQQ", "weight": 0.25},
    {"ticker": "TLT", "weight": 0.15},
    {"ticker": "GLD", "weight": 0.10},
    {"ticker": "VNQ", "weight": 0.10}
  ],
  "start_date": "2021-01-01",
  "end_date": "2026-08-31",
  "risk_free_rate": 0.0,
  "annualization_factor": 252
}
```

The service loads every unique ticker once through the Release 1 query layer. It
uses adjusted close-to-close simple returns and the intersection of trading dates
shared by every holding and the benchmark. Missing returns are never forward-filled.
Static target weights are applied to each aligned daily return; transaction costs,
weight drift, cash flows, and rebalance schedules are outside R2.1.

The response contains total return, CAGR, volatility, Sharpe, Sortino, Calmar,
best/worst day/month/year, structured drawdown dates and durations, and benchmark
alpha, beta, R², active return, tracking error, information ratio, and capture
ratios. All outputs are typed and JSON-safe. The backend suite contains 41
deterministic tests and analytics tests use synthetic data rather than AWS/Yahoo.

## Release 2.2 risk, contribution, attribution, and stress API

`POST /api/analytics/portfolio/risk` accepts the R2.1 portfolio contract plus
`confidence_levels` (`0.95`, `0.99`) and an optional custom historical stress
window. It loads each unique ticker once through the existing query layer and
reuses one aligned return frame for every risk calculation.

The response includes annualized covariance and correlation matrices, covariance-
based portfolio volatility, one-day historical and normal-parametric VaR,
historical CVaR, concentration, Euler volatility contributions, geometrically
linked return contributions, benchmark-relative contributions, and historical
stress results. VaR and CVaR are positive loss magnitudes: `0.02` means a 2%
one-day loss threshold or expected tail loss.

Historical VaR is the negative lower empirical return quantile. Historical CVaR
is the positive magnitude of the average return at or below that quantile.
Parametric VaR is `max(0, z * daily volatility - daily mean)` and assumes normal
daily returns; it is not presented as a tail-risk model.

Concentration reports largest, top-three, and top-five weights, HHI
`sum(weight²)`, and effective holdings `1 / HHI`. Risk contributions use annualized
sample covariance: marginal contribution is `(Σw)[i] / portfolio volatility`, and
component contribution is weight times marginal contribution. Components reconcile
to portfolio volatility and percentage contributions reconcile to 1.0.

Return contributions begin with daily `weight * asset return` and apply exact
geometric linking through subsequent portfolio growth. Their sum therefore equals
the compounded static-weight portfolio return; multiplying each asset's full-period
return by its starting weight would not provide that identity. Benchmark analysis
uses a 100% benchmark-equivalent portfolio and reports active differences. This is
benchmark-relative contribution analysis, not Brinson attribution.

Fixed stress windows are COVID Crash (2020-02-19–2020-03-23), 2022 Rate Shock
(2022-01-03–2022-10-14), and 2023 Banking Stress (2023-03-08–2023-03-24, covering
the SVB failure and immediate banking-market response). Scenarios outside the
requested portfolio period are explicitly unavailable. R2.2 does not implement
hypothetical factor shocks.

The backend suite contains 57 deterministic tests. No analytics unit test contacts
AWS or Yahoo.

## Release 2.3 optimization and scenario API

`POST /api/analytics/portfolio/optimize` adds long-only, fully invested portfolio
construction without changing the Release 1 data path. It returns the current and
equal-weight portfolios, minimum variance, maximum Sharpe, constrained risk parity,
and a requested-point efficient frontier. Every strategy reports weights, expected
annual return, covariance-based annual volatility, Sharpe ratio, HHI, effective
holdings, one-way turnover, and solver diagnostics.

Expected returns are arithmetic daily means multiplied by the annualization factor;
covariance is the aligned daily sample covariance multiplied by that factor. Minimum
variance minimizes `w'Σw`; maximum Sharpe maximizes `(w'μ - rf) / sqrt(w'Σw)`;
risk parity minimizes squared differences between percentage volatility
contributions. Under binding bounds or turnover limits, exact equal risk
contributions may be infeasible and the constrained best result is returned.

The contract supports per-asset minimum and maximum weights, an optional target
return for minimum variance/frontier feasibility, and optional one-way turnover
`0.5 * sum(abs(new weight - current weight))`. Infeasible bounds, target returns,
turnover configurations, and numerical solver failures produce clear HTTP 422
responses; unsuccessful results are never silently presented as portfolios.

Scenario output is explicitly labelled `illustrative_hypothetical_shock`. A
portfolio shock is the sum of target weight times supplied asset shock. These
forward-looking what-if calculations are distinct from R2.2's observed historical
stress windows and are not forecasts, factor models, or probability estimates.

Example request additions:

```json
{
  "objective": "maximum_sharpe",
  "minimum_asset_weight": 0.0,
  "maximum_asset_weight": 1.0,
  "turnover_constraint": null,
  "frontier_point_count": 30,
  "requested_strategies": ["equal_weight", "minimum_variance", "maximum_sharpe", "risk_parity", "efficient_frontier"],
  "hypothetical_scenarios": ["Equity Selloff", "Rate Shock"],
  "custom_asset_shocks": {"SPY": -0.20, "QQQ": -0.25, "TLT": 0.08}
}
```

R2.3 remains a single-period mean-covariance engine. It does not model transaction
costs, taxes, liquidity, estimation error, resampling, Black-Litterman views,
shorting, leverage, multi-period rebalancing, forecasting, or machine learning.

## Release 2.4 application integration and visualization

R2.4 provides a desktop-first Next.js, React, TypeScript, Tailwind CSS, and Plotly
application for the validated analytics APIs. The application includes Overview,
Portfolio Builder, Performance, Risk, Benchmark-Relative Contribution Analysis,
Optimization, and Stress Testing pages. Analytics are never recalculated in the
browser: charts, metrics, and tables display typed backend responses.

The Portfolio Builder defaults to SPY 40%, QQQ 25%, TLT 15%, GLD 10%, and VNQ
10%, benchmarked to SPY from 2021-01-01. Inputs are stored in versioned browser
local storage and can be reset. `Run Analysis` sends the portfolio concurrently to
the performance, risk, and optimization endpoints, then retains the three-response
bundle in React Context so navigation does not repeat S3-backed calculations.

The performance response now includes backward-compatible cumulative growth,
drawdown, monthly-return, and annual-return series calculated by the established
Python analytics functions. This supports Plotly visualization without duplicating
financial formulas in TypeScript.

Run locally in two terminals:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

cd frontend
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` when the backend is not at
the default URL. The backend uses its existing `STORAGE_MODE`, `AWS_REGION`,
`S3_BUCKET`, `S3_PREFIX`, and optional local `AWS_PROFILE` configuration. No AWS
credential belongs in frontend configuration.

R2.4 has no authentication, database-backed portfolios, collaboration, live
streaming, transaction-cost modeling, or production deployment. Analysis results
are held in memory and must be rerun after a browser refresh; only portfolio inputs
persist locally.

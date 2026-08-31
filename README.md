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

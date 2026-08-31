# PortfolioIQ Architecture

Market-data APIs are ingestion sources, not application databases.

## Storage
- S3/Parquet: historical market, macro, factor, processed, feature, model, and report data.
- PostgreSQL (planned): users, portfolios, holdings, saved scenarios, runs, prediction metadata.
- DuckDB: analytical queries over Parquet.

## Incremental ingestion
For each ticker, load latest stored date, request only missing dates, validate, merge/dedupe, persist, and write a quality report.

Local and S3 modes use the same `StorageBackend` interface. With S3 mode enabled,
logical keys such as `raw/market_prices/SPY.parquet` are stored below the configured
prefix (for example, `portfolioiq/raw/market_prices/SPY.parquet`). boto3 obtains
authentication from the standard AWS credential chain; credentials are never part
of the storage interface or project configuration files.

## Data-lake namespaces

Centralized key helpers keep storage paths out of ingestion and query logic. The
planned namespaces are `raw`, `processed`, `features`, `models`, `metadata`, and
`reports`. Release 1 currently writes only raw market prices, dataset manifests,
and quality reports. Later jobs can add subtrees without changing either storage
backend.

Market prices use one object per ticker, such as
`raw/market_prices/SPY.parquet`. This is the right Release 1 tradeoff for 40–60
liquid ETFs and daily history: each object is small, full-ticker reads are common,
and yearly partitioning would create many small objects and extra S3 requests.
Reassess `ticker=<ticker>/year=<year>/data.parquet` partitioning when individual
ticker objects become expensive to rewrite or scan—roughly when intraday data,
thousands of assets, or multi-million-row ticker datasets are introduced. If that
happens, benchmark DuckDB pruning and S3 request counts before migrating.

## Market-price schema and manifests

Schema version `1.0` has the canonical ordered columns:

```text
date, ticker, open, high, low, close, volume
```

Each successful dataset has a compact manifest at
`metadata/market_prices/<TICKER>.json` containing provider, row count, date range,
UTC refresh timestamp, schema version, quality status, and logical storage key.
The status API reads these small manifests rather than downloading every Parquet
object. Manifests describe datasets; they do not duplicate observations.

## Data quality policy

Hard failures block a Parquet write: empty datasets, duplicate ticker/date rows,
missing or nonpositive close values, non-monotonic dates, negative volume, and
widespread OHLC inconsistency (more than five rows or 0.1% of the dataset).
Warnings do not block a write: isolated OHLC inconsistencies, moves over 50%,
calendar gaps over 10 days, and data more than 7 calendar days stale. Isolated
adjusted-price anomalies remain visible without discarding an otherwise sound
history. Every report includes counts plus explicit `failures`, `warnings`,
`passed`, and `status` fields.

## Cost posture

- Parquet compression and columnar reads reduce storage and data transfer.
- Incremental refreshes limit upstream calls to missing dates.
- Unchanged Parquet objects are not rewritten, avoiding requests and versions.
- Small manifests keep status checks from reading full analytical objects.
- S3 Standard fits actively queried data at the current scale.
- Glacier and aggressive lifecycle transitions are inappropriate while these
  datasets support interactive API and analytics reads.

## AWS security and CI/CD

The development bucket is private, has all S3 public-access blocks enabled, and
uses versioning. `.env`, AWS credentials, and generated data are excluded from
Git. boto3 uses a named local profile, environment credentials, SSO, or an IAM
role through its normal credential chain; APIs and application logs never return
secret values.

`AmazonS3FullAccess` is acceptable only as a temporary development convenience.
The example [least-privilege policy](aws/portfolioiq-s3-policy.json) scopes list,
read, write, and connectivity-test deletion to this project's bucket and prefix.
Deletion can be removed if the connectivity/maintenance workflow changes. Review
and attach it manually only after testing; the project does not change IAM policy.

The scheduled GitHub workflow uses GitHub OIDC: the `main` repository workflow
assumes `PortfolioIQGitHubActionsRole`, and
`aws-actions/configure-aws-credentials@v4` exchanges the OIDC token for temporary
AWS credentials. The job receives only non-secret repository variables and does
not use a local profile, `.env`, or long-lived AWS access keys. The role trust
policy should restrict subjects to `ChetanBhangare/PortfolioIQ` and the intended
branch or workflow events; its permissions should remain scoped to the PortfolioIQ
S3 bucket and prefix.

## Release 1 operational baseline

The frozen Release 1 path is:

```text
Yahoo Finance -> provider abstraction -> incremental ingestion -> structured
quality validation -> private S3 Parquet + JSON manifests/reports -> FastAPI
```

The 33-ticker universe is defined once as `DEFAULT_ASSET_UNIVERSE` in
`backend/app/core/settings.py`. Market-price schema `1.0` contains `date`,
`ticker`, `open`, `high`, `low`, `close`, and `volume`. Each ticker has one raw
Parquet object, one metadata manifest, and one quality report below the
`portfolioiq` prefix. The status endpoint reads manifests; it does not scan
Parquet. Price endpoints read the configured storage backend, so S3 mode has no
local-file fallback.

The 2026-08-31 freeze inventory has 33 successful datasets, 88,436 total rows,
and 99 current objects totaling approximately 4.59 MB. Thirty-two datasets pass
cleanly; VLUE passes with one isolated OHLC warning. There are no hard failures,
stale warnings, suspicious-gap warnings, extreme-move warnings, duplicate-key
issues, or schema-version mismatches.

Incremental refreshes preserve current Parquet objects and rewrite only changed
datasets; metadata and quality reports record every refresh. A full current-universe
rerun completed in 11.813 seconds with 33 unchanged and zero rewritten Parquet
objects. The S3-backed API reported all 33 datasets available. The backend suite
contains 20 offline tests.

Operational limitations remain intentionally narrow: Yahoo availability and
adjusted-bar quality are external dependencies; the model is daily, not intraday;
S3 partitioning remains one file per ticker at this scale; and GitHub/AWS trust
and role policies require administrative review when repository or branch scope
changes. These limitations do not require Release 2 architecture in Release 1.

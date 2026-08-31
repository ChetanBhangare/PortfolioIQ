# Codex starter prompt

Read README.md and docs/ARCHITECTURE.md first. Preserve this architecture: external APIs -> incremental ETL -> AWS S3 Parquet -> DuckDB/Python -> FastAPI -> Next.js. Do not put financial calculations in the frontend. Do not hard-code credentials. We are in Release 1. Run backend tests, inspect ingestion, help configure S3 securely, validate one ticker end-to-end, then add FRED macro ingestion using the same storage interfaces.

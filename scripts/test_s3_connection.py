"""Perform a write/read/delete connectivity check against the configured S3 bucket."""

import os
from pathlib import Path
from uuid import uuid4

import boto3
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main():
    load_dotenv(PROJECT_ROOT / ".env")
    region = os.getenv("AWS_REGION", "us-east-1")
    bucket = os.getenv("S3_BUCKET")
    prefix = os.getenv("S3_PREFIX", "portfolioiq").strip("/")
    if not bucket:
        raise SystemExit("S3_BUCKET is not configured. Set it in .env or your environment.")

    session = boto3.Session(region_name=region)
    identity = session.client("sts").get_caller_identity()
    s3 = session.client("s3")
    s3.head_bucket(Bucket=bucket)

    key = f"{prefix}/connectivity-tests/{uuid4().hex}.txt".strip("/")
    payload = b"PortfolioIQ S3 connectivity test"
    uploaded = False
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=payload, ContentType="text/plain")
        uploaded = True
        downloaded = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        if downloaded != payload:
            raise RuntimeError("S3 read-back content did not match the uploaded content")
    finally:
        if uploaded:
            s3.delete_object(Bucket=bucket, Key=key)

    print(
        f"S3 connectivity succeeded for account {identity['Account']} using "
        f"{identity['Arn']} and private bucket s3://{bucket}. Temporary object deleted."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit(f"S3 connectivity failed: {error}") from error

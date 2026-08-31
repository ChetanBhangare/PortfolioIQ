"""Create or secure the private S3 bucket configured in the project environment."""

import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main():
    load_dotenv(PROJECT_ROOT / ".env")
    region = os.getenv("AWS_REGION", "us-east-1")
    bucket = os.getenv("S3_BUCKET")
    if not bucket:
        raise SystemExit("S3_BUCKET is not configured. Set it in .env or your environment.")

    client = boto3.client("s3", region_name=region)
    try:
        client.head_bucket(Bucket=bucket)
        result = "already exists and is reachable"
    except ClientError as error:
        code = str(error.response.get("Error", {}).get("Code", ""))
        if code not in {"404", "NoSuchBucket", "NotFound"}:
            raise SystemExit(
                f"Cannot inspect s3://{bucket} (AWS error {code or 'unknown'}). "
                "Check that the name is available and your AWS identity has permission."
            ) from error
        kwargs = {"Bucket": bucket}
        if region != "us-east-1":
            kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}
        client.create_bucket(**kwargs)
        result = f"created in {region}"

    client.put_public_access_block(
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    client.put_bucket_versioning(
        Bucket=bucket, VersioningConfiguration={"Status": "Enabled"}
    )
    print(f"s3://{bucket} {result}; public access is blocked and versioning is enabled.")


if __name__ == "__main__":
    main()

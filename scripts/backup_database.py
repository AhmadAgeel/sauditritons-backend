#!/usr/bin/env python3
"""Create a compressed PostgreSQL backup and upload it to S3-compatible storage."""

from __future__ import annotations

import gzip
import os
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import boto3
from botocore.config import Config


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    database_url = required("PRODUCTION_DATABASE_URL")
    bucket = required("BACKUP_S3_BUCKET")
    access_key = required("BACKUP_S3_ACCESS_KEY_ID")
    secret_key = required("BACKUP_S3_SECRET_ACCESS_KEY")
    endpoint = os.getenv("BACKUP_S3_ENDPOINT_URL", "").strip() or None
    region = os.getenv("BACKUP_S3_REGION", "auto").strip() or "auto"
    url_style = os.getenv("BACKUP_S3_URL_STYLE", "path").strip() or "path"
    if url_style not in {"path", "virtual"}:
        raise SystemExit("BACKUP_S3_URL_STYLE must be 'path' or 'virtual'")
    retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
    now = datetime.now(timezone.utc)
    key = f"database/{now:%Y/%m}/sauditritons-{now:%Y%m%dT%H%M%SZ}.dump.gz"

    with tempfile.TemporaryDirectory() as directory:
        raw_path = Path(directory) / "database.dump"
        compressed_path = Path(directory) / "database.dump.gz"
        subprocess.run(
            ["pg_dump", "--dbname", database_url, "--format=custom", "--no-owner", "--no-acl", "--file", str(raw_path)],
            check=True,
        )
        with raw_path.open("rb") as source, gzip.open(compressed_path, "wb", compresslevel=9) as destination:
            while chunk := source.read(1024 * 1024):
                destination.write(chunk)

        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4", s3={"addressing_style": url_style}),
        )
        client.upload_file(
            str(compressed_path),
            bucket,
            key,
            ExtraArgs={"ContentType": "application/gzip", "CacheControl": "no-store"},
        )

        cutoff = now - timedelta(days=retention_days)
        expired = []
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix="database/"):
            for item in page.get("Contents", []):
                if item["LastModified"] < cutoff:
                    expired.append({"Key": item["Key"]})
                if len(expired) == 1000:
                    client.delete_objects(Bucket=bucket, Delete={"Objects": expired})
                    expired = []
        if expired:
            client.delete_objects(Bucket=bucket, Delete={"Objects": expired})

    print(f"Uploaded {key}")


if __name__ == "__main__":
    main()

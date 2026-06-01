"""Storage helper to upload media to either S3 or use local filesystem.

This is a small convenience wrapper; `boto3` is optional and only required
if you want S3 uploads. The function raises if upload fails.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def upload_to_local(src_path: str, dest_dir: str) -> str:
    src = Path(src_path)
    if not src.exists():
        raise FileNotFoundError(f"Source not found: {src}")
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    with src.open("rb") as rf, dest.open("wb") as wf:
        wf.write(rf.read())
    return str(dest)


def upload_to_s3(src_path: str, bucket: str, key: Optional[str] = None) -> str:
    try:
        import boto3
    except Exception as e:
        raise RuntimeError("boto3 is required for S3 uploads") from e

    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION"),
    )
    src = Path(src_path)
    if not src.exists():
        raise FileNotFoundError(f"Source not found: {src}")
    key = key or src.name
    s3.upload_file(str(src), bucket, key)
    return f"s3://{bucket}/{key}"

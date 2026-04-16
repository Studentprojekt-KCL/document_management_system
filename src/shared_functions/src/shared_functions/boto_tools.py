"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law."""

import os
import io
import json
from contextlib import suppress

import boto3
from botocore.exceptions import ClientError
from dmis_logger import dms_error


def upload_file(content: dict | list, file_name: str, bucket: str = "slask") -> str:
    """Upload files to MinIO.

    Args:
    ----
        content: JSON structured content to upload.
        file_name: What to name the file.
        bucket: Name of bucket in MinIO (defaults to slask).
    """
    try:
        client = boto3.client(
            "s3",
            endpoint_url=os.environ.get("MINIO_ACCESS_ADDRESS"),
            aws_access_key_id=os.environ.get("MINIO_USERNAME"),
            aws_secret_access_key=os.environ.get("MINIO_PASSWORD"),
        )
    except ClientError as err:
        dms_error(f"Could not connect to MinIO (might be missing credentials). {err}")

    with suppress(ClientError):
        client.create_bucket(Bucket=bucket)

    data = io.BytesIO(json.dumps(content).encode("utf-8"))
    client.upload_fileobj(data, bucket, file_name)

    url = client.generate_presigned_url(ClientMethod="get_object", Params={"Bucket": bucket, "Key": file_name}, ExpiresIn=3600)

    return url

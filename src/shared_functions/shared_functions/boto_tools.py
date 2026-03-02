import os
import io
import json

import boto3
from botocore.exceptions import ClientError


def upload_file(content: dict | list):
    client = boto3.client(
        "s3",
        endpoint_url=os.environ.get('MINIO_ADDRESS'),
        aws_access_key_id=os.environ.get('MINIO_USERNAME'),
        aws_secret_access_key=os.environ.get('MINIO_PASSWORD'),
    ) #TODO error handling for this botocore.exceptions.ClientError (when auth is incorrect).
    try:
        client.create_bucket(Bucket="artifacts") #TODO, prob look if bucket exists.
    except ClientError:
        pass

    data = io.BytesIO(json.dumps(content).encode("utf-8"))
    client.upload_fileobj(data, "artifacts", "myfile.json")

#backend/app/dependencies.py

from functools import lru_cache
import boto3
from app.config import settings

@lru_cache
def get_s3():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
    )

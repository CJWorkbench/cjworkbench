import os

__all__ = ("AWS_S3_ENDPOINT", "S3_BUCKET_NAME_PATTERN")

AWS_S3_ENDPOINT = os.environ.get("AWS_S3_ENDPOINT")  # None means AWS default
S3_BUCKET_NAME_PATTERN = os.environ.get("S3_BUCKET_NAME_PATTERN", "%s")

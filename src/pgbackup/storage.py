"""S3 upload functionality."""

import logging

import boto3

logger = logging.getLogger(__name__)


def upload_to_s3(
    filepath: str,
    bucket: str,
    key: str,
    endpoint_url: str | None = None,
) -> str:
    """Upload a file to S3 and return the S3 URI.

    Parameters
    ----------
    filepath:
        Local path to the file to upload.
    bucket:
        Target S3 bucket name.
    key:
        S3 object key.
    endpoint_url:
        Optional custom endpoint for S3-compatible storage.

    Returns
    -------
    str
        The ``s3://bucket/key`` URI of the uploaded object.
    """
    kwargs: dict = {}
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url

    logger.info(
        "Uploading %s -> s3://%s/%s", filepath, bucket, key,
    )
    client = boto3.client("s3", **kwargs)
    client.upload_file(filepath, bucket, key)
    uri = f"s3://{bucket}/{key}"
    logger.info("Upload complete: %s", uri)
    return uri

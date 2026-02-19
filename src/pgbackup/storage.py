"""S3 upload functionality."""

import boto3


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

    client = boto3.client("s3", **kwargs)
    client.upload_file(filepath, bucket, key)
    return f"s3://{bucket}/{key}"

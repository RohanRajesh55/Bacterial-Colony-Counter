"""S3/MinIO client wrapper for image storage operations."""

import logging
from io import BytesIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from api.config import Settings

logger = logging.getLogger(__name__)


def get_s3_client():
    """Create and return a configured S3 client for MinIO.

    Returns:
        boto3.client: Configured S3 client instance.
    """
    settings = Settings()
    return boto3.client(
        service_name="s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name=settings.S3_REGION,
    )


def upload_image(
    bucket: str,
    key: str,
    image_bytes: bytes,
    content_type: str = "image/png",
) -> str:
    """Upload an image to S3/MinIO.

    Args:
        bucket: S3 bucket name.
        key: Object key (path) in the bucket.
        image_bytes: Raw image bytes to upload.
        content_type: MIME type of the image (default: image/png).

    Returns:
        str: The object key that was uploaded.
    """
    client = get_s3_client()
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=BytesIO(image_bytes),
        ContentType=content_type,
    )
    logger.info("Uploaded image to s3://%s/%s", bucket, key)
    return key


def get_presigned_url(bucket: str, key: str, expires_in: int = 3600) -> str:
    """Generate a presigned URL for accessing an S3 object.

    Args:
        bucket: S3 bucket name.
        key: Object key (path) in the bucket.
        expires_in: URL expiration time in seconds (default: 1 hour).

    Returns:
        str: Presigned URL for the object.
    """
    client = get_s3_client()
    url = client.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )
    return url


def ensure_bucket_exists(bucket: str) -> None:
    """Ensure the specified S3 bucket exists, creating it if necessary.

    Args:
        bucket: S3 bucket name to check/create.
    """
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=bucket)
        logger.info("Bucket %s already exists", bucket)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code in ("404", "NoSuchBucket"):
            logger.info("Creating bucket %s", bucket)
            client.create_bucket(Bucket=bucket)
        else:
            logger.error("Error checking bucket %s: %s", bucket, e)
            raise

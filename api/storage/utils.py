"""Utility functions for storage operations."""

import hashlib


def compute_image_hash(image_bytes: bytes) -> str:
    """Compute SHA256 hash of image bytes for deduplication.

    Args:
        image_bytes: Raw image bytes.

    Returns:
        str: 64-character hexadecimal hash string.
    """
    return hashlib.sha256(image_bytes).hexdigest()


def get_extension_from_content_type(content_type: str) -> str:
    """Map MIME content type to file extension.

    Args:
        content_type: MIME type string (e.g., "image/jpeg").

    Returns:
        str: File extension without dot (e.g., "jpg").
    """
    content_type_map = {
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/png": "png",
        "image/gif": "gif",
        "image/webp": "webp",
        "image/bmp": "bmp",
        "image/tiff": "tiff",
    }
    return content_type_map.get(content_type.lower(), "bin")

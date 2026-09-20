from __future__ import annotations

from dataclasses import dataclass
import base64
import binascii
from io import BytesIO
import re
from urllib.parse import quote
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

from app.config import settings

register_heif_opener()


class StorageNotConfiguredError(RuntimeError):
    pass


class InvalidImageError(ValueError):
    pass


class StorageUploadError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredImage:
    url: str
    key: str
    width: int
    height: int
    bytes: int
    content_type: str = "image/webp"


_DATA_IMAGE_RE = re.compile(r"^data:image/(?:jpeg|png|webp|heic|heif);base64,(.+)$", re.IGNORECASE | re.DOTALL)
EVENT_IMAGE_KEY_RE = re.compile(r"^events/[0-9a-f]{32}\.webp$")


def decode_inline_image(value: str) -> bytes:
    match = _DATA_IMAGE_RE.match(value.strip())
    if match is None:
        raise InvalidImageError("The stored value is not a supported inline image")
    try:
        return base64.b64decode(match.group(1), validate=True)
    except (ValueError, binascii.Error) as error:
        raise InvalidImageError("The stored inline image is malformed") from error


def storage_is_configured() -> bool:
    return all((
        settings.object_storage_access_key_id,
        settings.object_storage_secret_access_key,
        settings.object_storage_bucket,
        settings.object_storage_public_base_url,
    ))


def _client():
    if not storage_is_configured():
        raise StorageNotConfiguredError("Object storage is not configured")
    return boto3.client(
        "s3",
        endpoint_url=settings.object_storage_endpoint_url or None,
        region_name=settings.object_storage_region,
        aws_access_key_id=settings.object_storage_access_key_id,
        aws_secret_access_key=settings.object_storage_secret_access_key,
        config=Config(signature_version="s3v4", s3={"addressing_style": settings.object_storage_url_style}),
    )


def prepare_event_image(source: bytes) -> tuple[bytes, int, int]:
    if not source:
        raise InvalidImageError("Choose an image to upload")
    if len(source) > settings.object_storage_image_max_bytes:
        raise InvalidImageError("Image must be smaller than 10 MB")

    try:
        with Image.open(BytesIO(source)) as opened:
            image = ImageOps.exif_transpose(opened)
            image.thumbnail((2400, 2400), Image.Resampling.LANCZOS)
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA" if "transparency" in image.info else "RGB")
            width, height = image.size
            output = BytesIO()
            image.save(output, format="WEBP", quality=92, method=6, lossless=False)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise InvalidImageError("Upload a valid JPEG, PNG, HEIC, or WebP image") from error

    return output.getvalue(), width, height


def store_event_image(source: bytes) -> StoredImage:
    body, width, height = prepare_event_image(source)
    key = f"events/{uuid4().hex}.webp"
    try:
        _client().put_object(
            Bucket=settings.object_storage_bucket,
            Key=key,
            Body=body,
            ContentType="image/webp",
            CacheControl="public, max-age=31536000, immutable",
        )
    except (BotoCoreError, ClientError) as error:
        raise StorageUploadError("Image storage is temporarily unavailable") from error

    base = settings.object_storage_public_base_url.rstrip("/")
    return StoredImage(
        url=f"{base}/{quote(key, safe='/')}",
        key=key,
        width=width,
        height=height,
        bytes=len(body),
    )


def read_stored_image(key: str):
    try:
        return _client().get_object(Bucket=settings.object_storage_bucket, Key=key)
    except (BotoCoreError, ClientError) as error:
        code = getattr(error, "response", {}).get("Error", {}).get("Code")
        if code in {"NoSuchKey", "404", "NotFound"}:
            raise FileNotFoundError(key) from error
        raise StorageUploadError("Image storage is temporarily unavailable") from error

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.storage import EVENT_IMAGE_KEY_RE, StorageNotConfiguredError, StorageUploadError, read_stored_image


router = APIRouter(prefix="/media", tags=["Media"])


@router.get("/{key:path}")
def event_image(key: str):
    if EVENT_IMAGE_KEY_RE.fullmatch(key) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    try:
        stored = read_stored_image(key)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    except StorageNotConfiguredError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Image storage is not configured")
    except StorageUploadError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Image storage is temporarily unavailable")

    body = stored["Body"]

    def stream():
        try:
            while chunk := body.read(64 * 1024):
                yield chunk
        finally:
            body.close()

    headers = {"Cache-Control": "public, max-age=31536000, immutable"}
    if stored.get("ETag"):
        headers["ETag"] = stored["ETag"]
    return StreamingResponse(stream(), media_type=stored.get("ContentType") or "image/webp", headers=headers)

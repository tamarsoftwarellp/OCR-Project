"""
Server-side Cloudinary upload helper. Used when the BACKEND itself receives
an uploaded file and wants to send it to Cloudinary on the user's behalf - as
opposed to the earlier `uploads.router.get_cloudinary_signature` flow, where
the frontend uploads directly to Cloudinary using a signature.

Both approaches are valid; use this one when you want the backend to own the
upload (simpler frontend, but the file passes through your server).
"""
import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException

from app.config import settings

# Configure the Cloudinary SDK once, using the same credentials already
# defined in app/config.py (.env).
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)

# Only allow document-type files for claims (avoid accidental image/video
# uploads bloating the "claims" folder). Adjust as needed.
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE_MB = 25


async def upload_pdf_to_cloudinary(file: UploadFile, folder: str = "claims") -> dict:
    """
    Uploads an incoming FastAPI UploadFile to Cloudinary and returns the
    relevant Cloudinary response fields (secure_url, public_id, etc.).

    Raises HTTPException(400) for invalid file type / size, and
    HTTPException(502) if Cloudinary itself fails.
    """
    filename = file.filename or "upload"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({size_mb:.1f} MB). Max allowed is {MAX_FILE_SIZE_MB} MB.",
        )

    try:
        # resource_type="auto" lets Cloudinary correctly store PDFs
        # (which Cloudinary treats as "raw"/"image" depending on content).
        result = cloudinary.uploader.upload(
            contents,
            folder=folder,
            resource_type="auto",
            use_filename=True,
            unique_filename=True,
            overwrite=False,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Cloudinary upload failed: {e}")

    return {
        "secure_url": result.get("secure_url"),
        "public_id": result.get("public_id"),
        "resource_type": result.get("resource_type"),
        "format": result.get("format"),
        "bytes": result.get("bytes"),
        "original_filename": filename,
        "mime_type": file.content_type or "application/octet-stream",
    }

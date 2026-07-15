"""
Optional helper: generates a Cloudinary upload signature so the FRONTEND can
upload directly to Cloudinary (client-side) without ever seeing the
CLOUDINARY_API_SECRET. This matches the flow you described:

    frontend --(direct upload)--> Cloudinary
    frontend --(POST cloudinary url)--> our /claims endpoint

If you already generate the signature elsewhere (e.g. a Node service), you
can skip mounting this router entirely.

This file ALSO exposes a server-side upload endpoint (POST /uploads/pdf)
for cases where you'd rather send the file straight to the backend and let
IT talk to Cloudinary.
"""
import time
import hashlib

from fastapi import APIRouter, Depends, UploadFile, File, Form

from app.config import settings
from app.core.security import get_current_user
from app.services.cloudinary_service import upload_pdf_to_cloudinary

router = APIRouter(
    prefix="/uploads", tags=["uploads"], dependencies=[Depends(get_current_user)]
)


@router.get("/cloudinary-signature")
async def get_cloudinary_signature(folder: str = "claims"):
    timestamp = int(time.time())
    params_to_sign = f"folder={folder}&timestamp={timestamp}{settings.CLOUDINARY_API_SECRET}"
    signature = hashlib.sha1(params_to_sign.encode("utf-8")).hexdigest()

    return {
        "timestamp": timestamp,
        "signature": signature,
        "api_key": settings.CLOUDINARY_API_KEY,
        "cloud_name": settings.CLOUDINARY_CLOUD_NAME,
        "folder": folder,
    }


@router.post("/pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    folder: str = Form(default="claims"),
):
    """
    Server-side upload: frontend sends the raw file here (multipart/form-data),
    the backend uploads it to Cloudinary and returns the secure_url.

    Example (curl):
        curl -X POST http://localhost:8000/uploads/pdf \\
             -F "file=@MEDSAVE.pdf" \\
             -F "folder=claims"

    The frontend then typically takes the returned `secure_url` and calls
    POST /claims with it to create the claim record. (Or use the combined
    POST /claims/upload endpoint to do both steps in a single call.)
    """
    result = await upload_pdf_to_cloudinary(file, folder=folder)
    return result

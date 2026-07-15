from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import ensure_indexes
from app.routers import auth, claims, documents, uploads

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Backend that stores raw OCR-extracted JSON (from the Claim OCR "
        "engine) exactly as produced, and serves it to the frontend so the "
        "claim review form can be auto-filled. Missing / wrongly extracted "
        "fields stay editable by the reviewer via the entity PATCH endpoint."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(claims.router)
app.include_router(documents.router)
app.include_router(documents.callback_router)
app.include_router(uploads.router)


@app.on_event("startup")
async def _on_startup():
    await ensure_indexes()


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.ENV}


@app.get("/")
async def root():
    return {
        "message": "Claim OCR Backend is running",
        "docs": "/docs",
    }

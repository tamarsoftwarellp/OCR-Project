"""
Central configuration for the backend.
All values are read from environment variables (see .env.example).
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ---- MongoDB ----
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "claims_db"

    # ---- Cloudinary (used only if backend itself needs to talk to Cloudinary,
    # e.g. to fetch the uploaded file for the OCR engine) ----
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # ---- OCR engine ----
    # If the OCR engine runs as a separate microservice, point to its URL.
    # If it runs in-process / as a subprocess, this can be left blank.
    OCR_ENGINE_URL: str = "http://localhost:9000"

    # ---- Backend ----
    BACKEND_PUBLIC_URL: str = "http://localhost:8000"

    # ---- App ----
    APP_NAME: str = "Claim OCR Backend"
    ENV: str = "development"
    CORS_ORIGINS: list[str] = ["*"]

    # ---- Auth / JWT ----
    # IMPORTANT: override JWT_SECRET_KEY via .env in production. This default
    # is only here so the app doesn't crash on a fresh clone.
    JWT_SECRET_KEY: str = "change-this-secret-key-in-env-file"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ---- OCR engine callback auth ----
    # Shared secret (NOT a user JWT) so the OCR engine - a machine, not a
    # logged-in reviewer - can still POST results back to
    # /claims/{claim_id}/documents/callback after that router got locked
    # down with get_current_user. Override via .env in production.
    OCR_CALLBACK_SECRET: str = "change-this-ocr-callback-secret"

    class Config:
        env_file = ".env"


settings = Settings()

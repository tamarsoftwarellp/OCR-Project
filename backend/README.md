# Claim OCR Backend

FastAPI service that owns claims, uploads, OCR dispatch, and persistence of extracted document data in MongoDB.

## Module Overview

- Creates claim records from uploaded PDFs.
- Uploads files to Cloudinary when the backend receives the file directly.
- Dispatches OCR jobs to the engine API.
- Receives OCR callbacks and stores the raw document payloads in MongoDB.
- Serves claim and document data to the frontend review desk.

## Tech Stack

- FastAPI
- Motor / MongoDB
- Cloudinary
- Pydantic
- Uvicorn

## Folder Structure

```text
backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── utils.py
│   ├── models/
│   ├── routers/
│   └── services/
├── requirements.txt
├── .env.example
└── README.md
```

## Prerequisites

- Python 3.10+ recommended
- MongoDB running locally or in the cloud
- Cloudinary credentials
- Engine API reachable from the backend

## Environment Variables

Use `backend/.env.example` as the source of truth.

- `MONGO_URI`
- `MONGO_DB_NAME`
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`
- `OCR_ENGINE_URL`
- `BACKEND_PUBLIC_URL`
- `APP_NAME`
- `ENV`
- `CORS_ORIGINS`

## Installation

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Fill in `.env` before starting the server.

## Local Run Commands

```bash
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` for Swagger UI.

## Build Commands

- None. This module is a Python API service.

## API Endpoints

### Claims

- `POST /claims/upload`
- `POST /claims`
- `GET /claims`
- `GET /claims/{claim_id}`
- `PATCH /claims/{claim_id}/status`
- `DELETE /claims/{claim_id}`

### Documents

- `GET /claims/{claim_id}/documents`
- `POST /claims/{claim_id}/documents`
- `POST /claims/{claim_id}/documents/bulk`
- `POST|PATCH /claims/{claim_id}/documents/callback`
- `GET /claims/{claim_id}/documents/{document_type}`
- `PATCH /claims/{claim_id}/documents/{document_type}/entities`

### Uploads

- `GET /uploads/cloudinary-signature`
- `POST /uploads/pdf`

### Health

- `GET /health`

## Processing Flow

1. The frontend uploads a PDF to `POST /claims/upload`.
2. The backend sends the file to Cloudinary and creates a MongoDB claim record.
3. The backend dispatches a job to the engine API at `OCR_ENGINE_URL` using `POST /ocr/process`.
4. The engine runs the OCR pipeline and posts the final payload back to the backend callback URL.
5. The backend stores each extracted sub-document in MongoDB and derives summary fields at read time.
6. The frontend reads `GET /claims/{claim_id}` and patches individual extracted entities during review.

## Troubleshooting

- MongoDB connection issues usually mean `MONGO_URI` is wrong or MongoDB is not running.
- Cloudinary upload failures usually mean one of the Cloudinary credentials is missing.
- If OCR jobs never start, confirm `OCR_ENGINE_URL` points to the engine API and the engine is running.
- If callback updates do not arrive, confirm `BACKEND_PUBLIC_URL` is reachable from the engine host.
- If CORS blocks the browser, update `CORS_ORIGINS` for the deployment environment.

## Developer Notes

- The backend stores raw OCR payloads as-is so the frontend can re-render them without losing fidelity.
- Dynamic entity keys are intentional and should not be normalized into fixed SQL-style columns.
- Claim summary fields are derived from document data at read time.
- Keep secrets in `.env`, not in the repository.


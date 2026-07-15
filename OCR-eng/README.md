# Claim OCR Engine

The engine module is the OCR processing side of the system. It converts uploaded PDFs into page images, runs extraction and classification, builds structured JSON artifacts, and posts the final payload back to the backend.

## Module Overview

- `api.py` exposes a small FastAPI launcher for starting OCR jobs.
- `main.py` runs the full OCR pipeline and writes intermediate and final artifacts to disk.
- `project/` contains configuration, LLM client code, and pipeline helpers.
- `OCR_Extraction_folder/` contains the OCR, layout, merge, and extraction implementation.
- `RESULT/` is the generated output tree for OCR runs.

## Tech Stack

- Python
- FastAPI
- Uvicorn
- Groq client
- OpenCV
- pdf2image
- OCR and document processing libraries from `requirements.txt`

## Folder Structure

```text
engine/
├── api.py
├── main.py
├── project/
├── OCR_Extraction_folder/
├── requirements.txt
├── .env.example
└── RESULT/
```

## Prerequisites

- Python 3.10+ recommended
- A valid `GROQ_API_KEY`
- Backend API running and reachable from the engine for callbacks
- System dependencies required by `pdf2image` and the OCR stack

## Environment Variables

Use `engine/.env.example` as the starting point.

- `GROQ_API_KEY` - required for the LLM stage
- `OCR_PDF_PATH` - local PDF input path used by the batch pipeline
- `OCR_CALLBACK_URL` - backend callback URL for the final payload
- `OCR_CALLBACK_METHOD` - callback method, defaults to `PATCH`
- `OCR_CLAIM_ID` - claim identifier propagated into the result tree
- `OCR_DOCUMENT_ID` - document identifier propagated into the result tree
- `OCR_DOCUMENT_TYPE` - document type for the current OCR run
- `OCR_FILE_URL` - source file URL copied into the payload
- `OCR_MIME_TYPE` - source MIME type copied into the payload
- `OCR_MAX_PAGES` or `MAX_PDF_PAGES` - optional page cap for test runs
- `OCR_RESULT_ROOT` - custom output root, defaults to `RESULT`
- `OCR_RUN_ID` - run identifier used in the output tree

## Installation

```bash
cd engine
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Local Run Commands

Start the launcher API:

```bash
uvicorn api:app --reload --port 8001
```

Run the batch pipeline directly:

```bash
python main.py
```

## Build Commands

- None. This module is a Python service and pipeline.

## OCR Flow

1. The backend calls `POST /ocr/process` with claim, document, file, and callback metadata.
2. `api.py` starts `main.py` in a subprocess and injects the request metadata as environment variables.
3. `main.py` converts the PDF into pages, preprocesses images, runs layout detection, OCR, classification, and LLM extraction.
4. Intermediate files are written under `RESULT/<claim_or_document>/<run_id>/`.
5. The final payload includes `raw_ocr_response`, `structured_ocr_data`, `mapped_fields`, warnings, page counts, and status metadata.
6. The engine posts the payload back to the backend callback endpoint.

## Output Layout

The batch pipeline writes a staged directory tree similar to:

- `01_images/`
- `02_enhanced/`
- `03_layout/`
- `04_regions/`
- `05_ocr/`
- `06_document_classification/`
- `08_merged_documents/`
- `09_llm_json/`
- `final_output.json`
- `final_payload.json`

## Troubleshooting

- If the pipeline exits immediately, confirm `GROQ_API_KEY` is set.
- If PDF conversion fails, verify the Poppler/pdf2image prerequisites for your OS.
- If the backend never receives a callback, check `OCR_CALLBACK_URL`, `BACKEND_PUBLIC_URL`, and network reachability between the services.
- If results are missing, inspect `RESULT/` and `logs/llm_parser.log` for the failing stage.
- For test runs, set `OCR_MAX_PAGES` or `MAX_PDF_PAGES` to keep output small.

## Developer Notes

- Keep generated output out of version control.
- The engine is intentionally verbose so OCR runs can be debugged from the console and the result tree.
- `main.py` is the authoritative pipeline entrypoint; `api.py` only launches it.
- Do not hardcode secrets in the engine source. Use environment variables only.


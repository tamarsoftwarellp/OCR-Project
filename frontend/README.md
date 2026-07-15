# Claim OCR Frontend

React + Vite review desk for claim intake, processing visibility, and document-level OCR correction.

## Module Overview

- Upload a claim PDF and optional file/reference number.
- Track claim processing progress and document-level OCR status.
- Review extracted entities and tables.
- Update claim status during manual review.

## Tech Stack

- React 19
- Vite
- React Router
- Tailwind CSS v4
- axios
- lucide-react

## Folder Structure

```text
frontend/
├── src/
│   ├── api/
│   ├── components/
│   ├── pages/
│   ├── App.jsx
│   ├── main.jsx
│   └── index.css
├── package.json
├── vite.config.js
├── postcss.config.js
└── README.md
```

## Prerequisites

- Node.js 18+ recommended
- Backend API running

## Environment Variables

- No build-time environment variables are required by default.
- The backend base URL is stored in browser `localStorage` under `claim_ocr_api_base_url`.
- Use the settings modal in the UI to point the app at a different backend host.

## Installation

```bash
cd frontend
npm install
```

## Local Run Commands

```bash
npm run dev
```

Open the Vite dev server URL shown in the terminal.

## Build Commands

```bash
npm run build
npm run preview
```

## Routes

- `/` - upload claim PDF
- `/status` and `/status/:claimId` - track processing
- `/claims` - case register
- `/claims/:claimId` - document-wise review

## API Integration

- `POST /claims/upload` uploads the PDF and creates the claim.
- `GET /claims/{claim_id}` loads claim and document details.
- `GET /claims` populates the case register.
- `PATCH /claims/{claim_id}/status` updates the claim workflow status.
- `PATCH /claims/{claim_id}/documents/{document_type}/entities` persists edited fields.
- `GET /health` is used by the settings modal to test connectivity.

## OCR / Review Flow

1. Upload a PDF from the home page.
2. The frontend sends the file to the backend upload endpoint.
3. The status page polls the claim every 3 seconds until the backend reports a terminal state.
4. The document review page renders one tab per extracted document.
5. Edited entities are saved field-by-field through the backend API.

## Troubleshooting

- If the app cannot reach the API, open the settings modal and update the base URL.
- If upload progress stays at zero, confirm the backend is reachable and accepts multipart uploads.
- If routes load blank, make sure the Vite dev server and React Router are both running from `frontend/`.
- If styles look broken, re-run `npm install` to restore the Tailwind and Vite toolchain.

## Developer Notes

- The app is intentionally configurable at runtime so the backend host can change without rebuilding.
- Review edits are kept in a local draft state until the user clicks save.
- Keep the API contract in `src/api/client.js` synchronized with backend route changes.

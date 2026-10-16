# LandGuard BD — Smart Land Deed Verification (MVP)

A bilingual (English + বাংলা) web prototype for the LandTech 2026 P2 — Deed & Ownership Verification challenge. It compares user-entered deed fields against fictional records, records a SHA-256 fingerprint of the uploaded file, and creates a PDF report.

> **Important:** This is a prototype with synthetic/demo data. It is not a government service, is not connected to official land records, and must not be used for legal, lending, or ownership decisions. A field match does not prove authenticity or ownership. Missing records do not prove fraud. The current MVP does not run OCR; the extracted-field form is user-reviewed/manual. Identity checks are explicitly not connected and no biometric data is collected.

## Included
- React + Vite responsive dashboard and verification workflow.
- Full interface language toggle: English / বাংলা, persisted in browser storage.
- FastAPI backend, SQLAlchemy models, JWT login, password hashing, upload signature checks, SHA-256, verification history, audit log, and PDF reports.
- Seeded synthetic reference data: 25 fictional deeds, 50 fictional people, one fictional office, parcel records and simulated mutation references.
- SQLite default for easy local startup; MySQL configurable with `DATABASE_URL`.

## Requirements
- Windows 10/11
- Python 3.11+ recommended (Python 3.14 may have dependency compatibility issues; use Python 3.12 if installation errors occur)
- Node.js 20+ and npm
- Optional: MySQL 8 if you want to use MySQL rather than SQLite

## Run on Windows
Open two terminals.

### 1. Backend
```powershell
cd LandGuardBD\backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```
If PowerShell blocks activation, run this for the current terminal only: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate again.

API docs: http://127.0.0.1:8000/docs
Health: http://127.0.0.1:8000/api/v1/health

### 2. Frontend
```powershell
cd LandGuardBD\frontend
npm install
npm run dev
```
Open http://localhost:5173

### Demo login
- Username: `admin`
- Password: `LandGuard123!`

Change the demo password and `SECRET_KEY` before any shared environment. This code is not production-hardened.

## Switch to MySQL
1. Create the database using a MySQL client:
```sql
CREATE DATABASE landguard_bd CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'landguard_user'@'localhost' IDENTIFIED BY 'change_me';
GRANT ALL PRIVILEGES ON landguard_bd.* TO 'landguard_user'@'localhost';
FLUSH PRIVILEGES;
```
2. Edit `backend/.env`:
```env
DATABASE_URL=mysql+pymysql://landguard_user:change_me@localhost:3306/landguard_bd?charset=utf8mb4
SECRET_KEY=replace-with-a-long-random-secret
UPLOAD_DIR=./private_uploads
MAX_UPLOAD_MB=10
```
3. Restart the backend. Tables and seed records are created at startup. The demo seed is idempotent.

## Test the workflow
1. Sign in using the demo login.
2. Open **Verify a deed**.
3. Select a local JPG, PNG or PDF test document (do not use real citizens' documents).
4. Keep the prefilled fields and click **Run verification**. For a matching test, the selected file must be a valid image/PDF and deed number `DEMO-2024-001` should have the other prefilled fields unchanged.
5. Change `D-301` to `D-999` to trigger a mismatch. Change the deed number to `FAKE-000` to get `UNVERIFIABLE`.
6. Download the PDF report, then view **Verification history** and **Audit log**.

A valid file is required; create a harmless test image/PDF for the upload test. The verification field values are editable so you can demonstrate mismatch cases without OCR.

## API endpoints
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/register`
- `GET /api/v1/dashboard/stats`
- `POST /api/v1/verifications` (multipart `file`, `fields_json`)
- `GET /api/v1/verifications`
- `GET /api/v1/verifications/{id}`
- `GET /api/v1/verifications/{id}/checks`
- `GET /api/v1/verifications/{id}/report`
- `GET /api/v1/records/search?q=...`
- `GET /api/v1/deeds/{id}`
- `GET /api/v1/mutations`
- `GET /api/v1/audit-logs`

## Project map
- `frontend/` — React + Vite interface
- `backend/app/` — FastAPI, SQLAlchemy models, auth, seed and verification workflow
- `database/schema.sql` — MySQL schema overview / starter tables
- `tests/` — API smoke-test notes
- `docs/` — architecture and limitation notes

## Current MVP limitations / next steps
- OCR is not yet integrated; fields are entered or corrected manually.
- File hash is generated and reported but no trusted reference hash is provisioned by default, so the report does not claim a hash match.
- RBAC has roles in the user model, but fine-grained role-specific permissions and admin user management need to be completed before any shared deployment.
- QR-signed reports, Alembic migrations, full automated test coverage, official-source adapter implementation, and production security review are not yet implemented.
- PDF report text uses ASCII-safe fallback in this MVP; Bangla PDF font embedding should be added for full Bangla report support.
- No live government portal scraping or system access is implemented.

## AI use disclosure
AI assistance was used to scaffold and review parts of the code, documentation, and user interface. The project team must review, test, understand, and disclose AI-generated contributions according to the LandTech 2026 rulebook. All seeded records in this project are synthetic.

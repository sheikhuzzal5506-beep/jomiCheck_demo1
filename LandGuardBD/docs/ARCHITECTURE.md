# Architecture

```text
Browser (React + Vite)
  ├── English / বাংলা UI
  ├── Upload and manually review deed fields
  └── Dashboard / reference records / history / report
            │ HTTP JSON + multipart upload
            ▼
FastAPI (`backend/app/main.py`)
  ├── Login + JWT token
  ├── Upload validation + SHA-256 digest
  ├── Field comparison against synthetic reference records
  ├── PDF report generation
  └── Audit event creation
            │ SQLAlchemy
            ▼
SQLite by default / MySQL when configured
```

## Verification semantics
- `MATCHED`: all supplied comparable fields match a found synthetic deed.
- `MISMATCH_FOUND`: one or more supplied fields conflict with a found synthetic deed.
- `REVIEW_REQUIRED`: a deed reference is found but no comparable fields were supplied.
- `UNVERIFIABLE`: no matching synthetic deed number exists.
- Field comparison, file hash, identity checks and legal ownership are separate concepts. The current version computes a SHA-256 digest but has no trusted reference hash by default; identity is not checked.

## Security boundaries
The backend limits uploads by extension MIME and file signature, uses generated private filenames, and stores uploads under a private local folder. Configure a strong secret and use HTTPS, access controls, malware scanning, retention policies, secret management, and a security review before shared deployment. The demo login is for local presentation only.

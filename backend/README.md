# ZeroTrace Authoritative FastAPI Backend

The **ZeroTrace Authoritative Backend** is the single source of truth and cryptographic trust authority for device wipe evidence validation, digital certificate generation & signing, Supabase record persistence, and public verification.

---

## 1. Revised Architecture & Responsibilities

```
 ┌──────────────────────┐
 │  Desktop App (PyQt5) │  - Device wiping & sanitization execution
 │                      │  - Local verification hash calculation
 └──────────┬───────────┘  - Submits raw wipe evidence over HTTPS
            │
            ▼ POST /api/v1/evidence/submit
 ┌──────────────────────┐
 │   FastAPI Backend    │  - Sole authority for auth & authorization
 │                      │  - Media-aware policy validation (Purge vs Clear)
 │                      │  - Private key custody (SIGNING_PRIVATE_KEY_PEM)
 │                      │  - Authoritative ECDSA-SHA256 signing
 │                      │  - ReportLab PDF generation with QR & embedded token
 └─────┬──────────┬─────┘  - Durable, idempotent submission tracking
       │          │
       ▼          ▼
 ┌──────────┐   ┌───────────────────────────┐
 │ Supabase │   │ React Web Portal / Public │
 │ Postgres │   │  - Certificate browser    │
 │ Storage  │   │  - Public dual-anchor     │
 └──────────┘   │    PDF & Hash verifier    │
                └───────────────────────────┘
```

- **Desktop App (PyQt5):** Responsible *only* for device wiping and submitting wipe evidence to the backend over HTTPS. It never issues authoritative production certificates and never holds the authoritative private key.
- **FastAPI Backend:** Sole authority for validating wipe evidence, signing certificates using ECDSA P-256, writing to Supabase, and performing dual-anchor verification.
- **Supabase:** PostgreSQL database storing certificates, wipe submissions, revocation audit trails, and user profiles. Supabase Storage holds authoritative signed certificate PDFs. Privileged writes are restricted to backend service keys.
- **React Web Portal & Public Clients:** Authenticated users manage their certificates and accounts; public visitors verify PDF certificates and verification hashes anonymously.

---

## 2. Security & Trust Model

1. **Private Key Isolation:**
   - The ECDSA private key (`SIGNING_PRIVATE_KEY_PEM`) exists **exclusively** on the FastAPI backend in `backend/.env`.
   - The client never submits pre-signed certificates for the backend to ingest; the backend construct the canonical payload and signs it server-side.
2. **Dual-Anchor Public Verification:**
   - **Database consistency alone is never sufficient** to return `Verified`.
   - The verifier validates:
     1. `cryptographic_authenticity_ecdsa`: Authoritative ECDSA-SHA256 signature against pinned public key.
     2. `database_consistency`: Registered in PostgreSQL database with matching hash and cert ID.
     3. `revocation_status`: Status is active, not revoked.
     4. `issuer_account_status`: Status of the issuing user account (active, deactivated, or deleted).
3. **Idempotency & Replay Protection:**
   - Evidence submissions accept or generate a unique `idempotency_key`.
   - Re-submitting the same wipe evidence returns the existing signed certificate record without re-signing or creating duplicate database rows.
4. **Media-Aware Sanitization Policy (NIST SP 800-88 Rev. 1):**
   - **Purge:** Firmware-level commands (NVMe Sanitize, ATA Secure Erase, Crypto Scramble) on supported media without unrecovered errors.
   - **Clear:** Multi-pass overwrite (DoD 5220.22-M, NIST Clear) or hardware sanitize fallback to overwrite.
   - **Inconclusive/Failed:** Zero bytes wiped, drive I/O errors, or corrupted completion hash. Certificate issuance is rejected with HTTP 422.
5. **Non-Destructive Account Deletion:**
   - Account deletion marks the user profile as `status = 'deleted'`.
   - Historical sanitization certificates remain preserved for compliance and auditability.

---

## 3. Directory Layout

```
backend/
├── app/
│   ├── api/v1/
│   │   ├── auth.py             # User profile, deactivation, and soft-deletion
│   │   ├── certificates.py     # Certificate listing, detail, PDF download, and revocation
│   │   ├── health.py           # Health check endpoint
│   │   ├── verification.py     # Public rate-limited PDF/JSON upload & hash verification
│   │   └── wipe_evidence.py    # Authoritative evidence submission & signing
│   ├── core/
│   │   ├── config.py           # Settings loaded via pydantic-settings
│   │   ├── errors.py           # Standardized exceptions and HTTP error handlers
│   │   └── security.py         # Supabase JWT validation & sliding-window rate limiting
│   ├── schemas/
│   │   ├── auth.py             # User account & deletion schemas
│   │   ├── certificate.py      # Canonical certificate, revocation, and verification models
│   │   └── evidence.py         # Device & wipe execution evidence schemas
│   ├── services/
│   │   ├── crypto_service.py   # Canonicalization, SHA-256, and ECDSA P-256 signing/verifying
│   │   ├── evidence_validator.py # Media-aware policy validator (Purge vs Clear vs Inconclusive)
│   │   ├── pdf_service.py      # ReportLab generator with QR code & machine payload extraction
│   │   └── supabase_service.py # Privileged PostgreSQL operations and Supabase Storage uploads
│   └── main.py                 # FastAPI application, CORS, routers, and lifecycle
├── migrations/
│   └── schema_additions.sql   # SQL for wipe_submissions, revocation logs, and user status
├── tests/
│   ├── conftest.py             # Pytest fixtures and test clients
│   ├── test_crypto_service.py  # Unit tests for ECDSA and canonical hashing
│   ├── test_endpoints.py       # Integration tests for routes, idempotency, and verification
│   ├── test_evidence_validator.py # Tests for Purge, Clear, and failure rejection
│   └── test_pdf_service.py     # Tests for PDF generation and payload extraction
├── .env.example
├── .env
├── requirements.txt
└── README.md
```

---

## 4. Environment Variables

Create a `backend/.env` file (copied from `backend/.env.example`):

```bash
# Supabase Configuration
SUPABASE_URL=https://<your-project-id>.supabase.co
SUPABASE_KEY=<anon-key>
SUPABASE_SERVICE_KEY=<service-role-key>

# Server Configuration
ENVIRONMENT=development
PORT=8000
HOST=0.0.0.0
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","http://127.0.0.1:3000","http://127.0.0.1:5173"]

# Cryptographic Keys (ECDSA P-256)
SIGNING_PRIVATE_KEY_PEM="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
SIGNING_PUBLIC_KEY_PEM="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"

# Storage Bucket Name
SUPABASE_STORAGE_BUCKET=certificates
```

---

## 5. Quickstart & Running Locally

### Installation
```bash
cd backend
pip install -r requirements.txt
```

### Running the Server
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

The interactive API documentation is available at:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

### Running Automated Tests
```bash
python -m pytest backend/tests -v
```

---

## 6. API Reference

### 6.1 Submit Wipe Evidence
`POST /api/v1/evidence/submit`

**Headers:**
- `Authorization: Bearer <supabase_jwt_token>` (optional for standalone execution, required for user-bound certificates)

**Request Body:**
```json
{
  "idempotency_key": "IDEMP-drive1-20261027T1000",
  "device": {
    "device_id": "\\\\.\\PhysicalDrive1",
    "device_name": "Samsung SSD 980",
    "device_model": "Samsung SSD 980 500GB",
    "device_serial": "S56XNX0R123456",
    "total_bytes": 500107862016,
    "sector_size": 512,
    "media_type": "NVMe"
  },
  "execution": {
    "wipe_method": "NVMe Sanitize",
    "passes": 1,
    "bytes_wiped": 500107862016,
    "sectors_wiped": 976773168,
    "completion_hash": "668eeb95e40e3ac6cc0fef16aff39b4bc8e6ef8e6fe673b9b3b59e6800f41ab9",
    "hardware_sanitization_used": true,
    "fallback_occurred": false,
    "errors": [],
    "wipe_start_time": "2026-10-27T10:00:00Z",
    "wipe_end_time": "2026-10-27T10:14:32Z"
  },
  "operator_notes": "Decommissioning lab server storage."
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "idempotent_replay": false,
  "cert_id": "CERT-C8D71203A49F21B6",
  "sanitization_level": "Purge",
  "verification_hash": "668eeb95e40e3ac6cc0fef16aff39b4bc8e6ef8e6fe673b9b3b59e6800f41ab9",
  "signature": "MEYCIQDx...",
  "download_url": "https://<supabase-url>/storage/v1/object/public/certificates/<user_id>/CERT-C8D71203A49F21B6.pdf",
  "certificate": { ... }
}
```

---

### 6.2 Public Verification

#### A. File Upload (PDF or JSON)
`POST /api/v1/verify/pdf`

**Multipart Form:**
- `file`: PDF or JSON certificate file.

**Response (200 OK):**
```json
{
  "success": true,
  "final_verdict": "Verified",
  "verdict_explanation": "Authentic ZeroTrace Certificate. Valid cryptographic signature, active registry record, and active issuer account.",
  "cryptographic_authenticity": true,
  "registry_recognition": true,
  "revocation_status": "active",
  "issuer_account_status": "active",
  "checks": [
    {
      "check": "cryptographic_authenticity_ecdsa",
      "passed": true,
      "description": "ECDSA-SHA256 digital signature validation against authoritative public key",
      "details": { "reason": "ok" }
    },
    {
      "check": "database_consistency",
      "passed": true,
      "description": "Authoritative database registry record consistency",
      "details": { "found": true, "cert_id": "CERT-C8D71203A49F21B6" }
    },
    {
      "check": "revocation_status",
      "passed": true,
      "description": "Certificate validity and revocation state check",
      "details": { "status": "active" }
    },
    {
      "check": "issuer_account_status",
      "passed": true,
      "description": "Status of the account that issued this sanitization certificate",
      "details": { "account_status": "active" }
    }
  ],
  "certificate": { ... }
}
```

#### B. Hash & Signature Lookup
`POST /api/v1/verify/hash`

**Request Body:**
```json
{
  "hash": "668eeb95e40e3ac6cc0fef16aff39b4bc8e6ef8e6fe673b9b3b59e6800f41ab9",
  "signature": "MEYCIQDx...",
  "cert_id": "CERT-C8D71203A49F21B6"
}
```

---

### 6.3 Certificate Management & Revocation

- `GET /api/v1/certificates` (List authenticated user's certificates)
- `GET /api/v1/certificates/{cert_id}` (Retrieve certificate details)
- `GET /api/v1/certificates/{cert_id}/download` (Download signed PDF)
- `POST /api/v1/certificates/{cert_id}/revoke` (Auditable revocation)
  ```json
  {
    "reason": "Hardware drive returned to manufacturer under RMA warranty."
  }
  ```

---

### 6.4 Account Status & Non-Destructive Deletion

- `GET /api/v1/auth/me` (Retrieve user profile & account status)
- `PATCH /api/v1/auth/account/status` (Toggle `active` or `deactivated`)
- `POST /api/v1/auth/account/delete` (Soft-delete user while preserving certificates)
  ```json
  {
    "confirmation": "DELETE MY ACCOUNT"
  }
  ```

---

## 7. Phased Client Integration Guides

### PyQt5 Desktop App Integration
In the next phase of migration:
1. After completing local drive sanitization, the desktop app constructs the `WipeEvidenceSubmission` payload containing hardware details, overwrite passes, completion hash, and timestamps.
2. The desktop app calls `POST https://api.zerotrace.org/api/v1/evidence/submit` with `Authorization: Bearer <user_token>`.
3. The desktop app receives the signed certificate metadata and PDF download link.
4. The private key remains absent from client binaries.

### React Web Portal Integration
In the next phase of migration:
1. Update `REACT_APP_API_URL` to point to `http://localhost:8000/api/v1` (or production backend URL).
2. Public verification calls `/api/v1/verify/pdf` and `/api/v1/verify/hash` to display the 4-part trust status.
3. Dashboard fetches certificates via `/api/v1/certificates`.

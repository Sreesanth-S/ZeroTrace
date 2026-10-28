# ZeroTrace

ZeroTrace is an enterprise-grade, verifiable data sanitization and certificate issuance system designed for Windows storage devices. It enables operators to securely erase hard disk drives (HDDs), solid-state drives (SSDs), NVMe drives, and USB flash drives, performing read-back verification and generating cryptographically signed (ECDSA P-256) tamper-proof PDF certificates. 

The architecture features a native **PyQt5 Windows Desktop Application** for drive wiping, an authoritative **FastAPI Backend** as the sole signing and validation authority, a **React (Vite) Web Portal** for public verification and audit dashboards, and an authoritative **Supabase PostgreSQL & Private Storage** backend.

---

## Overview

ZeroTrace solves the problem of proving that storage media has been irreversibly erased prior to decommissioning, recycling, or resale:

1. **Physical Drive Wiping**: Operates with elevated Administrator privileges on Windows, discovering physical drives via WMI and Win32 low-level handles (`\\.\PhysicalDriveX`).
2. **Hidden Sector Sanitization**: Detects and un-hides Host Protected Area (HPA) and Device Configuration Overlay (DCO) sectors via ATA `IDENTIFY DEVICE` and `SET MAX ADDRESS`, ensuring zero hidden remnants.
3. **Multi-Pass Algorithms**: Supports Quick Wipe (1-pass zeros), DoD 5220.22-M (3-pass & 7-pass), and hardware controller-level commands (NVMe Sanitize / ATA Secure Erase) with automatic software fallback.
4. **Post-Wipe Verification**: Samples 64 evenly distributed blocks across the storage volume, computing canonical SHA-256 completion hashes.
5. **Backend-Authoritative Signing**: Evidence is submitted to the FastAPI backend, which validates the sanitization outcome (classifying assurance level as **Purge** or **Clear** according to NIST SP 800-88 Rev. 1), signs the certificate with ECDSA P-256, and generates a tamper-evident PDF with an embedded cryptographic payload.
6. **Dual-Anchor Public Verification**: Anyone can upload a certificate PDF to the web portal to independently verify its mathematical authenticity against the authoritative key and check its active/revoked status against the registry.

---

## Architecture

```mermaid
flowchart TD
    subgraph DesktopApp["Windows Desktop Application (PyQt5)"]
        UI["Main Window & Progress Dialogs"]
        WE["Wipe Engine (Win32 / WMI / HPA)"]
        JNL["Crash-Safe Journal (wipe_journal.json)"]
        FBC["FastAPI Backend Client"]
        PEN["Pending Submissions Offline Cache"]
    end

    subgraph FastApiBackend["Authoritative FastAPI Backend (Port 8000)"]
        AUTH_ROUTER["/api/v1/auth (Login / Register / Account Deletion)"]
        EVID_ROUTER["/api/v1/evidence (Evidence Validation & Classification)"]
        CERT_ROUTER["/api/v1/certificates (List / Download PDF / Revoke)"]
        VERIF_ROUTER["/api/v1/verify (Dual-Anchor Verification Policy)"]
        VALIDATOR["Media-Aware Policy Validator (NIST 800-88)"]
        SIGNER["Cryptographic Signer (ECDSA P-256 Private Key)"]
        PDF_SVC["PDF Generator (ReportLab / Embedded Machine Token)"]
    end

    subgraph WebPortal["React Web Portal (Vite, Port 5173)"]
        FE_DASH["Operator Dashboard (Certificates List / PDF Download)"]
        FE_VERIF["Public Verification Portal (Dual-Anchor PDF Inspection)"]
    end

    subgraph Supabase["Supabase Cloud Infrastructure"]
        AUTH_DB["Supabase Auth (Operators)"]
        POSTGRES[("Authoritative DB (certificates & user_profiles)")]
        STORAGE["Private Storage Bucket (certificates/*.pdf)"]
    end

    UI --> WE
    WE --> JNL
    WE --> FBC
    FBC -- "Network Failure Fallback" --> PEN
    PEN -. "Retry on Reconnection" .-> FBC
    FBC -- "HTTPS / JWT" --> FastApiBackend

    FE_DASH -- "HTTPS / Supabase Auth" --> Supabase
    FE_DASH -- "HTTPS / JWT" --> FastApiBackend
    FE_VERIF -- "In-Memory PDF Verification" --> FastApiBackend

    FastApiBackend --> VALIDATOR
    FastApiBackend --> SIGNER
    FastApiBackend --> PDF_SVC
    FastApiBackend -- "Privileged Service Key (Sole Write Authority)" --> POSTGRES
    FastApiBackend -- "Upload Signed PDF (application/pdf)" --> STORAGE
    FastApiBackend --> AUTH_DB
```

---

## Key Features

### 1. Drive Detection & Sanitization Engine
* **Physical Drive Enumeration**: Discovers HDDs, SATA SSDs, NVMe SSDs, and USB storage devices via WMI (`Win32_DiskDrive`, `Win32_DiskPartition`, `Win32_LogicalDisk`) and low-level Win32 `CreateFile` calls.
* **HPA & DCO Detection**: Queries ATA IDENTIFY DEVICE sector limits to detect hidden drive capacity, temporarily exposes hidden sectors via `SET MAX ADDRESS` (ATA opcode `0xF9`), wipes the hidden region, and restores original boundaries.
* **Software Overwrite Patterns**:
  * **Quick Wipe**: 1-pass single zero fill (`0x00`).
  * **DoD 5220.22-M (3-Pass)**: Sequential passes of zeros (`0x00`), ones (`0xFF`), and cryptographically pseudo-random bytes.
  * **DoD 5220.22-M (7-Pass)**: Seven sequential alternating passes.
* **Hardware Erase & Automatic Fallback**: Issues pass-through low-level command structures for ATA Secure Erase (`IOCTL_ATA_PASS_THROUGH_DIRECT`) and NVMe Sanitize (`IOCTL_STORAGE_PROTOCOL_COMMAND`). If the hardware controller reports frozen state, timeout, or failure, the engine automatically catches the error, downgrades to software DoD 3-Pass overwrite, and accurately records the fallback.
* **Post-Wipe Sampling**: Reads 64 evenly spaced 1 MB blocks across the storage volume post-wipe, generating a SHA-256 completion hash.
* **Automatic Re-Initialization & Formatting**: Dismounts existing logical volumes before wiping and re-initializes/formats the drive after sanitization using native PowerShell storage cmdlets (`Clear-Disk`, `Initialize-Disk`, `New-Partition`, `Format-Volume`) with a `diskpart` script fallback.
* **Crash-Safe Recovery Journal**: Maintains an active `wipe_journal.json` log on disk to track progress, drive parameters, and status during execution.

### 2. FastAPI Authoritative Backend
* **Sole Authority for Signing & Storage**: Client apps have zero write permissions to the database or storage. Only the FastAPI backend issues, signs, records, and stores certificates using the Supabase `service_role` key.
* **Media-Aware Validation Policy**: Classifies sanitization assurance according to NIST SP 800-88 Rev. 1:
  * **Purge**: Hardware sanitize / cryptographic erase on SSD/NVMe, or certified ATA Secure Erase.
  * **Clear**: Multi-pass or single-pass overwrites on HDDs and SSDs.
* **Idempotency & Replay Protection**: Deterministic idempotency keys prevent duplicate records from re-wipes or network retries.
* **Auditable Revocation**: Operators can revoke compromised or recalled certificates with recorded timestamp, user ID, client IP, and justification.
* **Historical Certificate Preservation**: Upon operator account deletion, foreign keys set `user_id = NULL`, ensuring issued audit certificates remain permanently valid and verifiable.

### 3. Dual-Anchor Public Verification
When a certificate PDF is uploaded to `/api/v1/verify/pdf`:
* **Zero Storage Footprint**: Uploaded verification PDFs are processed strictly **in-memory** in RAM and never written to disk or uploaded to cloud storage.
* **Visual Tamper Detection**: Extracts visible page text and compares it against the signed machine payload (`BEGIN_ZEROTRACE_PAYLOAD`). Any unauthorized PDF edits (tampered serial numbers, capacity, or hashes) trigger a `tampered_pdf_text_mismatch` flag.
* **Cryptographic Verification**: Recomputes canonical SHA-256 hashes and verifies the ECDSA signature against the authoritative public key (`NIST P-256`).
* **Registry Recognition**: Verifies that the certificate ID and hash exist in Supabase and confirms whether the certificate is active or revoked.

### 4. React (Vite) Web Portal
* **Public Verification Portal**: Drag-and-drop PDF upload or direct 64-character hash lookup with detailed audit reports.
* **Compliance Dashboard**: Authenticated operator portal to view issued certificates, download signed PDFs, and view sanitization levels (**Purge** / **Clear**).

---

## Project Structure

```text
ZeroTrace/
├── backend/                       # Authoritative FastAPI Backend
│   ├── app/
│   │   ├── api/v1/                # API Routers (auth, evidence, certificates, verification)
│   │   ├── core/                  # Configuration, security, errors
│   │   ├── schemas/               # Pydantic models (evidence, certificate, auth)
│   │   ├── services/              # Crypto service, PDF service, Supabase service, validator
│   │   └── main.py                # FastAPI entry point
│   ├── requirements.txt           # Backend dependencies (fastapi, uvicorn, pycryptodome, pypdf)
│   └── tests/                     # Backend pytest suite
├── desktop_app/                   # PyQt5 Desktop Application
│   ├── assets/                    # Icons and graphical assets
│   ├── application.py             # QApplication wrapper and lifecycle management
│   ├── backend_client.py          # FastApiBackendClient (evidence submit, PDF download, retry)
│   ├── dialogs.py                 # Login, certificate viewer, and confirmation dialogs
│   ├── main.py                    # Application entry point with UAC elevation check
│   ├── main_window.py             # Main GUI layout, drive table, live wipe controls
│   ├── requirements.txt           # Desktop dependencies (PyQt5, pywin32, wmi, requests)
│   ├── wipe_engine.py             # Core sanitization engine (WMI/Win32 I/O, HPA/DCO, verification)
│   ├── wipe_thread.py             # Asynchronous QThread wipe worker
│   └── tests/                     # Desktop integration & wipe engine test suite
├── frontend/                      # React (Vite) Web Portal
│   ├── src/
│   │   ├── lib/                   # Supabase client initializers
│   │   ├── App.jsx                # Main React app (Dashboard, Verification, Auth)
│   │   └── main.jsx               # React entry point
│   ├── package.json               # Frontend dependencies & build scripts
│   └── vite.config.js             # Vite configuration
├── supabase_config/               # Database Configuration
│   └── schema.sql                 # Unified all-in-one schema, RLS policies, & storage setup
├── pytest.ini                     # Pytest configuration
├── .gitignore                     # Git ignore rules for Python, Node, keys, and build artifacts
└── README.md                      # Project documentation
```

---

## Installation & Setup

### Prerequisites
* **Operating System**: Windows 10 / 11 (Administrator privileges required for low-level drive writes).
* **Python**: Python 3.10+ (recommended 3.12).
* **Node.js**: Node.js 18+ and npm.
* **Supabase**: A Supabase project with PostgreSQL and Storage enabled.

---

### 1. Database Setup (Supabase)
ZeroTrace uses a single unified database setup file:
1. Open your **Supabase Dashboard** → **SQL Editor**.
2. Copy and paste the entire contents of [`supabase_config/schema.sql`](supabase_config/schema.sql).
3. Click **Run**.
*(This creates the `certificates` and `user_profiles` tables, configures RLS policies, establishes foreign keys with historical preservation, and provisions the private `certificates` storage bucket limited to `application/pdf`).*

---

### 2. FastAPI Backend Setup
1. Configure `backend/.env`:
   ```env
   ENVIRONMENT=production
   PORT=8000
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-supabase-anon-key
   SUPABASE_SERVICE_KEY=your-supabase-service-role-key
   SIGNING_PRIVATE_KEY_PEM="-----BEGIN EC PRIVATE KEY-----\n...\n-----END EC PRIVATE KEY-----"
   SIGNING_PUBLIC_KEY_PEM="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
   CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]
   ```
2. Install dependencies:
   ```cmd
   pip install -r backend/requirements.txt
   ```
3. Start the backend:
   ```cmd
   uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
4. API documentation will be available at `http://localhost:8000/docs`.

---

### 3. Desktop Application Setup & Development Run
1. Configure `desktop_app/.env`:
   ```env
   FASTAPI_BACKEND_URL=http://localhost:8000/api/v1
   SIGNING_PUBLIC_KEY_PEM="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
   ```
   *(Note: Privileged private keys and service role keys are strictly omitted from the desktop app).*
2. Install dependencies:
   ```cmd
   pip install -r desktop_app/requirements.txt
   ```
3. Launch in development mode from an elevated Command Prompt or PowerShell:
   ```cmd
   python desktop_app/main.py
   ```
   *(In development, an interactive live log console tab opens behind the main application window to stream runtime debug logs).*

---

### 4. Building the Standalone Executable (`.exe`)
You can compile the PyQt5 desktop client into a self-contained, single-file Windows executable:

1. **Install PyInstaller**:
   ```cmd
   pip install pyinstaller
   ```

2. **Build with the Project Specification**:
   ```cmd
   cd desktop_app
   pyinstaller ZeroTrace.spec --clean
   ```

3. **Output Location**:
   The compiled standalone binary is placed in:
   ```text
   desktop_app/dist/ZeroTrace.exe
   ```

**What the build automatically bundles**:
* **Application Logo & Icon**: Embeds `ZeroTrace.ico` as the Windows file icon and taskbar icon.
* **Embedded Assets**: Bundles `ZeroTrace.png`, `checkmark.png`, `EULA.txt`, and runtime `.env`.
* **UAC Administrator Elevation**: Embeds `app.manifest` (`requireAdministrator`) to ensure proper physical drive access permissions.
* **Clean GUI Experience**: Built with `console=False` (Windows GUI subsystem) so that no background Command Prompt window appears for end users.

---

### 5. React Web Portal Setup
1. Navigate to the frontend directory:
   ```cmd
   cd frontend
   npm install
   ```
2. Configure `frontend/.env`:
   ```env
   VITE_SUPABASE_URL=https://your-project.supabase.co
   VITE_SUPABASE_ANON_KEY=your-supabase-anon-key
   VITE_API_URL=http://localhost:8000/api/v1
   ```
3. Start the development server or build for production:
   ```cmd
   npm run dev       # Development server at http://localhost:5173
   npm run build     # Production build to frontend/dist
   ```

---

## Running Test Suites

ZeroTrace includes an automated test suite covering cryptographic validation, evidence validation, endpoint security, and drive engine logic:

```cmd
# Run all backend and desktop integration tests (46 tests)
pytest backend/tests desktop_app/tests

# Build web frontend for production verification
cd frontend && npm run build
```

---

## Security Model Summary

| Layer | Responsibility | Security Policy |
| :--- | :--- | :--- |
| **Desktop App** | Drive I/O, Overwrite, Sampling | Requires Windows Admin UAC. No private keys stored. |
| **FastAPI Backend** | Sole Signing Authority & Validation | Holds P-256 private key. Validates NIST 800-88 sanitization. Sole writer to Supabase. |
| **Supabase DB** | Authoritative Registry | RLS enabled. Client apps have read-only access. `service_role` has write access. |
| **Storage** | Tamper-Proof Artifact Storage | Private bucket. Restricted strictly to `application/pdf`. Accessible only via authenticated backend proxy or signed URLs. |
| **Verification** | Dual-Anchor Integrity Checking | In-memory verification. Rechecks ECDSA signature against public key, tests for PDF visual tampering, and checks revocation registry. |

---

## License

All rights reserved. ZeroTrace Compliance Solutions.

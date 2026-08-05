# ZeroTrace

ZeroTrace is a secure, verifiable data sanitization and certificate issuance system designed for Windows storage devices. It enables users to safely erase hard disk drives (HDDs), solid-state drives (SSDs), NVMe drives, and USB flash drives, performing read-back verification and generating cryptographically signed (ECDSA P-256) tamper-proof PDF/JSON certificates. The system includes a native PyQt5 desktop application for drive wiping and a React/Express web portal for public certificate verification.

---

## Overview

ZeroTrace addresses the challenge of verifying that storage media has been securely wiped prior to disposal, recycling, or resale. 

The application operates on Windows with elevated Administrator privileges, detecting connected storage devices via WMI and Win32 APIs. It executes software overwrite sanitization patterns (Quick 1-Pass Zeros, DoD 5220.22-M 3-Pass, and DoD 7-Pass), un-hides and wipes Host Protected Area (HPA) and Device Configuration Overlay (DCO) sectors, performs 64-block sampling read-back verification, automatically re-initializes and formats storage volumes post-wipe, and logs operation progress into a local recovery journal.

Wipe results are compiled into digitally signed certificates containing SHA-256 verification hashes, ECDSA signatures, and embedded QR codes. Certificates can be stored locally or synchronized to a cloud database (Supabase) and verified publicly through a web application using file uploads, hash lookups, or camera-based QR code scanning.

---

## Features

### Fully Implemented

* **Windows Storage Device Detection**: Discovers HDDs, SATA SSDs, NVMe SSDs, and USB flash drives using WMI (`Win32_DiskDrive`, `Win32_DiskPartition`, `Win32_LogicalDisk`) and low-level Win32 `CreateFile` handles.
* **Host Protected Area (HPA) & DCO Detection and Sanitization**: Queries ATA IDENTIFY DEVICE sector limits to detect hidden drive capacity, temporarily exposes hidden sectors via `SET MAX ADDRESS` (ATA opcode `0xF9`), wipes the hidden region, and restores original LBA boundaries.
* **Software Multi-Pass Overwrite Sanitization**:
  * **Quick Wipe**: 1-pass single zero fill (`0x00`).
  * **DoD 5220.22-M (3-Pass)**: Sequential passes of zeros (`0x00`), ones (`0xFF`), and cryptographically pseudo-random data (`os.urandom`).
  * **DoD 5220.22-M (7-Pass)**: Seven sequential passes alternating zeros, ones, and pseudo-random patterns.
* **Read-Back Hash Verification**: Samples 64 evenly spaced 1 MB blocks across the storage volume post-wipe, computing a SHA-256 completion hash bound to device metadata and timestamp to prove physical disk state.
* **Automatic Volume Dismounting & Re-Formatting**: Dismounts existing logical volumes before wiping and re-initializes/formats the drive after sanitization using native PowerShell storage cmdlets (`Clear-Disk`, `Initialize-Disk`, `New-Partition`, `Format-Volume`) with a `diskpart` script fallback.
* **Crash & Power-Loss Recovery Journaling**: Maintains an active `wipe_journal.json` log on disk to track progress, drive parameters, and status during execution.
* **ECDSA Digital Certificate Generation**: Creates JSON certificates signed with ECDSA P-256 (FIPS 186-3) signatures via PyCryptodome (supporting local offline private keys or authenticated backend API signing).
* **PDF Certificate Compilation**: Uses ReportLab to generate printable PDF certificates with embedded metadata, compliance mapping (NIST SP 800-88 Rev 1 / IEEE 2883-2022 / DoD 5220.22-M), and generated QR codes.
* **PyQt5 Desktop Application**:
  * Mandatory Windows Administrator privilege elevation request.
  * EULA acceptance tracking saved in `QSettings`.
  * User authentication with Supabase Auth or offline local PIN fallback.
  * Interactive drive selection with system-drive protection warnings.
  * Live wipe progress monitoring, pass tracking, and status reporting.
  * Local certificate viewing and manual cloud sync controls.
* **Express.js Web Backend**:
  * Certificate verification endpoints for raw SHA-256 hashes, JSON certificate files, and PDF upload parsing (`pdf-parse` payload extraction).
  * Server-side certificate signing endpoint (`/api/certificates/sign`) with JWT authorization.
  * Security header enforcement (`helmet`), rate limiting (`express-rate-limit`), and CORS control.
* **React + Vite Verification Web Portal**:
  * Drag-and-drop PDF/JSON file verification interface.
  * Direct hash lookup input.
  * Web camera QR code scanner using `html5-qrcode`.
  * User login, registration, and user certificate list dashboard connected to Supabase Auth.
* **Database & Cloud Storage Integration**: PostgreSQL schema with Row Level Security (RLS) policies for user certificates, profiles, wipe logs, verification logs, and storage buckets for PDF/JSON artifacts.

### Partially Implemented

* **Hardware Controller-Level Erase (ATA Secure Erase & NVMe Format/Sanitize)**:
  * **Current Status: Partial Implementation with Automatic Software Fallback**
  * The codebase includes pass-through low-level command structures for ATA Security Set Password / Erase Unit (`IOCTL_ATA_PASS_THROUGH_DIRECT`) and NVMe Admin Format / Sanitize (`IOCTL_STORAGE_PROTOCOL_COMMAND`).
  * If the drive controller rejects the command, times out, or if the drive is in a frozen state, the engine catches the exception, logs a warning, flags compliance as `"Clear (Software Fallback)"`, and automatically falls back to executing a software DoD 3-Pass overwrite.

---

## Architecture

```mermaid
flowchart TD
    subgraph DesktopApp["Windows Desktop Application (PyQt5 / Python)"]
        UI["Main Window & Dialogs"]
        WE["Wipe Engine (Win32 / WMI)"]
        JNL["Wipe Journal (JSON Log)"]
        CS["Certificate Signer (ECDSA P-256)"]
        PDF["PDF Generator (ReportLab & QR)"]
        SC["Supabase Desktop Client"]
    end

    subgraph WebPortal["Web Portal Stack"]
        FE["Frontend (React + Vite)"]
        BE["Backend API (Express.js / Node.js)"]
    end

    subgraph Cloud["Cloud Infrastructure (Supabase)"]
        AUTH["Supabase Auth"]
        DB[(PostgreSQL Database)]
        ST["Storage Buckets (PDF/JSON)"]
    end

    UI --> WE
    WE --> JNL
    WE --> CS
    CS --> PDF
    UI --> SC
    SC --> AUTH
    SC --> DB
    SC --> ST

    FE --> BE
    BE --> AUTH
    BE --> DB
    BE --> ST
    FE --> AUTH
```

---

## Project Structure

```text
ZeroTrace/
├── certificates/              # Output directory for locally generated PDF/JSON certs & QR codes
├── desktop_app/               # PyQt5 Desktop Client Source Code
│   ├── app.manifest           # Windows application manifest
│   ├── application.py         # Main QApplication wrapper, EULA check & auth flow
│   ├── certificate_manager.py # Certificate creation, signing orchestration & cloud sync
│   ├── dialogs.py             # Qt Dialogs (Login, PIN setup/entry, certificate viewer)
│   ├── EULA.txt               # End User License Agreement text
│   ├── logger.py              # Application logger setup
│   ├── main.py                # Main entry point & Windows admin elevation check
│   ├── main_window.py         # Primary GUI layout, drive table, wipe controls & thread handling
│   ├── pdf_generator.py       # ReportLab PDF certificate compiler & QR code generator
│   ├── signer.py              # ECDSA P-256 signing and SHA-256 hash generation (PyCryptodome)
│   ├── supabase_client.py     # Wrapper for Supabase Auth, DB, and Storage operations
│   ├── verifier.py            # Local JSON/PDF signature verification helper
│   ├── wipe_engine.py         # Core sanitization engine (WMI/Win32 I/O, HPA/DCO, verification)
│   └── wipe_thread.py         # PyQt QThread wrapper for asynchronous wipe execution
├── supabase_config/           # Database setup scripts
│   ├── schema.sql             # PostgreSQL schema (certificates, user_profiles, logs)
│   └── policies.sql           # Row Level Security (RLS) rules and storage permissions
├── web_portal/                # Web Portal Source Code
│   ├── backend/               # Express.js API Server
│   │   ├── lib/               # Supabase JS client initializers
│   │   ├── routes/            # Express route handlers (auth, certificates, verification, signing)
│   │   ├── uploads/           # Temporary file upload directory for verification
│   │   └── server.js          # Express app entry point, middleware & rate limiting
│   └── frontend/              # React + Vite Web Application
│       ├── public/            # Static assets
│       └── src/               # React components (Verification Portal, QR Scanner, Dashboard)
├── requirements.txt           # Python dependency specifications
└── README.md                  # Project documentation
```

---

## Technologies Used

* **Programming Languages**: Python 3.10+, JavaScript (Node.js ES Modules & React JSX), SQL (PostgreSQL)
* **Desktop Framework**: PyQt5
* **Web Backend Framework**: Node.js, Express.js
* **Web Frontend Framework**: React 18, Vite
* **Database & Cloud Services**: Supabase (PostgreSQL, Row Level Security, Supabase Auth, Supabase Storage)
* **Cryptography & PDF Generation**: PyCryptodome (`Crypto.PublicKey.ECC`, `Crypto.Signature.DSS`), ReportLab, `qrcode[pil]`, `pdf-parse`
* **Windows Hardware Access**: `pywin32` (`win32file`, `win32con`), `wmi`, `ctypes`, PowerShell Storage Cmdlets, `diskpart`
* **Testing & Build Tools**: PyTest, PyInstaller

---

## Installation

### Prerequisites

* **Operating System**: Windows 10 / 11 (Windows elevation required for physical drive access).
* **Python**: Python 3.10 or higher.
* **Node.js**: Node.js v18 or higher & npm.
* **Supabase Instance**: A Supabase project URL and API keys (Anon & Service Role).

### 1. Clone the Repository

```cmd
git clone https://github.com/Sreesanth-S/ZeroTrace.git
cd ZeroTrace
```

### 2. Desktop Application Setup

1. Create and activate a Python virtual environment:
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```
2. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```
3. Configure environment variables in `desktop_app/.env`:
   ```env
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-supabase-anon-key
   SIGNING_PRIVATE_KEY_PEM="-----BEGIN EC PRIVATE KEY-----\n...\n-----END EC PRIVATE KEY-----"
   SIGNING_PUBLIC_KEY_PEM="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
   BACKEND_URL=http://localhost:5000
   ```

### 3. Database & Supabase Setup

1. Open your Supabase SQL Editor.
2. Run `supabase_config/schema.sql` to create tables (`certificates`, `user_profiles`, `wipe_logs`, `verification_logs`) and indexes.
3. Run `supabase_config/policies.sql` to configure Row Level Security (RLS) policies and storage bucket access.
4. Create a public storage bucket named `certificates` in Supabase Storage.

### 4. Web Portal Backend Setup

1. Navigate to the backend directory:
   ```cmd
   cd web_portal/backend
   npm install
   ```
2. Create `web_portal/backend/.env`:
   ```env
   PORT=5000
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-supabase-anon-key
   SUPABASE_SERVICE_KEY=your-supabase-service-role-key
   SIGNING_PUBLIC_KEY_PEM="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
   CORS_ORIGINS=http://localhost:5173
   ```
3. Start the Express server:
   ```cmd
   npm start
   ```

### 5. Web Portal Frontend Setup

1. Navigate to the frontend directory:
   ```cmd
   cd web_portal/frontend
   npm install
   ```
2. Create `web_portal/frontend/.env`:
   ```env
   VITE_SUPABASE_URL=https://your-project.supabase.co
   VITE_SUPABASE_ANON_KEY=your-supabase-anon-key
   VITE_API_URL=http://localhost:5000
   ```
3. Start the development server:
   ```cmd
   npm run dev
   ```

---

## Usage

### Running the Desktop Application

Launch `main.py` from an elevated Windows Command Prompt or PowerShell (it will prompt for Administrator elevation automatically):

```cmd
cd desktop_app
python main.py
```

1. **EULA Agreement**: Review and accept the license terms on initial startup.
2. **Authentication**: Sign in using your Supabase user credentials (or proceed in offline mode).
3. **PIN Security**: Set or enter a 4-to-8 digit security PIN.
4. **Drive Selection**: View detected storage devices. Select a target non-system drive.
5. **Wipe Execution**: Choose the desired wiping method (Quick 1-Pass, DoD 3-Pass, DoD 7-Pass, or Hidden Sector Wipe) and confirm.
6. **Certificate Management**: View generated certificate records, print/export PDFs, or trigger manual cloud synchronization.

### Running the Web Verification Portal

1. Access the web interface at `http://localhost:5173`.
2. Navigate to **Verify Certificate**.
3. Verify via:
   * **File Upload**: Drag and drop a ZeroTrace `.json` or `.pdf` certificate file.
   * **Hash Lookup**: Enter a 64-character SHA-256 verification hash directly.
   * **QR Scanner**: Scan the QR code printed on a physical certificate using a web camera.

---

## Workflow

```text
Launch Desktop Application (Admin Privileges)
│
├──> Accept EULA & Authenticate (Supabase or Offline PIN)
│
├──> Query System Storage Devices (WMI / Win32 API)
│    ├──> Detect HPA/DCO Hidden Sectors (ATA IDENTIFY)
│    └──> Filter Out Windows System Drive for Safety
│
├──> Select Target Drive & Choose Sanitization Algorithm
│    ├──> Option A: Quick Wipe (1-Pass Zeros)
│    ├──> Option B: DoD 5220.22-M (3-Pass Zeros/Ones/Random)
│    ├──> Option C: DoD 5220.22-M (7-Pass)
│    └──> Option D: Hidden Sector Wipe (HPA/DCO Exposure & Overwrite)
│
├──> Execute Sanitization Engine
│    ├──> Log Operation to Local Wipe Journal (wipe_journal.json)
│    ├──> Dismount Drive Volumes
│    ├──> Un-hide HPA Sectors (SET MAX ADDRESS)
│    ├──> Perform Overwrite Pass(es)
│    └──> Sample 64 Blocks & Generate SHA-256 Completion Hash
│
├──> Automatic Post-Wipe Disk Initialization & Formatting (PowerShell / Diskpart)
│
├──> Generate Cryptographic Certificate
│    ├──> Sign Hash via ECDSA P-256 (Local Keys or Backend API)
│    ├──> Compile PDF (ReportLab) & JSON Certificate Files
│    └──> Embed Verification QR Code
│
└──> Cloud Sync & Public Verification
     ├──> Upload Metadata & Artifacts to Supabase Database & Storage
     └──> Verify Publicly via Web Portal (File Upload / Hash / Camera QR Scan)
```

---

## Implemented Modules

### Desktop Client Modules

* **`desktop_app/wipe_engine.py`**: Interacts directly with Windows disk handles (`\\\\.\\PhysicalDriveX`). Performs WMI drive discovery, ATA IDENTIFY parsing, SET MAX ADDRESS execution, multi-pass pattern writes, read-back verification sampling, PowerShell/Diskpart disk partitioning, and wipe progress journaling (`WipeJournal`).
* **`desktop_app/signer.py`**: Computes SHA-256 canonical certificate hashes and generates/verifies ECDSA P-256 digital signatures using PyCryptodome. Supports loading keys from environment variables or local `.pem` files.
* **`desktop_app/pdf_generator.py`**: Formats and builds PDF certificates using ReportLab. Encodes certificate metadata and verification URLs into QR codes using `qrcode`.
* **`desktop_app/certificate_manager.py`**: Coordinates the post-wipe certificate pipeline. Constructs certificate dictionaries, manages local storage in `certificates/`, sends signing requests to the backend server when online, and uploads records and files to Supabase.
* **`desktop_app/supabase_client.py`**: Encapsulates Supabase authentication, database queries on `certificates` and `user_profiles`, and storage bucket operations.
* **`desktop_app/application.py` & `main_window.py`**: Implements the PyQt5 graphical interface, handling EULA persistence, PIN verification, drive table rendering, progress bar updates, and worker thread lifecycle (`wipe_thread.py`).

### Web Portal Modules

* **`web_portal/backend/routes/verification.js`**: Receives certificate verification requests. Extracts hashes from uploaded JSON files or PDF text streams (parsing embedded `ZT_PAYLOAD` markers), verifies ECDSA signatures against the server's public key, and queries Supabase database records for match validation.
* **`web_portal/backend/routes/signing.js`**: Exposes `/api/certificates/sign` to sign certificate payloads using the server's private key for authenticated desktop client sessions.
* **`web_portal/frontend/src/App.jsx` & `PublicVerificationPortal.jsx`**: Provides the user interface for certificate verification, drag-and-drop file inputs, verification result badge rendering, and camera QR scanning integrations (`QrScanner.jsx`).

---

## Security Features

* **ECDSA P-256 Digital Signatures**: Certificates are cryptographically signed using ECDSA P-256 with SHA-256 hashing. Any modification to certificate JSON data invalidates the signature.
* **Read-Back Hash Verification**: Computes a SHA-256 hash by sampling 64 evenly spaced 1 MB blocks across the physical drive surface post-wipe to confirm disk state.
* **PIN Access Control**: Desktop application access requires a PIN verified against BCrypt/SHA-256 hashes stored in Supabase user profiles or local settings.
* **System Drive Protection**: Automatically flags and restricts sanitization operations on the active Windows boot/system drive (`C:`).
* **Database Row Level Security**: Supabase PostgreSQL database tables (`certificates`, `user_profiles`, `wipe_logs`) are protected with RLS policies restricting data access to authorized owners and service roles.
* **Backend Security Hardening**: Express.js server implements HTTP security headers via `helmet` and IP-based rate limiting on verification and signing endpoints.

---

## Limitations

* **Windows Operating System Only**: The wiping engine relies strictly on Windows Win32 APIs (`win32file`, `win32con`), WMI, Windows PowerShell, and `diskpart`. Linux and macOS are not supported.
* **Hardware Controller-Level Erase Requires Software Fallback**: Hardware ATA Secure Erase and NVMe Format/Sanitize pass-through commands often fail or report frozen state under standard Windows AHCI/NVMe storage drivers without specialized vendor drivers or power-cycling. In all such cases, the engine automatically falls back to software multi-pass overwrites.
* **No Bootable Standalone ISO Environment**: The current implementation runs as an installed Windows application within a host Windows OS environment; it does not include a standalone Linux live ISO image.
* **Administrator Elevation Requirement**: The application cannot discover physical drives or execute low-level write handles without full Windows Administrator elevation.

---

## Future Improvements

* Development of a Linux-based bootable ISO environment to allow wiping system drives offline.
* Advanced NVMe/SATA controller driver integration for native hardware secure erase without OS driver interference.
* Integration of additional software sanitization standards (such as Gutmann 35-pass and Schneier 7-pass).

---

## License

No license has been specified.

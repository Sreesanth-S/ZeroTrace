# ZeroTrace
ZeroTrace is a secure, cross-platform data wiping solution designed to safely erase data from storage devices and issue tamper-proof digital certificates. It is an ideal solution for device recycling or resale, providing a verifiable trust chain for data destruction.

## 🚀 Features
- Comprehensive Device Support: Securely wipes HDDs, SSDs, NVMe drives, USB storage, and Android smartphones.
- Advanced Wiping Methods: Utilizes controller-level erasure (ATA/NVMe) where available, with a fallback to secure overwrite patterns.
- Hidden Sector Detection: Identifies and wipes Host Protected Area (HPA) and Device Configuration Overlay (DCO) sectors.
- Tamper-Proof Certification: Generates digitally signed JSON and PDF certificates featuring QR codes and hashes for easy verification.
-Verification Ecosystem: Includes a public web portal for certificate validation and a user dashboard to track wiped devices.
- Security-First Design: PIN-protected application access and a Supabase backend for secure data management.
- Flexible Deployment: Supports online usage with cloud sync or offline usage via a bootable ISO.

## 🛠 Tech Stack
### Desktop Application
- Language: Python 3
- GUI Framework: PyQt5
- PDF/QR Generation: ReportLab, Pillow, and qrcode
- Security: PyCryptodome (Cryptography) and bcrypt
- System Integration: pywin32, WMI, and psutil for Windows device detection

### Web Portal
- Frontend: React (Vite), Tailwind CSS, and React Router
- Backend: Node.js with Express
- Database/Auth: Supabase

## 📋 Prerequisites
Desktop: Python 3.10+ and Administrator/Root privileges.
Web: Node.js (v18+) and a Supabase account.

## Installation & Setup
1. Desktop App Setup
Bash
### Clone the repository
```
git clone https://github.com/sreesanth-s/zerotrace.git 
cd ZeroTrace
```
# Install dependencies
```
pip install -r requirements.txt
```
2. Web Portal Setup
```
cd web_portal/backend
npm install

# Configure your .env file with SUPABASE_URL and SUPABASE_KEY
npm start
```
```
cd web_portal/frontend
npm install
npm run dev
```
🖥 Usage
Running the Desktop Application
The application requires administrative privileges to access hardware-level wiping commands. On Windows, it will automatically prompt for UAC elevation.
```
python desktop_app/main.py
```
Verifying Certificates
Navigate to the public web portal.

Scan the QR code on the PDF certificate or upload the certificate file.

The portal will verify the digital signature against the public key to ensure authenticity.

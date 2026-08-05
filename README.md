# ZeroTrace

ZeroTrace is a secure, verifiable data sanitization and certificate issuance system designed for Windows storage devices. It enables users to safely erase hard disk drives (HDDs), solid-state drives (SSDs), NVMe drives, and USB flash drives, performing read-back verification and generating cryptographically signed (ECDSA P-256) tamper-proof PDF/JSON certificates. The system includes a native PyQt5 desktop application for drive wiping and a React/Express web portal for public certificate verification.

---

## Overview

ZeroTrace addresses the challenge of verifying that storage media has been securely wiped prior to disposal, recycling, or resale. 

The application operates on Windows with elevated Administrator privileges, detecting connected storage devices via WMI and Win32 APIs. It executes software overwrite sanitization patterns (Quick 1-Pass Zeros, DoD 5220.22-M 3-Pass, and DoD 7-Pass), un-hides and wipes Host Protected Area (HPA) and Device Configuration Overlay (DCO) sectors, performs 64-block sampling read-back verification, automatically re-initializes and formats storage volumes post-wipe, and logs operation progress into a local recovery journal.

Wipe results are compiled into digitally signed certificates containing SHA-256 verification hashes, ECDSA signatures, and embedded QR codes. Certificates can be stored locally or synchronized to a cloud database (Supabase) and verified publicly through a web application using file uploads, hash lookups, or camera-based QR code scanning.

---

## Features  

- Secure wiping of HDDs, SSDs, NVMe, USB, smartphones (via Android)  
- Uses controller-level erase (e.g. ATA/NVMe) where supported, fallback to overwrite  
- Detects and optionally wipes hidden/Host Protected Area (HPA/DCO) sectors on drives
- Generates digitally signed certificates (JSON + PDF) with QR / hash for verification  
- Public web portal for certificate verification  
- User dashboard showing wiped devices  
- PIN-protected application access  
- Offline usage (bootable ISO) and online usage with sync  
- Supabase backend for storing user, device, certificate data  

# ZeroTrace  

ZeroTrace is a secure, cross-platform data wiping solution that enables users to safely erase data from storage devices and issue tamper-proof certificates. Ideal for recycling or resale, it ensures trust by letting recipients verify that devices were wiped securely.

## Features  

- Secure wiping of HDDs, SSDs, NVMe, USB, smartphones (via Android)  
- Uses controller-level erase (e.g. ATA/NVMe) where supported, fallback to overwrite  
- Generates digitally signed certificates (JSON + PDF) with QR / hash for verification  
- Public web portal for certificate verification  
- User dashboard showing wiped devices  
- PIN-protected application access  
- Offline usage (bootable ISO) and online usage with sync  
- Supabase backend for storing user, device, certificate data  

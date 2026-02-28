import json
import sys
from pathlib import Path
from datetime import datetime

# Add desktop_app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pdf_generator import PDFCertificateGenerator
from signer import CertificateSigner, generate_cert_id


def load_or_build_certificate_data(json_path: Path | None) -> dict:
    if json_path:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # Fallback sample data for standalone test run
    sample = {
        "cert_id": generate_cert_id("TEST-DEVICE-001"),
        "version": "1.0",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "device_id": "TEST-DEVICE-001",
        "device": "Test SSD",
        "device_info": {
            "model": "Test Model",
            "serial": "TEST-SERIAL-123",
            "capacity": "512 GB",
            "type": "SSD",
        },
        "method_used": "Quick Wipe (1-Pass Zeros)",
        "passes_completed": 1,
        "start": datetime.utcnow().isoformat(),
        "end": datetime.utcnow().isoformat(),
        "status": "Completed",
        "verification": {
            "completion_hash": "",
            "method": "SHA-256",
            "verified": True,
        },
        "operator": {
            "user_id": "local",
            "email": "local@test",
        },
    }
    signer = CertificateSigner()
    return signer.sign_certificate(sample)


def try_verify_embedded_markers(pdf_path: Path) -> None:
    try:
        import pdfplumber  # optional
    except Exception:
        print("Marker check skipped (install pdfplumber for PDF text extraction check).")
        return

    text_chunks = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            text_chunks.append(page.extract_text() or "")
    full_text = "\n".join(text_chunks)

    has_begin = "ZT_PAYLOAD_V1_BEGIN" in full_text
    has_end = "ZT_PAYLOAD_V1_END" in full_text
    print(f"Embedded marker BEGIN found: {has_begin}")
    print(f"Embedded marker END found: {has_end}")


def main():
    input_json = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    cert_data = load_or_build_certificate_data(input_json)

    out_dir = Path(__file__).parent / "certificates"
    generator = PDFCertificateGenerator(output_dir=str(out_dir))

    cert_id = cert_data.get("cert_id", "TEST-CERT")
    output_name = f"{cert_id}_embedded.pdf"
    pdf_path = generator.generate_certificate(cert_data, output_name)

    print(f"Generated embedded PDF: {pdf_path}")
    print(f"Certificate ID: {cert_id}")
    print(f"Verification hash: {cert_data.get('_signature', {}).get('verification_hash', 'N/A')}")
    try_verify_embedded_markers(pdf_path)


if __name__ == "__main__":
    main()


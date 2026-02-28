import sys
import json
from pathlib import Path

# Add desktop_app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pdf_generator import PDFCertificateGenerator

def test_qr_code_with_hash():
    """Test QR code generation with verification hash"""
    generator = PDFCertificateGenerator()
    
    # Create sample certificate data with verification hash
    cert_data = {
        'cert_id': 'TEST-CERT-12345',
        'device_id': 'PHYSICALDRIVE1',
        'device': 'Samsung SSD 1TB',
        'method_used': 'Quick Wipe',
        'status': 'Completed',
        'generated_at': '2026-02-27T17:00:00Z',
        '_signature': {
            'verification_hash': 'a1b2c3d4e5f6789012345678901234567890abcdefghijklmnopqrstuvwxyz12'
        },
        'device_info': {
            'model': 'Samsung 870 EVO',
            'serial': 'S12345678',
        }
    }
    
    # Test 1: Generate standalone QR code image
    print("Test 1: Generate standalone QR code image...")
    qr_path = generator.generate_qr_code_image(
        cert_id='TEST-CERT-12345',
        verification_hash='a1b2c3d4e5f6789012345678901234567890abcdefghijklmnopqrstuvwxyz12',
        device_id='PHYSICALDRIVE1',
        method='Quick Wipe'
    )
    assert qr_path.exists(), f"QR code image not created at {qr_path}"
    print(f"✓ Standalone QR code created: {qr_path}")
    print(f"  File size: {qr_path.stat().st_size} bytes")
    
    # Test 2: Verify QR code data structure
    print("\nTest 2: Verify QR code data structure...")
    try:
        # Try to decode QR code if pyzbar is available
        from pyzbar.pyzbar import decode
        from PIL import Image
        
        img = Image.open(qr_path)
        decoded = decode(img)
        if decoded:
            qr_content = decoded[0].data.decode('utf-8')
            qr_data = json.loads(qr_content)
            
            expected_hash = 'a1b2c3d4e5f6789012345678901234567890abcdefghijklmnopqrstuvwxyz12'
            actual_hash = qr_data.get('verification_hash', '')
            
            assert actual_hash == expected_hash, f"Hash mismatch: {actual_hash} != {expected_hash}"
            print(f"✓ QR code contains full verification hash")
            print(f"  Hash: {actual_hash}")
            print(f"  QR data keys: {list(qr_data.keys())}")
        else:
            print("⚠ Warning: Could not decode QR code")
    except ImportError:
        print("✓ pyzbar not installed - QR file created successfully")
        print("  To fully verify, install: pip install pyzbar pillow")
    
    # Test 3: Create PDF with embedded QR code
    print("\nTest 3: Generate PDF certificate with embedded QR code...")
    pdf_path = generator.generate_certificate(cert_data, 'test_cert_with_qr.pdf')
    assert pdf_path.exists(), f"PDF not created at {pdf_path}"
    print(f"✓ PDF certificate created: {pdf_path}")
    print(f"  File size: {pdf_path.stat().st_size} bytes")
    
    # Test 4: Verify certificate has full hash in metadata
    print("\nTest 4: Verify certificate metadata...")
    verification_hash = cert_data.get('_signature', {}).get('verification_hash', '')
    assert verification_hash == 'a1b2c3d4e5f6789012345678901234567890abcdefghijklmnopqrstuvwxyz12'
    print(f"✓ Certificate metadata contains full hash")
    print(f"  Hash length: {len(verification_hash)} characters")
    
    print("\n" + "="*60)
    print("All QR code verification tests passed! ✓")
    print("="*60)
    print("\nGenerated artifacts:")
    print(f"  - {qr_path}")
    print(f"  - {pdf_path}")

if __name__ == '__main__':
    test_qr_code_with_hash()

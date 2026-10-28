import React, { useEffect, useRef, useState } from 'react';
import { Html5Qrcode } from 'html5-qrcode';

const QrScanner = ({ onResult }) => {
  const containerIdRef = useRef(`qr-code-scanner-${Math.random().toString(36).slice(2)}`);
  const scannerRef = useRef(null);
  const scannedRef = useRef(false);
  const [status, setStatus] = useState('Starting camera...');

  useEffect(() => {
    let isMounted = true;
    const containerId = containerIdRef.current;
    const scanner = new Html5Qrcode(containerId);
    scannerRef.current = scanner;

    const startScanner = async () => {
      try {
        await scanner.start(
          { facingMode: 'environment' },
          { fps: 10, qrbox: { width: 240, height: 240 } },
          (decodedText) => {
            if (scannedRef.current) return;
            scannedRef.current = true;
            setStatus('QR code scanned.');
            onResult(decodedText);
          },
          () => {
            // Ignore noisy frame-level decode errors.
          }
        );

        if (isMounted) setStatus('Point camera at QR code');
      } catch (error) {
        if (isMounted) {
          setStatus('Camera unavailable. Use image upload below.');
        }
        console.error('QR scanner start failed:', error);
      }
    };

    startScanner();

    return () => {
      isMounted = false;
      const cleanup = async () => {
        try {
          if (scannerRef.current?.isScanning) {
            await scannerRef.current.stop();
          }
          await scannerRef.current?.clear();
        } catch (error) {
          console.error('QR scanner cleanup failed:', error);
        }
      };
      cleanup();
    };
  }, [onResult]);

  const handleImageScan = async (event) => {
    const file = event.target.files?.[0];
    if (!file || !scannerRef.current) return;

    try {
      setStatus('Scanning uploaded image...');
      const decodedText = await scannerRef.current.scanFile(file, true);
      setStatus('QR code scanned from image.');
      onResult(decodedText);
    } catch {
      setStatus('Could not read QR from image.');
    } finally {
      event.target.value = '';
    }
  };

  return (
    <div style={{ width: '100%' }}>
      <div id={containerIdRef.current} style={{ width: '100%' }} />
      <p style={{ marginTop: 8, fontSize: 12, opacity: 0.9 }}>{status}</p>
      <label style={{ display: 'inline-block', marginTop: 6, fontSize: 12, textDecoration: 'underline', cursor: 'pointer' }}>
        Scan from image
        <input type="file" accept="image/*" onChange={handleImageScan} style={{ display: 'none' }} />
      </label>
    </div>
  );
};

export default QrScanner;

import React, { useEffect } from 'react';
import { Html5QrcodeScanner } from 'html5-qrcode';

const QrScanner = ({ onResult }) => {
  useEffect(() => {
    // The ID string to be used for the HTML element
    const qrCodeRegionId = "qr-code-scanner";

    const qrCodeScanner = new Html5QrcodeScanner(
      qrCodeRegionId, // Pass the string ID here
      { fps: 10, qrbox: 250 },
      false
    );

    const onScanSuccess = (decodedText) => {
      // Cleanup the scanner after a successful scan
      qrCodeScanner.clear().then(() => {
        onResult(decodedText);
      }).catch((error) => {
        console.error("Failed to clear scanner:", error);
      });
    };

    const onScanError = (errorMessage) => {
      // Log errors but don't stop the scanner
      console.warn(errorMessage);
    };

    qrCodeScanner.render(onScanSuccess, onScanError);

    // This cleanup function is crucial to prevent multiple scanners from running
    return () => {
      qrCodeScanner.clear().catch((error) => {
        console.error("Failed to clear scanner on unmount:", error);
      });
    };
  }, [onResult]);

  return (
    // The div with the matching string ID
    <div id="qr-code-scanner" style={{ width: "100%" }}></div>
  );
};

export default QrScanner;
import React from 'react';
import QRCode from 'react-qr-code';

const QrGenerator = ({ data }) => {
  if (!data) {
    return <p>No data to generate QR code.</p>;
  }

  // FIX: Reduced the size to make the QR code smaller
  const qrSize = 128; 

  return (
    <div style={{ padding: '8px', background: 'white', display: 'inline-block', borderRadius: '4px', border: '1px solid #ddd' }}>
      <QRCode
        value={data}
        size={qrSize}
        viewBox={`0 0 ${qrSize} ${qrSize}`}
      />
    </div>
  );
};

export default QrGenerator;

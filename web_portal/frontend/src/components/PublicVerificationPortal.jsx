import React, { useState } from 'react';
import QrScanner from './QrScanner';
import { supabaseKey } from '../lib/supabase';

const PublicVerificationPortal = () => {
  const [verificationMode, setVerificationMode] = useState('pdf');
  const [verificationResult, setVerificationResult] = useState(null);

  const extractVerificationHash = (rawScanValue) => {
    const value = String(rawScanValue || '').trim();
    if (!value) return '';

    try {
      const parsed = JSON.parse(value);
      if (parsed?.verification_hash) return String(parsed.verification_hash).trim();
    } catch {
      // Continue with URL/plain-text parsing
    }

    try {
      const asUrl = new URL(value);
      const queryHash = asUrl.searchParams.get('hash');
      if (queryHash) return queryHash.trim();
    } catch {
      // Not a URL, continue
    }

    const hexHashRegex = /^[A-Fa-f0-9]{64}$/;
    if (hexHashRegex.test(value)) return value;

    return '';
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setVerificationResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('http://localhost:5000/api/verify/file', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (response.ok) {
        setVerificationResult(data);
      } else {
        setVerificationResult({ error: data.error || 'File verification failed' });
      }
    } catch (error) {
      console.error('File upload error:', error);
      setVerificationResult({ error: 'Network error. Please try again.' });
    } finally {
      // Clear file input
      e.target.value = '';
    }
  };

  const verifyByHash = async (hash) => {
    if (!hash) return;
    setVerificationResult(null);
    try {
      const response = await fetch('http://localhost:5000/api/verify/hash', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'apikey': supabaseKey,
        },
        body: JSON.stringify({ hash }),
      });
      const data = await response.json();
      if (response.ok) {
        setVerificationResult(data);
      } else {
        setVerificationResult({ error: data.error || data.message || 'Verification failed' });
      }
    } catch (error) {
      console.error('QR verification error:', error);
      setVerificationResult({ error: 'Network error. Please try again.' });
    }
  };

  const handleScanResult = (result) => {
    const hash = extractVerificationHash(result);
    if (!hash) {
      setVerificationResult({ error: 'QR code does not contain a valid verification hash.' });
      return;
    }
    verifyByHash(hash);
  };

  const renderVerificationContent = () => {
    switch (verificationMode) {
      case 'pdf':
        return (
          <section>
            <h2>Verify by Uploading Certificate</h2>
            <div className="verification-box">
              <p>Upload your certificate file (JSON) to verify its authenticity.</p>
              <form>
                <input
                  type="file"
                  accept=".pdf,.json"
                  onChange={handleFileUpload}
                  required
                />
              </form>
              {verificationResult && (
                <div className="verification-result" style={{ marginTop: '20px', padding: '10px', border: '1px solid #ccc', borderRadius: '5px' }}>
                  {verificationResult.error ? (
                    <p style={{ color: 'red' }}>{verificationResult.error}</p>
                  ) : (
                    <div>
                      <p><strong>Status:</strong> {verificationResult.status}</p>
                      <p><strong>Message:</strong> {verificationResult.message}</p>
                      {verificationResult.details && (
                        <div>
                          <p><strong>Certificate ID:</strong> {verificationResult.cert_id}</p>
                          <p><strong>Device Name:</strong> {verificationResult.details.device_name}</p>
                          <p><strong>Wipe Method:</strong> {verificationResult.details.wipe_method}</p>
                          <p><strong>Wipe Date:</strong> {verificationResult.details.wipe_date}</p>
                          <p><strong>Signature Valid:</strong> {verificationResult.details.signature_valid ? 'Yes' : 'No'}</p>
                          <p><strong>Database Match:</strong> {verificationResult.details.database_match ? 'Yes' : 'No'}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </section>
        );

      case 'scan':
        return (
          <section>
            <h2>Scan QR Code</h2>
            <p>Scan a QR code on a physical certificate for quick verification.</p>
            {/* The qr-scanner-container likely already provides the box styling */}
            <div className="qr-scanner-container">
              <QrScanner onResult={handleScanResult} />
            </div>
          </section>
        );
        
      default:
        return null;
    }
  };

  return (
    <div className="public-portal-container">
      <h1>Certification Verification Portal</h1>
      <p>Verify the authenticity of a certificate instantly using one of the methods below.</p>

      {/* Navigation Tabs for Verification Options */}
      <div className="top-nav">
        <button
          style={{
            backgroundColor: verificationMode === 'pdf' ? '#1e7e34' : '#28a745',
            color: 'white',
          }}
          onClick={() => setVerificationMode('pdf')}
        >
          JSON Upload
        </button>
        <button 
          style={{ 
            backgroundColor: verificationMode === 'scan' ? '#1e7e34' : '#28a745',
            color: 'white',
          }}
          onClick={() => setVerificationMode('scan')}
        >
          QR Scan
        </button>
      </div>

      <div className="verification-options">
        {renderVerificationContent()}
      </div>
    </div>
  );
};

// This is the line that must be present
export default PublicVerificationPortal;



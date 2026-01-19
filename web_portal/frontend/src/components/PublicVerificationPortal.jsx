import React, { useState } from 'react';
import QrScanner from './QrScanner';
import { supabaseKey } from '../lib/supabase';
// Removed: import QrGenerator from './QrGenerator';

const PublicVerificationPortal = ({ setView }) => {
  const [certificateId, setCertificateId] = useState('');
  // State to manage the active verification mode: 'manual', 'pdf', or 'scan'
  const [verificationMode, setVerificationMode] = useState('manual');
  const [verificationResult, setVerificationResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleManualVerification = async (e) => {
    e.preventDefault();
    if (certificateId.trim() === '') return;

    setIsLoading(true);
    setVerificationResult(null);

    try {
      const response = await fetch(`http://localhost:5000/api/verify/id/${certificateId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'apikey': supabaseKey,
        },
      });

      const data = await response.json();

      if (response.ok) {
        setVerificationResult(data);
      } else {
        setVerificationResult({ error: data.message || 'Verification failed' });
      }
    } catch (error) {
      console.error('Verification error:', error);
      setVerificationResult({ error: 'Network error. Please try again.' });
    } finally {
      setIsLoading(false);
    }
  };

  const handlePdfUpload = (e) => {
    e.preventDefault();
    const file = e.target.files[0];
    if (file) {
      console.log('PDF file uploaded:', file.name);
      // In a real app, you would process the PDF (e.g., extract embedded data or hash) 
      // and send it to the backend for verification.
      // NOTE: Using console.log instead of alert for better practice.
      console.log(`Simulating verification for PDF: ${file.name}`);
      // Clear file input if necessary or handle state change
    }
  };

  const handleScanResult = (result) => {
    console.log('Scan result:', result);
    // Handle the verification logic here, e.g., navigate to a URL
    window.location.href = result; 
  };

  const renderVerificationContent = () => {
    switch (verificationMode) {
      case 'manual':
        return (
          <section>
            <h2>Verify by Entering ID</h2>
            <div className="verification-box">
              <form onSubmit={handleManualVerification}>
                <input
                  type="text"
                  value={certificateId}
                  onChange={(e) => setCertificateId(e.target.value)}
                  placeholder="Enter Certificate ID"
                  required
                />
                <button type="submit" disabled={isLoading}>
                  {isLoading ? 'Verifying...' : 'Verify Certificate'}
                </button>
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
                          <p><strong>Wipe Date:</strong> {verificationResult.details.wipe_date}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </section>
        );

      case 'pdf':
        return (
          <section>
            <h2>Verify by Uploading PDF</h2>
            <div className="verification-box">
              <p>Upload the certificate PDF to verify its digital signature.</p>
              <form>
                <input
                  type="file"
                  accept=".pdf"
                  onChange={handlePdfUpload}
                  required
                />
              </form>
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
            backgroundColor: verificationMode === 'manual' ? '#1e7e34' : '#28a745',
            color: 'white',
          }}
          onClick={() => setVerificationMode('manual')}
        >
          Manual ID
        </button>
        <button 
          style={{ 
            backgroundColor: verificationMode === 'pdf' ? '#1e7e34' : '#28a745',
            color: 'white',
          }}
          onClick={() => setVerificationMode('pdf')}
        >
          PDF Upload
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


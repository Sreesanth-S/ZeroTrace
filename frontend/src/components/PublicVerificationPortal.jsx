import React, { useState } from 'react';

const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const PublicVerificationPortal = () => {
  const [verificationResult, setVerificationResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setVerificationResult({
        final_verdict: 'Unverified',
        verdict_explanation: 'Only official ZeroTrace PDF certificates (.pdf) are supported for tamper detection.'
      });
      return;
    }

    setVerificationResult(null);
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${apiUrl}/verify/pdf`, {
        method: 'POST',
        body: formData
      });

      const data = await response.json();
      setVerificationResult(data);
    } catch (error) {
      console.error('File upload error:', error);
      setVerificationResult({
        final_verdict: 'Unverified',
        verdict_explanation: 'Network error or backend unreachable. Please try again.'
      });
    } finally {
      setLoading(false);
      e.target.value = '';
    }
  };

  return (
    <div className="public-portal-container">
      <h1>Certificate Verification Portal</h1>
      <p>Verify the authenticity of a ZeroTrace PDF certificate and detect tampering.</p>

      <section>
        <h2>Upload Certificate PDF</h2>
        <div className="verification-box">
          <p>Select an official digitally signed PDF certificate (.pdf) to verify integrity.</p>
          <form onSubmit={(e) => e.preventDefault()}>
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileUpload}
              required
            />
          </form>

          {loading && <p>Verifying PDF certificate authenticity and checking for tamper evidence...</p>}

          {verificationResult && !loading && (
            <div className="verification-result" style={{ marginTop: '20px', padding: '15px', border: '1px solid #ccc', borderRadius: '6px' }}>
              <p><strong>Verdict:</strong> {verificationResult.final_verdict}</p>
              <p><strong>Explanation:</strong> {verificationResult.verdict_explanation}</p>
              <p><strong>Cryptographic Authenticity:</strong> {verificationResult.cryptographic_authenticity ? 'Valid' : 'Failed'}</p>
              <p><strong>Registry Recognition:</strong> {verificationResult.registry_recognition ? 'Found' : 'Not Found'}</p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
};

export default PublicVerificationPortal;


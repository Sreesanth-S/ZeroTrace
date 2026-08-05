import React from 'react';

export default function PrivacyPolicy() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-8 text-gray-200">
      <h1 className="text-3xl font-bold text-white mb-6">Privacy Policy</h1>
      <p className="text-sm text-gray-400 mb-4">Effective Date: July 29, 2026</p>

      <section className="mb-6">
        <h2 className="text-xl font-semibold text-white mb-2">1. Information We Collect</h2>
        <p className="mb-2">
          ZeroTrace collects minimal personal and technical information necessary to perform secure data sanitization verification and cloud certificate storage:
        </p>
        <ul className="list-disc list-inside ml-4 space-y-1 text-gray-300">
          <li><b>Account Credentials:</b> Email address, full name, and organization details provided during registration.</li>
          <li><b>Verification Access Logs:</b> IP addresses, timestamps, and browser user-agent headers collected when submitting certificates or verification hashes to the verification portal.</li>
          <li><b>Device Sanitization Metadata:</b> Drive serial numbers, model names, capacity, wipe algorithm used, start/end timestamps, and post-wipe read-back verification hashes.</li>
        </ul>
      </section>

      <section className="mb-6">
        <h2 className="text-xl font-semibold text-white mb-2">2. How Information Is Used</h2>
        <p className="mb-2">
          The collected information is used strictly to:
        </p>
        <ul className="list-disc list-inside ml-4 space-y-1 text-gray-300">
          <li>Generate tamper-evident, cryptographically signed Certificates of Sanitization.</li>
          <li>Provide a public verification service for third parties to confirm certificate validity.</li>
          <li>Maintain auditable logs of data destruction activities for regulatory compliance (GDPR, CCPA, HIPAA).</li>
          <li>Prevent fraudulent verification attempts and rate-limit service abuse.</li>
        </ul>
      </section>

      <section className="mb-6">
        <h2 className="text-xl font-semibold text-white mb-2">3. Storage & Security</h2>
        <p>
          Certificates and authentication data are securely stored in Supabase managed cloud infrastructure with Row-Level Security (RLS) enforcement. Cryptographic signatures are anchored using server-managed private keys (ECDSA-SHA256).
        </p>
      </section>

      <section className="mb-6">
        <h2 className="text-xl font-semibold text-white mb-2">4. Your Data Protection Rights (GDPR / CCPA)</h2>
        <p className="mb-2">
          Depending on your jurisdiction, you have rights to access, rectify, or request deletion of your personal account data. Please note that public verification logs and certificate verification hashes are preserved to maintain non-repudiable audit trails of historical data destruction operations.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="text-xl font-semibold text-white mb-2">5. Contact Us</h2>
        <p>
          If you have questions regarding this Privacy Policy or ZeroTrace data compliance, please contact privacy@zerotrace.io.
        </p>
      </section>
    </div>
  );
}

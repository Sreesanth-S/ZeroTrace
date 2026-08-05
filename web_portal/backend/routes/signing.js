// web_portal/backend/routes/signing.js
import express from 'express';
import crypto from 'crypto';
import { requireAuth } from './auth.js';

const router = express.Router();

function canonicalize(value) {
  if (Array.isArray(value)) {
    return value.map(canonicalize);
  }
  if (value && typeof value === 'object') {
    return Object.keys(value)
      .sort()
      .reduce((acc, key) => {
        acc[key] = canonicalize(value[key]);
        return acc;
      }, {});
  }
  return value;
}

function computeCertificateHash(certificate) {
  const clone = { ...certificate };
  delete clone._signature;
  const canonical = canonicalize(clone);
  const json = JSON.stringify(canonical);
  return crypto.createHash('sha256').update(json, 'utf8').digest('hex');
}

/**
 * POST /api/certificates/sign
 * Signs raw certificate data using server-anchored private key.
 * Requires user authentication via Bearer token (JWT).
 */
router.post('/sign', requireAuth, async (req, res) => {
  try {
    const certData = req.body?.cert_data || req.body;
    if (!certData || !certData.cert_id) {
      return res.status(400).json({ error: 'Invalid certificate data. cert_id is required.' });
    }

    const privateKeyPem = process.env.SIGNING_PRIVATE_KEY_PEM
      ? process.env.SIGNING_PRIVATE_KEY_PEM.replace(/\\n/g, '\n').replace(/^"|"$/g, '')
      : null;

    const publicKeyPem = process.env.SIGNING_PUBLIC_KEY_PEM
      ? process.env.SIGNING_PUBLIC_KEY_PEM.replace(/\\n/g, '\n').replace(/^"|"$/g, '')
      : null;

    if (!privateKeyPem || !publicKeyPem) {
      return res.status(500).json({ error: 'Server signing keys not configured.' });
    }

    // 1. Calculate deterministic hash
    const verificationHash = computeCertificateHash(certData);

    // 2. Sign hash with ECDSA-SHA256
    const signer = crypto.createSign('sha256');
    signer.update(verificationHash, 'utf8');
    signer.end();

    const signature = signer.sign(privateKeyPem, 'base64');

    // 3. Attach trusted signature object
    const signedCert = {
      ...certData,
      _signature: {
        algorithm: 'ECDSA-SHA256',
        signature: signature,
        public_key: publicKeyPem,
        signed_at: new Date().toISOString(),
        verification_hash: verificationHash,
        signing_mode: 'server_trusted'
      }
    };

    return res.json({
      success: true,
      signed_cert: signedCert
    });
  } catch (error) {
    console.error('Certificate signing error:', error);
    return res.status(500).json({ error: 'Failed to sign certificate: ' + error.message });
  }
});

export default router;

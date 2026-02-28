// web_portal/backend/routes/verification.js
import express from 'express';
import multer from 'multer';
import { unlink, readFile } from 'fs/promises';
import path from 'path';
import { createRequire } from 'module';
import crypto from 'crypto';
import zlib from 'zlib';
import supabaseClient from '../lib/supabaseClient.js';

const router = express.Router();
const require = createRequire(import.meta.url);

let pdfParse = null;
try {
  pdfParse = require('pdf-parse');
} catch (_error) {
  pdfParse = null;
}

const HASH_REGEX = /([A-Fa-f0-9]{64})/;
const PAYLOAD_BEGIN = 'ZT_PAYLOAD_V1_BEGIN';
const PAYLOAD_END = 'ZT_PAYLOAD_V1_END';

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

function verifyCertificateSignature(certificate) {
  const signatureInfo = certificate?._signature || {};
  const storedHash = String(signatureInfo.verification_hash || '').trim().toLowerCase();
  const signatureB64 = signatureInfo.signature;
  const publicKey = signatureInfo.public_key;

  if (!storedHash || !signatureB64 || !publicKey) {
    return { valid: false, reason: 'missing_signature_fields' };
  }

  const calculatedHash = computeCertificateHash(certificate);
  if (storedHash !== calculatedHash) {
    return { valid: false, reason: 'hash_mismatch', calculatedHash, storedHash };
  }

  try {
    const verifier = crypto.createVerify('sha256');
    verifier.update(storedHash, 'utf8');
    verifier.end();
    const isValid = verifier.verify(publicKey, Buffer.from(signatureB64, 'base64'));
    return { valid: isValid, reason: isValid ? 'ok' : 'signature_invalid', storedHash };
  } catch (error) {
    return { valid: false, reason: `signature_error:${error.message}` };
  }
}

function extractVerificationHashFromJson(certificate) {
  return ((
    certificate?._signature?.verification_hash ||
    certificate?.verification?.completion_hash ||
    ''
  ) || '').trim().toLowerCase();
}

function extractVerificationHashFromPdfText(pdfText) {
  if (!pdfText) return '';

  const prefixedPatterns = [
    /verification\s*hash[^A-Fa-f0-9]*([A-Fa-f0-9]{64})/i,
    /\bhash[^A-Fa-f0-9]*([A-Fa-f0-9]{64})/i
  ];

  for (const pattern of prefixedPatterns) {
    const match = pdfText.match(pattern);
    if (match?.[1]) return match[1].trim().toLowerCase();
  }

  const fallback = pdfText.match(HASH_REGEX);
  return (fallback?.[1] || '').trim().toLowerCase();
}

function extractPayloadCertificateFromPdfText(pdfText) {
  if (!pdfText) return null;

  const beginIndex = pdfText.indexOf(PAYLOAD_BEGIN);
  const endIndex = pdfText.indexOf(PAYLOAD_END);
  if (beginIndex === -1 || endIndex === -1 || endIndex <= beginIndex) {
    return null;
  }

  const tokenRegion = pdfText.slice(beginIndex + PAYLOAD_BEGIN.length, endIndex);
  const token = tokenRegion.replace(/[^A-Za-z0-9\-_]/g, '');
  if (!token) return null;

  try {
    const compressed = Buffer.from(token, 'base64url');
    const jsonBuffer = zlib.inflateSync(compressed);
    const certificate = JSON.parse(jsonBuffer.toString('utf8'));
    return certificate;
  } catch (_error) {
    return null;
  }
}

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const config = req.app.get('config');
    cb(null, config.uploadFolder);
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    cb(null, uniqueSuffix + '-' + file.originalname);
  }
});

const upload = multer({
  storage,
  fileFilter: (req, file, cb) => {
    const ext = path.extname(file.originalname || '').toLowerCase();
    const isJsonByExt = ext === '.json';
    const isPdfByExt = ext === '.pdf';
    const isJsonByMime = file.mimetype === 'application/json' || file.mimetype === 'text/json';
    const isPdfByMime = file.mimetype === 'application/pdf';

    if (isJsonByExt || isPdfByExt || isJsonByMime || isPdfByMime) {
      cb(null, true);
    } else {
      cb(new Error(`Invalid file type (${file.mimetype || 'unknown'}). Only PDF and JSON allowed`));
    }
  },
  limits: {
    fileSize: 16 * 1024 * 1024 // 16MB
  }
});

// Verify certificate by uploading file
router.post('/file', upload.single('file'), async (req, res) => {
  let uploadPath = null;

  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No file provided' });
    }

    uploadPath = req.file.path;

    let verificationHash = '';
    let certId = 'unknown';
    let parsedCertificate = null;

    const ext = path.extname(req.file.originalname || '').toLowerCase();
    const isJsonFile = req.file.mimetype === 'application/json' || req.file.mimetype === 'text/json' || ext === '.json';
    const isPdfFile = req.file.mimetype === 'application/pdf' || ext === '.pdf';

    if (isJsonFile) {
      const fileContent = await readFile(uploadPath, 'utf-8');
      parsedCertificate = JSON.parse(fileContent);
      verificationHash = extractVerificationHashFromJson(parsedCertificate);
      certId = parsedCertificate.cert_id || 'unknown';
      console.log('JSON certificate loaded:', certId);
    } else if (isPdfFile) {
      if (!pdfParse) {
        return res.status(500).json({
          error: 'PDF verification is not available. Install backend dependency: pdf-parse'
        });
      }

      const pdfBuffer = await readFile(uploadPath);
      const parsedPdf = await pdfParse(pdfBuffer);
      const pdfText = parsedPdf?.text || '';
      parsedCertificate = extractPayloadCertificateFromPdfText(pdfText);

      if (parsedCertificate) {
        verificationHash = extractVerificationHashFromJson(parsedCertificate);
        certId = parsedCertificate.cert_id || 'unknown';
        console.log('Extracted signed payload token from PDF');
      } else {
        verificationHash = extractVerificationHashFromPdfText(pdfText);
      }

      console.log('PDF certificate uploaded:', req.file.originalname);
    } else {
      return res.status(400).json({
        error: `Unsupported certificate format (${req.file.mimetype || 'unknown'})`
      });
    }

    console.log('Extracted verification hash:', verificationHash);
    console.log('Extracted cert ID:', certId);

    verificationHash = (verificationHash || '').trim().toLowerCase();

    if (!verificationHash) {
      return res.status(400).json({
        error: 'Invalid certificate file - missing verification hash'
      });
    }

    // Get client info for logging
    const ipAddress = req.ip || req.connection.remoteAddress;
    const userAgent = req.headers['user-agent'] || 'Unknown';

    // Search for certificate in database using verification hash
    const certRecord = await supabaseClient.getCertificateByHash(verificationHash);

    console.log('Database lookup result:', certRecord ? 'Found' : 'Not found');

    if (!certRecord) {
      // Log verification attempt
      await supabaseClient.insertVerificationLog(
        certId,
        'not_found',
        ipAddress,
        userAgent
      );

      return res.status(404).json({
        status: 'NotFound',
        message: 'Certificate hash not found in database',
        cert_id: certId,
        details: {
          signature_valid: false,
          database_match: false,
          filename: req.file.originalname
        }
      });
    }

    // Verify hash match only (source of truth for public verification)
    const hashMatches = certRecord.verification_hash === verificationHash;
    console.log('Hash matches:', hashMatches);

    // Check if certificate is revoked
    if (certRecord.status === 'Revoked') {
      await supabaseClient.insertVerificationLog(
        certRecord.cert_id || certId,
        'Revoked',
        ipAddress,
        userAgent
      );

      return res.json({
        status: 'Revoked',
        message: 'This certificate has been revoked',
        cert_id: certId,
        details: {
          device_name: certRecord.device_name,
          wipe_date: certRecord.created_at,
          signature_valid: hashMatches,
          database_match: true,
          filename: req.file.originalname
        }
      });
    }

    // Certificate is valid
    if (hashMatches) {
      await supabaseClient.insertVerificationLog(
        certRecord.cert_id || certId,
        'Verified',
        ipAddress,
        userAgent
      );

      return res.json({
        status: 'Verified',
        message: 'Certificate is valid and authentic',
        cert_id: certId,
        details: {
          device_name: certRecord.device_name,
          device_model: certRecord.device_model,
          wipe_method: certRecord.wipe_method,
          wipe_date: certRecord.wipe_start_time,
          signature_valid: true,
          database_match: true,
          filename: req.file.originalname,
          status: certRecord.status
        }
      });
    }

    // Strong local verification when full signed certificate is available.
    if (parsedCertificate) {
      const localVerification = verifyCertificateSignature(parsedCertificate);
      if (!localVerification.valid) {
        return res.status(400).json({
          status: 'Invalid',
          message: 'Certificate signature/hash validation failed',
          cert_id: certId,
          details: {
            reason: localVerification.reason,
            filename: req.file.originalname
          }
        });
      }
    }

    await supabaseClient.insertVerificationLog(
      certRecord.cert_id || certId,
      'MismatchError',
      ipAddress,
      userAgent
    );

    return res.status(400).json({
      status: 'Invalid',
      message: 'Certificate hash does not match database records',
      cert_id: certId,
      details: {
        signature_valid: false,
        database_match: false,
        filename: req.file.originalname
      }
    });
  } catch (error) {
    console.error('File verification error:', error);
    res.status(500).json({ error: 'File verification failed: ' + error.message });
  } finally {
    // Clean up uploaded file
    if (uploadPath) {
      try {
        await unlink(uploadPath);
      } catch (err) {
        console.error('Failed to delete temporary file:', err);
      }
    }
  }
});

// Verify certificate by verification hash
router.post('/hash', async (req, res) => {
  try {
    const rawHash = req.body?.hash;
    const hash = String(rawHash || '').trim().toLowerCase();
    const ipAddress = req.ip || req.connection.remoteAddress;
    const userAgent = req.headers['user-agent'] || 'Unknown';

    if (!hash) {
      return res.status(400).json({ error: 'Hash is required' });
    }

    // Search by verification hash
    const certRecord = await supabaseClient.getCertificateByHash(hash);

    if (!certRecord) {
      await supabaseClient.insertVerificationLog(
        'unknown',
        'not_found',
        ipAddress,
        userAgent
      );

      return res.status(404).json({
        status: 'NotFound',
        message: 'No certificate found with this hash'
      });
    }

    if (certRecord.status === 'Revoked') {
      await supabaseClient.insertVerificationLog(
        certRecord.cert_id,
        'Revoked',
        ipAddress,
        userAgent
      );

      return res.json({
        status: 'Revoked',
        message: 'This certificate has been revoked',
        cert_id: certRecord.cert_id,
        details: {
          device_name: certRecord.device_name,
          wipe_date: certRecord.created_at
        }
      });
    }

    await supabaseClient.insertVerificationLog(
      certRecord.cert_id,
      'Verified',
      ipAddress,
      userAgent
    );

    res.json({
      status: 'Verified',
      message: 'Certificate found and Verified',
      cert_id: certRecord.cert_id,
      details: {
        device_name: certRecord.device_name,
        wipe_method: certRecord.wipe_method,
        wipe_date: certRecord.wipe_start_time
      }
    });
  } catch (error) {
    console.error('Hash verification error:', error);
    res.status(500).json({ error: 'Verification failed' });
  }
});

export default router;

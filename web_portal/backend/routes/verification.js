// web_portal/backend/routes/verification.js
import express from 'express';
import multer from 'multer';
import { unlink, readFile } from 'fs/promises';
import supabaseClient from '../lib/supabaseClient.js';

const router = express.Router();

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
    const allowedTypes = ['application/pdf', 'application/json'];
    if (allowedTypes.includes(file.mimetype)) {
      cb(null, true);
    } else {
      cb(new Error('Invalid file type. Only PDF and JSON allowed'));
    }
  },
  limits: {
    fileSize: 16 * 1024 * 1024 // 16MB
  }
});

// Verify certificate by ID
router.get('/id/:certId', async (req, res) => {
  try {
    const { certId } = req.params;

    console.log('Verifying certificate ID:', certId);

    // Get client info for logging
    const ipAddress = req.ip || req.connection.remoteAddress;
    const userAgent = req.headers['user-agent'] || 'Unknown';

    // Fetch certificate from database
    const certRecord = await supabaseClient.getCertificateById(certId);

    console.log('Certificate record found:', certRecord ? 'Yes' : 'No');
    if (certRecord) {
      console.log('Certificate status:', certRecord.status);
      console.log('Certificate cert_id:', certRecord.cert_id);
    }

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
        message: 'No certificate found with this ID',
        cert_id: certId
      });
    }

    // Check status
    if (certRecord.status === 'Revoked') {
      await supabaseClient.insertVerificationLog(
        certId,
        'Revoked',
        ipAddress,
        userAgent
      );

      return res.json({
        status: 'Revoked',
        message: 'This certificate has been Revoked',
        cert_id: certId,
        details: {
          device_name: certRecord.device_name,
          wipe_date: certRecord.created_at
        }
      });
    }

    // Log successful verification
    await supabaseClient.insertVerificationLog(
      certId,
      'Verified',
      ipAddress,
      userAgent
    );

    res.json({
      status: 'Verified',
      message: 'Certificate is valid and authentic',
      cert_id: certId,
      details: {
        device_name: certRecord.device_name,
        device_model: certRecord.device_model,
        wipe_method: certRecord.wipe_method,
        wipe_date: certRecord.wipe_start_time,
        status: certRecord.status
      }
    });
  } catch (error) {
    console.error('Verification error:', error);
    res.status(500).json({ error: 'Verification failed' });
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

    // Check file type and handle accordingly
    if (req.file.mimetype === 'application/pdf') {
      return res.status(400).json({
        error: 'PDF files are not supported for upload verification. Please use the QR scan feature or enter the certificate ID manually.'
      });
    }

    // Read and parse the certificate file (assuming JSON)
    const fileContent = await readFile(uploadPath, 'utf-8');
    const certificate = JSON.parse(fileContent);

    console.log('Certificate loaded:', certificate.cert_id);

    // Extract verification hash from certificate
    const verificationHash = certificate._signature?.verification_hash;
    const certId = certificate.cert_id;

    console.log('Extracted verification hash:', verificationHash);
    console.log('Extracted cert ID:', certId);

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
        message: 'Certificate not found in database',
        cert_id: certId,
        details: {
          signature_valid: false,
          database_match: false,
          filename: req.file.originalname
        }
      });
    }

    // Verify certificate details match
    const certIdMatches = certRecord.cert_id === certId;
    const hashMatches = certRecord.verification_hash === verificationHash;

    console.log('Certificate ID matches:', certIdMatches);
    console.log('Hash matches:', hashMatches);

    // Check if certificate is revoked
    if (certRecord.status === 'Revoked') {
      await supabaseClient.insertVerificationLog(
        certId,
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
    if (certIdMatches && hashMatches) {
      await supabaseClient.insertVerificationLog(
        certId,
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
    } else {
      // Certificate data mismatch
      await supabaseClient.insertVerificationLog(
        certId,
        'MismatchError',
        ipAddress,
        userAgent
      );

      return res.status(400).json({
        status: 'Invalid',
        message: 'Certificate data does not match database records',
        cert_id: certId,
        details: {
          signature_valid: hashMatches,
          database_match: certIdMatches,
          filename: req.file.originalname
        }
      });
    }
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
    const { hash } = req.body;

    if (!hash) {
      return res.status(400).json({ error: 'Hash is required' });
    }

    // Search by verification hash
    const { data, error } = await supabaseClient.client
      .from('certificates')
      .select('*')
      .eq('verification_hash', hash)
      .single();

    if (error || !data) {
      return res.status(404).json({
        status: 'NotFound',
        message: 'No certificate found with this hash'
      });
    }

    const certRecord = data;

    // Log verification
    const ipAddress = req.ip || req.connection.remoteAddress;
    const userAgent = req.headers['user-agent'] || 'Unknown';

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
// web_portal/backend/routes/verification.js
import express from 'express';
import multer from 'multer';
import { unlink } from 'fs/promises';
import { join } from 'path';
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
    
    // Get client info for logging
    const ipAddress = req.ip || req.connection.remoteAddress;
    const userAgent = req.headers['user-agent'] || 'Unknown';

    // Fetch certificate from database
    const certRecord = await supabaseClient.getCertificateById(certId);

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
    if (certRecord.status === 'revoked') {
      await supabaseClient.insertVerificationLog(
        certId,
        'revoked',
        ipAddress,
        userAgent
      );

      return res.json({
        status: 'Revoked',
        message: 'This certificate has been revoked',
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
      'verified',
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

    // Here you would implement the certificate verification logic
    // For now, we'll return a placeholder response
    // You would typically:
    // 1. Parse the file (PDF or JSON)
    // 2. Extract certificate data
    // 3. Verify signature
    // 4. Check against database

    const ipAddress = req.ip || req.connection.remoteAddress;
    const userAgent = req.headers['user-agent'] || 'Unknown';

    // Placeholder verification result
    const isValid = true;
    const message = 'Certificate verification not fully implemented';
    
    // For demonstration, assuming we extract cert_id from file
    const certId = 'demo-cert-id'; // This would come from parsing the file
    
    res.json({
      status: isValid ? 'Verified' : 'Invalid',
      message,
      details: {
        signature_valid: isValid,
        database_match: false,
        filename: req.file.originalname
      }
    });
  } catch (error) {
    console.error('File verification error:', error);
    res.status(500).json({ error: 'File verification failed' });
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
      'verified',
      ipAddress,
      userAgent
    );

    res.json({
      status: 'Verified',
      message: 'Certificate found and verified',
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
// web_portal/backend/routes/certificates.js
import express from 'express';
import { requireAuth } from './auth.js';
import supabaseClient from '../lib/supabaseClient.js';

const router = express.Router();

// Upload certificate files (JSON and PDF) to Supabase Storage via backend
router.post('/upload', requireAuth, async (req, res) => {
  try {
    const { cert_id, json_content, pdf_base64 } = req.body;
    if (!cert_id || !json_content || !pdf_base64) {
      return res.status(400).json({ error: 'cert_id, json_content, and pdf_base64 are required' });
    }

    const userId = req.user.id;
    const bucket = 'certificates';
    const jsonPath = `${userId}/${cert_id}.json`;
    const pdfPath = `${userId}/${cert_id}.pdf`;

    const client = supabaseClient.serviceClient || supabaseClient.client;

    // Upload JSON file
    const jsonBuffer = Buffer.from(typeof json_content === 'string' ? json_content : JSON.stringify(json_content));
    const { error: jsonErr } = await client.storage
      .from(bucket)
      .upload(jsonPath, jsonBuffer, { contentType: 'application/json', upsert: true });

    if (jsonErr) throw jsonErr;

    // Upload PDF file
    const pdfBuffer = Buffer.from(pdf_base64, 'base64');
    const { error: pdfErr } = await client.storage
      .from(bucket)
      .upload(pdfPath, pdfBuffer, { contentType: 'application/pdf', upsert: true });

    if (pdfErr) throw pdfErr;

    const json_url = client.storage.from(bucket).getPublicUrl(jsonPath).data.publicUrl;
    const pdf_url = client.storage.from(bucket).getPublicUrl(pdfPath).data.publicUrl;

    res.json({
      success: true,
      message: 'Files uploaded successfully',
      urls: { json_url, pdf_url }
    });
  } catch (error) {
    console.error('Certificate storage upload error:', error);
    res.status(500).json({ error: 'Storage upload failed', details: error.message });
  }
});

// Create/register a new certificate
router.post('/', requireAuth, async (req, res) => {
  try {
    const {
      cert_id,
      device_name,
      device_model,
      wipe_method,
      wipe_start_time,
      wipe_end_time,
      status,
      verification_hash,
      certificate_data
    } = req.body;

    if (!cert_id) {
      return res.status(400).json({ error: 'cert_id is required' });
    }

    // Insert certificate into database
    const { data, error } = await supabaseClient.client
      .from('certificates')
      .insert({
        cert_id,
        user_id: req.user.id,
        device_name: device_name || 'Unknown Device',
        device_model: device_model || 'Unknown Model',
        wipe_method: wipe_method || 'Unknown',
        wipe_start_time: wipe_start_time || new Date().toISOString(),
        wipe_end_time: wipe_end_time || new Date().toISOString(),
        status: status || 'Verified',
        verification_hash: verification_hash || null,
        certificate_data: certificate_data || null
      })
      .select()
      .single();

    if (error) {
      console.error('Certificate creation error:', error);
      return res.status(500).json({ error: 'Failed to create certificate', details: error });
    }

    res.status(201).json({
      message: 'Certificate created successfully',
      certificate: data
    });
  } catch (error) {
    console.error('Certificate creation error:', error);
    res.status(500).json({ error: 'Failed to create certificate' });
  }
});

// List user's certificates
router.get('/', requireAuth, async (req, res) => {
  try {
    const limit = parseInt(req.query.limit) || 50;
    const offset = parseInt(req.query.offset) || 0;

    const certificates = await supabaseClient.getUserCertificates(
      req.user.id,
      limit,
      offset
    );

    res.json({
      certificates,
      total: certificates.length,
      limit,
      offset
    });
  } catch (error) {
    console.error('Certificate list error:', error);
    res.status(500).json({ error: 'Failed to fetch certificates' });
  }
});

// Get specific certificate
router.get('/:certId', requireAuth, async (req, res) => {
  try {
    const { certId } = req.params;
    
    const cert = await supabaseClient.getCertificateById(certId);

    if (!cert) {
      return res.status(404).json({ error: 'Certificate not found' });
    }

    // Verify ownership
    if (cert.user_id !== req.user.id) {
      return res.status(403).json({ error: 'Unauthorized' });
    }

    res.json({ certificate: cert });
  } catch (error) {
    console.error('Certificate fetch error:', error);
    res.status(500).json({ error: 'Failed to fetch certificate' });
  }
});

// Download certificate file
router.get('/:certId/download', requireAuth, async (req, res) => {
  try {
    const { certId } = req.params;
    const fileType = req.query.type || 'pdf';

    if (!['pdf', 'json'].includes(fileType)) {
      return res.status(400).json({ error: 'Invalid file type' });
    }

    // Fetch certificate to verify ownership
    const cert = await supabaseClient.getCertificateById(certId);

    if (!cert) {
      return res.status(404).json({ error: 'Certificate not found' });
    }

    if (cert.user_id !== req.user.id) {
      return res.status(403).json({ error: 'Unauthorized' });
    }

    // Get signed URL
    const config = req.app.get('config');
    const url = await supabaseClient.getCertificateFileUrl(
      cert.user_id,
      certId,
      fileType,
      config.certificateBucket
    );

    if (!url) {
      return res.status(404).json({ error: 'File not found' });
    }

    res.json({ download_url: url });
  } catch (error) {
    console.error('Download error:', error);
    res.status(500).json({ error: 'Failed to generate download URL' });
  }
});

// Delete certificate
router.delete('/:certId', requireAuth, async (req, res) => {
  try {
    const { certId } = req.params;

    // Fetch certificate to verify ownership
    const cert = await supabaseClient.getCertificateById(certId);

    if (!cert) {
      return res.status(404).json({ error: 'Certificate not found' });
    }

    if (cert.user_id !== req.user.id) {
      return res.status(403).json({ error: 'Unauthorized' });
    }

    // Delete from database
    const { error } = await supabaseClient.client
      .from('certificates')
      .delete()
      .eq('cert_id', certId);

    if (error) {
      console.error('Delete error:', error);
      return res.status(500).json({ error: 'Failed to delete certificate' });
    }

    res.json({ message: 'Certificate deleted successfully' });
  } catch (error) {
    console.error('Delete error:', error);
    res.status(500).json({ error: 'Failed to delete certificate' });
  }
});

// Get user's certificate statistics
router.get('/stats', requireAuth, async (req, res) => {
  try {
    const certs = await supabaseClient.getUserCertificates(
      req.user.id,
      1000 // Get all for stats
    );

    // Calculate stats
    const total = certs.length;
    const verified = certs.filter(c => c.status === 'verified').length;
    const pending = certs.filter(c => c.status === 'pending').length;
    const revoked = certs.filter(c => c.status === 'revoked').length;

    // Get wipe methods distribution
    const methods = {};
    certs.forEach(cert => {
      const method = cert.wipe_method || 'Unknown';
      methods[method] = (methods[method] || 0) + 1;
    });

    res.json({
      total_certificates: total,
      verified,
      pending,
      revoked,
      wipe_methods: methods
    });
  } catch (error) {
    console.error('Stats error:', error);
    res.status(500).json({ error: 'Failed to fetch statistics' });
  }
});

export default router;
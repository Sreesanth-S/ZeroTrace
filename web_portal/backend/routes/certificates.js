// web_portal/backend/routes/certificates.js
import express from 'express';
import { requireAuth } from './auth.js';
import supabaseClient from '../lib/supabaseClient.js';

const router = express.Router();

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
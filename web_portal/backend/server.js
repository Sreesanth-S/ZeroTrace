// web_portal/backend/server.js
import 'dotenv/config';

import express from 'express';
import cors from 'cors';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { existsSync, mkdirSync } from 'fs';

import helmet from 'helmet';
import rateLimit from 'express-rate-limit';

// Import routes
import authRoutes from './routes/auth.js';
import certificatesRoutes from './routes/certificates.js';
import verificationRoutes from './routes/verification.js';
import signingRoutes from './routes/signing.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Create Express app
const app = express();

// Security Headers via Helmet
app.use(helmet());

// Configuration
const config = {
  port: process.env.PORT || 5000,
  uploadFolder: process.env.UPLOAD_FOLDER || 'uploads',
  corsOrigins: process.env.CORS_ORIGINS?.split(',') || ['http://localhost:5173'],
  supabaseUrl: process.env.SUPABASE_URL,
  supabaseKey: process.env.SUPABASE_KEY,
  supabaseServiceKey: process.env.SUPABASE_SERVICE_KEY,
  publicKeyPath: process.env.PUBLIC_KEY_PATH || 'keys/public_key.pem',
  certificateBucket: process.env.CERTIFICATE_BUCKET || 'certificates',
  appName: process.env.APP_NAME || 'ZeroTrace',
  appVersion: process.env.APP_VERSION || '1.0.0',
};

// Ensure upload directory exists
if (!existsSync(config.uploadFolder)) {
  mkdirSync(config.uploadFolder, { recursive: true });
}

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Rate Limiters
const verifyLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 30, // Limit each IP to 30 requests per windowMs
  message: { error: 'Too many verification attempts from this IP, please try again later.' },
  standardHeaders: true,
  legacyHeaders: false,
});

const signingLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 60,
  message: { error: 'Too many signing requests from this IP, please try again later.' },
  standardHeaders: true,
  legacyHeaders: false,
});

// CORS configuration
app.use(cors({
  origin: config.corsOrigins,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'apikey'],
  credentials: true
}));

// Make config available to routes
app.set('config', config);

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    version: config.appVersion
  });
});

// Register routes with rate limiting
app.use('/api/auth', authRoutes);
app.use('/api/certificates', certificatesRoutes);
app.use('/api/certificates', signingLimiter, signingRoutes);
app.use('/api/verify', verifyLimiter, verificationRoutes);

// Error handlers
app.use((req, res) => {
  res.status(404).json({ error: 'Not found' });
});

app.use((err, req, res, next) => {
  console.error('Error:', err);
  res.status(500).json({ error: 'Internal server error' });
});

// Start server
app.listen(config.port, () => {
  console.log(`Server running on port ${config.port}`);
  console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
});

export default app;
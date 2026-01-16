import dotenv from 'dotenv';
dotenv.config();

import express from 'express';
import cors from 'cors';
import axios from 'axios';
import path from 'path';
import { fileURLToPath } from 'url';

// Get __dirname equivalent for ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Import routes
import enrolmentRoutes from './routes/enrolment.js';
import demographicRoutes from './routes/demographic.js';
import biometricRoutes from './routes/biometric.js';
import dashboardRoutes from './routes/dashboard.js';
import aiRoutes from './routes/ai.js';
import hotspotsRoutes from './routes/hotspots.js';

const app = express();
const PORT = process.env.PORT || 3001;
const ML_BACKEND_URL = process.env.ML_BACKEND_URL || 'http://localhost:8000';

// Middleware
app.use(cors());
app.use(express.json());

// Serve static files from public folder
app.use(express.static(path.join(__dirname, 'public')));

// Routes
app.use('/api/enrolment', enrolmentRoutes);
app.use('/api/demographic', demographicRoutes);
app.use('/api/biometric', biometricRoutes);
app.use('/api/dashboard', dashboardRoutes);
app.use('/api/ai', aiRoutes);
app.use('/api/hotspots', hotspotsRoutes);

// ML Backend Proxy - Forward requests to Python FastAPI ML backend
app.use('/api/ml', async (req, res) => {
  try {
    const targetUrl = `${ML_BACKEND_URL}${req.originalUrl}`;
    console.log(`🔀 Proxying to ML Backend: ${req.method} ${targetUrl}`);

    const response = await axios({
      method: req.method,
      url: targetUrl,
      data: req.body,
      headers: {
        'Content-Type': 'application/json',
        ...req.headers
      },
      timeout: 120000 // 2 minute timeout for long-running ML tasks
    });

    res.status(response.status).json(response.data);
  } catch (error) {
    if (error.response) {
      res.status(error.response.status).json(error.response.data);
    } else if (error.code === 'ECONNREFUSED') {
      res.status(503).json({
        error: 'ML Backend Unavailable',
        message: 'The ML backend server is not running. Start it with: cd ml_backend && python -m uvicorn main:app --reload'
      });
    } else {
      console.error('ML Proxy Error:', error.message);
      res.status(500).json({ error: 'ML proxy error', message: error.message });
    }
  }
});

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Error:', err.message);
  res.status(500).json({
    error: 'Internal server error',
    message: err.message
  });
});

app.listen(PORT, () => {
  console.log(`🚀 UIDAI Backend Server running on http://localhost:${PORT}`);
  console.log(`📊 Dashboard API: http://localhost:${PORT}/api/dashboard`);
  console.log(`🤖 AI API: http://localhost:${PORT}/api/ai`);
  console.log(`🧠 ML API (proxied): http://localhost:${PORT}/api/ml → ${ML_BACKEND_URL}`);
  console.log(`🗺️  Hotspots API: http://localhost:${PORT}/api/hotspots`);
  console.log(`📈 Spatial Analysis: http://localhost:${PORT}/api/hotspots/spatial`);
});

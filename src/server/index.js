/**
 * UIDAI Analytics Dashboard - Express Server
 * Main entry point for the backend API
 */

require('dotenv').config();

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const path = require('path');

// Import routes
const apiRoutes = require('./routes/api');
const enrollmentRoutes = require('./routes/enrollment');
const geospatialRoutes = require('./routes/geospatial');
const groqRoutes = require('./routes/groq');
const dataRoutes = require('./routes/data');
const penetrationRoutes = require('./routes/penetration');

const app = express();
const PORT = process.env.PORT || 3000;

// ===================================
// Middleware
// ===================================

// Security headers
app.use(helmet({
    contentSecurityPolicy: false // Allow inline scripts for development
}));

// CORS
app.use(cors({
    origin: ['http://localhost:3000', 'http://127.0.0.1:3000', 'http://localhost:5500'],
    credentials: true
}));

// Request logging
app.use(morgan('dev'));

// Body parsing
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Serve static files from public folder
app.use(express.static(path.join(__dirname, '../../public')));

// ===================================
// API Routes
// ===================================

app.use('/api', apiRoutes);
app.use('/api/enrollment', enrollmentRoutes);
app.use('/api/geospatial', geospatialRoutes);
app.use('/api/groq', groqRoutes);
app.use('/api/data', dataRoutes);
app.use('/api/penetration', penetrationRoutes);

// ===================================
// Health Check
// ===================================

app.get('/health', (req, res) => {
    res.json({
        status: 'online',
        timestamp: new Date().toISOString(),
        services: {
            backend: 'online',
            uidaiApi: process.env.UIDAI_API_KEY ? 'configured' : 'missing',
            groqApi: process.env.GROQ_API_KEY_1 ? 'configured' : 'missing'
        }
    });
});

// ===================================
// Error Handling
// ===================================

// 404 Handler
app.use((req, res, next) => {
    res.status(404).json({
        error: 'Not Found',
        message: `Route ${req.method} ${req.url} not found`
    });
});

// Global error handler
app.use((err, req, res, next) => {
    console.error('Error:', err.message);
    res.status(err.status || 500).json({
        error: err.message || 'Internal Server Error',
        stack: process.env.NODE_ENV === 'development' ? err.stack : undefined
    });
});

// ===================================
// Start Server
// ===================================

app.listen(PORT, () => {
    console.log('='.repeat(50));
    console.log('🚀 UIDAI Analytics Dashboard Server');
    console.log('='.repeat(50));
    console.log(`📡 Server running on http://localhost:${PORT}`);
    console.log(`🌍 Environment: ${process.env.NODE_ENV || 'development'}`);
    console.log('');
    console.log('📊 API Endpoints:');
    console.log(`   GET  /health              - Health check`);
    console.log(`   GET  /api/status          - API status`);
    console.log(`   GET  /api/enrollment/*    - Enrollment data`);
    console.log(`   GET  /api/geospatial/*    - Geospatial data`);
    console.log(`   POST /api/groq/*          - Groq AI services`);
    console.log('='.repeat(50));
});

module.exports = app;

/**
 * Main API Routes
 * General status and information endpoints
 */

const express = require('express');
const router = express.Router();

// API Status
router.get('/status', (req, res) => {
    res.json({
        status: 'online',
        version: '1.0.0',
        timestamp: new Date().toISOString(),
        endpoints: {
            enrollment: '/api/enrollment',
            geospatial: '/api/geospatial',
            groq: '/api/groq'
        },
        dataSources: {
            enrollmentData: {
                name: 'Enrollment Data',
                description: 'Monthly enrollment by state, district, age groups',
                status: process.env.UIDAI_API_KEY ? 'ready' : 'api_key_missing'
            },
            demographicUpdates: {
                name: 'Demographic Updates',
                description: 'Demographic update statistics',
                status: process.env.UIDAI_API_KEY ? 'ready' : 'api_key_missing'
            },
            biometricUpdates: {
                name: 'Biometric Updates',
                description: 'Biometric update records',
                status: process.env.UIDAI_API_KEY ? 'ready' : 'api_key_missing'
            }
        }
    });
});

// API Keys status (masks actual keys)
router.get('/keys-status', (req, res) => {
    const maskKey = (key) => {
        if (!key) return 'NOT_SET';
        return key.substring(0, 8) + '...' + key.substring(key.length - 4);
    };

    res.json({
        uidai: {
            configured: !!process.env.UIDAI_API_KEY,
            masked: maskKey(process.env.UIDAI_API_KEY)
        },
        groq: {
            key1: { configured: !!process.env.GROQ_API_KEY_1, masked: maskKey(process.env.GROQ_API_KEY_1) },
            key2: { configured: !!process.env.GROQ_API_KEY_2, masked: maskKey(process.env.GROQ_API_KEY_2) },
            key3: { configured: !!process.env.GROQ_API_KEY_3, masked: maskKey(process.env.GROQ_API_KEY_3) },
            key4: { configured: !!process.env.GROQ_API_KEY_4, masked: maskKey(process.env.GROQ_API_KEY_4) }
        }
    });
});

module.exports = router;

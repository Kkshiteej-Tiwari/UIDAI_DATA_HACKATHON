/**
 * Server Configuration
 * Centralized configuration management
 */

require('dotenv').config();

const config = {
    // Server
    server: {
        port: process.env.PORT || 3000,
        env: process.env.NODE_ENV || 'development'
    },

    // UIDAI API
    uidai: {
        apiKey: process.env.UIDAI_API_KEY,
        baseUrl: process.env.UIDAI_BASE_URL || 'https://api.data.gov.in/resource',
        resources: {
            enrollment: process.env.ENROLLMENT_DATA_RESOURCE_ID,
            demographic: process.env.DEMOGRAPHIC_DATA_RESOURCE_ID,
            biometric: process.env.BIOMETRIC_DATA_RESOURCE_ID
        }
    },

    // Groq AI
    groq: {
        keys: [
            process.env.GROQ_API_KEY_1,
            process.env.GROQ_API_KEY_2,
            process.env.GROQ_API_KEY_3,
            process.env.GROQ_API_KEY_4
        ].filter(Boolean),
        baseUrl: process.env.GROQ_BASE_URL || 'https://api.groq.com/openai/v1',
        models: {
            fast: 'llama-3.1-8b-instant',
            powerful: 'llama-3.3-70b-versatile',
            balanced: 'mixtral-8x7b-32768'
        }
    },

    // API Rate Limits
    rateLimit: {
        windowMs: 15 * 60 * 1000, // 15 minutes
        max: 100 // requests per window
    }
};

// Validation
const validateConfig = () => {
    const warnings = [];

    if (!config.uidai.apiKey) {
        warnings.push('⚠️  UIDAI_API_KEY not set');
    }

    if (config.groq.keys.length === 0) {
        warnings.push('⚠️  No GROQ_API_KEYs configured');
    }

    if (warnings.length > 0) {
        console.log('\n🔧 Configuration Warnings:');
        warnings.forEach(w => console.log(`   ${w}`));
        console.log('');
    }

    return warnings.length === 0;
};

config.isValid = validateConfig();

module.exports = config;

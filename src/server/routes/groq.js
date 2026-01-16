/**
 * Groq AI Routes
 * AI-powered analysis using Groq API
 */

const express = require('express');
const router = express.Router();
const axios = require('axios');

// Groq API configuration with key rotation
const GROQ_KEYS = [
    process.env.GROQ_API_KEY_1,
    process.env.GROQ_API_KEY_2,
    process.env.GROQ_API_KEY_3,
    process.env.GROQ_API_KEY_4
].filter(Boolean);

let currentKeyIndex = 0;

const getGroqKey = () => {
    if (GROQ_KEYS.length === 0) return null;
    return GROQ_KEYS[currentKeyIndex];
};

const rotateKey = () => {
    currentKeyIndex = (currentKeyIndex + 1) % GROQ_KEYS.length;
    console.log(`🔄 Rotated to Groq API key ${currentKeyIndex + 1}`);
};

// Groq API client
const createGroqClient = () => {
    const apiKey = getGroqKey();
    if (!apiKey) return null;

    return axios.create({
        baseURL: process.env.GROQ_BASE_URL || 'https://api.groq.com/openai/v1',
        headers: {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        },
        timeout: 30000
    });
};

/**
 * GET /api/groq/status
 * Check Groq API status
 */
router.get('/status', (req, res) => {
    res.json({
        success: true,
        configured: GROQ_KEYS.length > 0,
        keysAvailable: GROQ_KEYS.length,
        currentKeyIndex: currentKeyIndex + 1,
        models: ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant', 'mixtral-8x7b-32768']
    });
});

/**
 * POST /api/groq/analyze
 * Analyze enrollment data using AI
 */
router.post('/analyze', async (req, res) => {
    try {
        const { data, analysisType = 'summary' } = req.body;

        if (!data) {
            return res.status(400).json({
                error: 'Missing data',
                message: 'Please provide data to analyze'
            });
        }

        const groqClient = createGroqClient();
        if (!groqClient) {
            return res.status(500).json({
                error: 'Groq API not configured',
                message: 'No Groq API keys available'
            });
        }

        const prompts = {
            summary: `Analyze this UIDAI enrollment data and provide a brief summary of key insights: ${JSON.stringify(data)}`,
            trends: `Identify trends and patterns in this UIDAI enrollment data: ${JSON.stringify(data)}`,
            anomalies: `Detect any anomalies or unusual patterns in this enrollment data: ${JSON.stringify(data)}`,
            forecast: `Based on this enrollment data, provide forecasting insights: ${JSON.stringify(data)}`
        };

        const response = await groqClient.post('/chat/completions', {
            model: 'llama-3.3-70b-versatile',
            messages: [
                {
                    role: 'system',
                    content: 'You are a data analyst expert specializing in UIDAI Aadhaar enrollment data. Provide clear, actionable insights.'
                },
                {
                    role: 'user',
                    content: prompts[analysisType] || prompts.summary
                }
            ],
            temperature: 0.7,
            max_tokens: 1000
        });

        res.json({
            success: true,
            analysisType,
            result: response.data.choices[0].message.content,
            model: response.data.model,
            usage: response.data.usage
        });

    } catch (error) {
        // Rotate key on rate limit
        if (error.response?.status === 429) {
            rotateKey();
            return res.status(429).json({
                error: 'Rate limited',
                message: 'API key rotated, please retry',
                retryAfter: 1
            });
        }

        console.error('❌ Groq API Error:', error.message);
        res.status(500).json({
            error: 'AI analysis failed',
            message: error.message
        });
    }
});

/**
 * POST /api/groq/chat
 * Interactive chat about enrollment data
 */
router.post('/chat', async (req, res) => {
    try {
        const { message, context } = req.body;

        if (!message) {
            return res.status(400).json({
                error: 'Missing message',
                message: 'Please provide a message'
            });
        }

        const groqClient = createGroqClient();
        if (!groqClient) {
            return res.status(500).json({
                error: 'Groq API not configured'
            });
        }

        const response = await groqClient.post('/chat/completions', {
            model: 'llama-3.1-8b-instant',
            messages: [
                {
                    role: 'system',
                    content: `You are an AI assistant for the UIDAI Analytics Dashboard. Help users understand Aadhaar enrollment data, geographic hotspots, and provide insights. ${context ? `Context: ${JSON.stringify(context)}` : ''}`
                },
                {
                    role: 'user',
                    content: message
                }
            ],
            temperature: 0.8,
            max_tokens: 500
        });

        res.json({
            success: true,
            response: response.data.choices[0].message.content,
            model: 'llama-3.1-8b-instant'
        });

    } catch (error) {
        if (error.response?.status === 429) {
            rotateKey();
        }
        res.status(500).json({ error: error.message });
    }
});

module.exports = router;

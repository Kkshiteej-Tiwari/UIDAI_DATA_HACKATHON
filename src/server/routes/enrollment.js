/**
 * Enrollment Data Routes
 * Fetches enrollment data from UIDAI APIs (data.gov.in)
 */

const express = require('express');
const router = express.Router();
const axios = require('axios');

const UIDAI_API_KEY = process.env.UIDAI_API_KEY;
const UIDAI_BASE_URL = process.env.UIDAI_BASE_URL || 'https://api.data.gov.in/resource';

// REAL UIDAI Resource IDs from data.gov.in (verified)
const RESOURCE_IDS = {
    // Aadhaar Monthly Enrollment Data (State, District, Pincode, Age groups)
    monthlyEnrollment: 'ecd49b12-3084-4521-8f7e-ca8bf72069ba',

    // Aadhaar Biometric Monthly Update Data (State, District, Bio updates)
    biometricUpdate: '65454dab-1517-40a3-ac1d-47d4dfe6891c',

    // Aadhaar Demographic Update Data
    demographicUpdate: 'd424aa50-3b06-4c46-a7d6-f4eaced08420'
};

// Axios instance for UIDAI API
const uidaiApi = axios.create({
    baseURL: UIDAI_BASE_URL,
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json'
    }
});

/**
 * GET /api/enrollment/uidai-data
 * Fetch Aadhaar enrollment data from UIDAI API
 */
router.get('/uidai-data', async (req, res) => {
    const { resourceId, limit = 100, offset = 0, state, district } = req.query;

    // Use provided resourceId or default to monthly enrollment
    const targetResourceId = resourceId || RESOURCE_IDS.monthlyEnrollment;

    try {
        console.log('\n' + '='.repeat(60));
        console.log('📊 UIDAI API Request');
        console.log('='.repeat(60));
        console.log(`Resource ID: ${targetResourceId}`);
        console.log(`API Key: ${UIDAI_API_KEY ? UIDAI_API_KEY.substring(0, 10) + '...' : 'NOT SET'}`);

        if (!UIDAI_API_KEY) {
            throw new Error('UIDAI API key not configured');
        }

        const params = {
            'api-key': UIDAI_API_KEY,
            format: 'json',
            limit: parseInt(limit),
            offset: parseInt(offset)
        };

        // Add state filter if provided
        if (state) {
            params['filters[state]'] = state;
        }
        if (district) {
            params['filters[district]'] = district;
        }

        const response = await uidaiApi.get(`/${targetResourceId}`, { params });

        // 1) Log HTTP status
        console.log(`\n1️⃣ HTTP Status: ${response.status}`);

        // 2) Log response keys
        console.log(`\n2️⃣ Response Keys: ${Object.keys(response.data).join(', ')}`);

        // Get records
        const records = response.data.records || response.data.data || [];

        // 3) Log first 3 records
        console.log('\n3️⃣ First 3 Records (Sample):');
        const sampleRecords = records.slice(0, 3);
        sampleRecords.forEach((record, i) => {
            console.log(`   Record ${i + 1}:`, JSON.stringify(record, null, 2));
        });

        // Parse and extract relevant fields (mapping to expected schema)
        const parsedRecords = records.map(record => {
            // Calculate total enrollments from age groups if available
            const age0_5 = parseInt(record.age_0_5) || 0;
            const age5_17 = parseInt(record.age_5_17) || 0;
            const age18Plus = parseInt(record.age_18_greater) || 0;
            const totalEnrollments = age0_5 + age5_17 + age18Plus;

            return {
                state_name: record.state || record.State || null,
                district_name: record.district || record.District || null,
                pincode: record.pincode || record.Pincode || null,
                total_enrollments: totalEnrollments > 0 ? totalEnrollments : null,
                age_0_5: age0_5 || null,
                age_5_17: age5_17 || null,
                age_18_plus: age18Plus || null,
                date: record.date || record.Date || null,
                month: record.date ? record.date.substring(0, 7) : null, // Extract YYYY-MM
                raw: record
            };
        });

        // Check if district-level data is available
        const hasDistrictData = parsedRecords.some(r => r.district_name !== null);
        if (!hasDistrictData && records.length > 0) {
            console.log('\n⚠️ District-level enrollment not available in this endpoint');
        }

        console.log('\n4️⃣ Parsed Fields (first 3):');
        parsedRecords.slice(0, 3).forEach((record, i) => {
            console.log(`   Parsed ${i + 1}:`, {
                state_name: record.state_name,
                district_name: record.district_name,
                total_enrollments: record.total_enrollments,
                month: record.month
            });
        });

        console.log('='.repeat(60) + '\n');

        res.json({
            success: true,
            httpStatus: response.status,
            source: 'UIDAI API (data.gov.in)',
            resourceId: targetResourceId,
            totalCount: response.data.count || response.data.total || records.length,
            recordsReturned: records.length,
            hasDistrictData,
            availableFields: records.length > 0 ? Object.keys(records[0]) : [],
            sampleRecords: sampleRecords,
            parsedRecords: parsedRecords.slice(0, 50) // Return first 50 parsed
        });

    } catch (error) {
        console.error('\n❌ UIDAI API Error:');
        console.error('   Status:', error.response?.status || 'N/A');
        console.error('   Message:', error.message);
        console.error('   Full Error:', error.response?.data || error);

        res.status(error.response?.status || 500).json({
            success: false,
            error: 'UIDAI API unreachable – check credentials or CORS',
            httpStatus: error.response?.status || 500,
            message: error.message,
            details: error.response?.data || null
        });
    }
});

/**
 * GET /api/enrollment/biometric-updates
 * Fetch biometric update data
 */
router.get('/biometric-updates', async (req, res) => {
    const { limit = 100, offset = 0, state } = req.query;

    try {
        const params = {
            'api-key': UIDAI_API_KEY,
            format: 'json',
            limit: parseInt(limit),
            offset: parseInt(offset)
        };

        if (state) {
            params['filters[state]'] = state;
        }

        console.log('📊 Fetching Biometric Update Data...');
        const response = await uidaiApi.get(`/${RESOURCE_IDS.biometricUpdate}`, { params });

        const records = response.data.records || [];

        res.json({
            success: true,
            httpStatus: response.status,
            resourceId: RESOURCE_IDS.biometricUpdate,
            totalCount: response.data.count || records.length,
            recordsReturned: records.length,
            records: records
        });

    } catch (error) {
        console.error('❌ Biometric API Error:', error.message);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * GET /api/enrollment/available-datasets
 * List available UIDAI datasets
 */
router.get('/available-datasets', (req, res) => {
    res.json({
        success: true,
        apiKey: UIDAI_API_KEY ? 'configured' : 'missing',
        datasets: [
            {
                name: 'Aadhaar Monthly Enrollment',
                resourceId: RESOURCE_IDS.monthlyEnrollment,
                description: 'Monthly enrollment by state, district, pincode, age groups',
                fields: ['date', 'state', 'district', 'pincode', 'age_0_5', 'age_5_17', 'age_18_greater']
            },
            {
                name: 'Aadhaar Biometric Updates',
                resourceId: RESOURCE_IDS.biometricUpdate,
                description: 'Biometric update data by state, district',
                fields: ['date', 'state', 'district', 'pincode', 'bio_age_5_17', 'bio_age_17_']
            },
            {
                name: 'Aadhaar Demographic Updates',
                resourceId: RESOURCE_IDS.demographicUpdate,
                description: 'Demographic update statistics'
            }
        ],
        usage: {
            enrollmentData: 'GET /api/enrollment/uidai-data?limit=100&state=Maharashtra',
            biometricData: 'GET /api/enrollment/biometric-updates?limit=100',
            withFilters: 'GET /api/enrollment/uidai-data?state=Kerala&district=Ernakulam'
        }
    });
});

/**
 * GET /api/enrollment/test
 * Test endpoint to verify API connectivity
 */
router.get('/test', async (req, res) => {
    try {
        console.log('Testing UIDAI API connectivity...');

        const response = await uidaiApi.get(`/${RESOURCE_IDS.monthlyEnrollment}`, {
            params: {
                'api-key': UIDAI_API_KEY,
                format: 'json',
                limit: 1
            }
        });

        res.json({
            success: true,
            message: 'UIDAI API is reachable',
            httpStatus: response.status,
            recordCount: response.data.count || 'N/A',
            sampleKeys: Object.keys(response.data)
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            message: 'UIDAI API unreachable',
            error: error.message,
            details: error.response?.data
        });
    }
});

module.exports = router;

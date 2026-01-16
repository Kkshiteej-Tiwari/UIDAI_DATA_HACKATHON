/**
 * Data Routes - Serve processed CSV data
 * Endpoints for penetration, enrollment, and feature data
 */

const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');
const csv = require('csv-parser');

// Paths to processed data
const PROCESSED_DIR = path.join(__dirname, '../data/processed');
const FEATURES_DIR = path.join(__dirname, '../data/features');

// Cache for CSV data (load once)
let stateDataCache = null;
let districtDataCache = null;
let enrollmentMasterCache = null;

/**
 * Load CSV file into memory
 */
async function loadCSV(filePath) {
    return new Promise((resolve, reject) => {
        const records = [];

        if (!fs.existsSync(filePath)) {
            reject(new Error(`File not found: ${filePath}`));
            return;
        }

        fs.createReadStream(filePath)
            .pipe(csv())
            .on('data', (row) => records.push(row))
            .on('end', () => resolve(records))
            .on('error', (error) => reject(error));
    });
}

/**
 * GET /api/data/penetration/states
 * Returns state-level penetration data
 */
router.get('/penetration/states', async (req, res) => {
    try {
        // Load from cache or file
        if (!stateDataCache) {
            const filePath = path.join(FEATURES_DIR, 'penetration_by_state.csv');
            stateDataCache = await loadCSV(filePath);
            console.log(`📊 Loaded ${stateDataCache.length} state records`);
        }

        // Parse numeric fields
        const data = stateDataCache.map(row => ({
            state: row.STATE,
            total_enrollment: parseInt(row.TOTAL_ENROLLMENT) || 0,
            age_0_5: parseInt(row.AGE_0_5) || 0,
            age_5_17: parseInt(row.AGE_5_17) || 0,
            age_18_plus: parseInt(row.AGE_18_PLUS) || 0,
            population: parseInt(row.POPULATION) || null,
            penetration_pct: parseFloat(row.PENETRATION_PCT) || null,
            monthly_velocity: parseInt(row.MONTHLY_VELOCITY) || null,
            months_of_data: parseInt(row.MONTHS_OF_DATA) || 0
        }));

        res.json({
            success: true,
            source: 'processed_csv',
            count: data.length,
            data: data
        });

    } catch (error) {
        console.error('❌ Error loading state data:', error.message);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * GET /api/data/penetration/districts
 * Returns district-level penetration data
 */
router.get('/penetration/districts', async (req, res) => {
    try {
        const { state, limit = 1000 } = req.query;

        // Load from cache or file
        if (!districtDataCache) {
            const filePath = path.join(FEATURES_DIR, 'penetration_by_district.csv');
            districtDataCache = await loadCSV(filePath);
            console.log(`📊 Loaded ${districtDataCache.length} district records`);
        }

        // Filter by state if provided
        let filteredData = districtDataCache;
        if (state) {
            const stateUpper = state.toUpperCase();
            filteredData = districtDataCache.filter(row => row.STATE === stateUpper);
        }

        // Apply limit
        filteredData = filteredData.slice(0, parseInt(limit));

        // Parse numeric fields
        const data = filteredData.map(row => ({
            state: row.STATE,
            district: row.DISTRICT,
            total_enrollment: parseInt(row.TOTAL_ENROLLMENT) || 0,
            age_0_5: parseInt(row.AGE_0_5) || 0,
            age_5_17: parseInt(row.AGE_5_17) || 0,
            age_18_plus: parseInt(row.AGE_18_PLUS) || 0,
            population: parseInt(row.POPULATION) || null,
            penetration_pct: parseFloat(row.PENETRATION_PCT) || null,
            monthly_velocity: parseInt(row.MONTHLY_VELOCITY) || null,
            months_of_data: parseInt(row.MONTHS_OF_DATA) || 0
        }));

        res.json({
            success: true,
            source: 'processed_csv',
            count: data.length,
            total: districtDataCache.length,
            filter: state ? { state: state.toUpperCase() } : null,
            data: data
        });

    } catch (error) {
        console.error('❌ Error loading district data:', error.message);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * GET /api/data/enrollment
 * Returns master enrollment data
 */
router.get('/enrollment', async (req, res) => {
    try {
        const { state, district, limit = 500 } = req.query;

        // Load from cache or file
        if (!enrollmentMasterCache) {
            const filePath = path.join(PROCESSED_DIR, 'enrollment_master.csv');
            enrollmentMasterCache = await loadCSV(filePath);
            console.log(`📊 Loaded ${enrollmentMasterCache.length} enrollment records`);
        }

        // Filter
        let filteredData = enrollmentMasterCache;
        if (state) {
            const stateUpper = state.toUpperCase();
            filteredData = filteredData.filter(row => row.STATE === stateUpper);
        }
        if (district) {
            const districtUpper = district.toUpperCase();
            filteredData = filteredData.filter(row => row.DISTRICT === districtUpper);
        }

        // Apply limit
        filteredData = filteredData.slice(0, parseInt(limit));

        // Parse numeric fields
        const data = filteredData.map(row => ({
            state: row.STATE,
            district: row.DISTRICT,
            total_enrollment: parseInt(row.TOTAL_ENROLLMENT) || 0,
            age_0_5: parseInt(row.AGE_0_5) || 0,
            age_5_17: parseInt(row.AGE_5_17) || 0,
            age_18_plus: parseInt(row.AGE_18_PLUS) || 0,
            record_count: parseInt(row.RECORD_COUNT) || 0
        }));

        res.json({
            success: true,
            source: 'processed_csv',
            count: data.length,
            total: enrollmentMasterCache.length,
            data: data
        });

    } catch (error) {
        console.error('❌ Error loading enrollment data:', error.message);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * GET /api/data/summary
 * Returns summary statistics
 */
router.get('/summary', async (req, res) => {
    try {
        // Load data if not cached
        if (!stateDataCache) {
            const filePath = path.join(FEATURES_DIR, 'penetration_by_state.csv');
            stateDataCache = await loadCSV(filePath);
        }
        if (!districtDataCache) {
            const filePath = path.join(FEATURES_DIR, 'penetration_by_district.csv');
            districtDataCache = await loadCSV(filePath);
        }

        // Compute summary
        const totalEnrollment = stateDataCache.reduce((sum, row) =>
            sum + (parseInt(row.TOTAL_ENROLLMENT) || 0), 0);

        const statesWithData = stateDataCache.filter(row =>
            row.PENETRATION_PCT && parseFloat(row.PENETRATION_PCT) > 0).length;

        const districtsWithData = districtDataCache.filter(row =>
            row.PENETRATION_PCT && parseFloat(row.PENETRATION_PCT) > 0).length;

        const avgPenetration = stateDataCache
            .filter(row => row.PENETRATION_PCT)
            .reduce((sum, row, _, arr) =>
                sum + parseFloat(row.PENETRATION_PCT) / arr.length, 0);

        res.json({
            success: true,
            summary: {
                total_states: stateDataCache.length,
                total_districts: districtDataCache.length,
                total_enrollment: totalEnrollment,
                states_with_penetration: statesWithData,
                districts_with_penetration: districtsWithData,
                average_penetration_pct: avgPenetration.toFixed(6)
            }
        });

    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

/**
 * POST /api/data/refresh
 * Clear cache and reload data
 */
router.post('/refresh', (req, res) => {
    stateDataCache = null;
    districtDataCache = null;
    enrollmentMasterCache = null;

    res.json({
        success: true,
        message: 'Cache cleared. Data will be reloaded on next request.'
    });
});

module.exports = router;

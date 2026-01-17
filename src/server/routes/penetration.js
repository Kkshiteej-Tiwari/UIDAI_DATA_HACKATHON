/**
 * Penetration Routes
 * Serves processed Aadhaar penetration and EEI data from CSV
 */

const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');
const csv = require('csv-parser');

// Paths to CSV files
const PENETRATION_FILE = path.join(__dirname, '../data/features/penetration_by_state.csv');
const EEI_FILE = path.join(__dirname, '../data/features/enrollment_efficiency_by_state.csv');

/**
 * Load and parse CSV file
 */
function loadCSV(filePath) {
    return new Promise((resolve, reject) => {
        if (!fs.existsSync(filePath)) {
            reject(new Error(`File not found: ${filePath}`));
            return;
        }

        const records = [];

        fs.createReadStream(filePath)
            .pipe(csv())
            .on('data', (row) => records.push(row))
            .on('end', () => resolve(records))
            .on('error', (error) => reject(error));
    });
}

/**
 * GET /api/penetration/state
 * Returns state-level penetration data
 */
router.get('/state', async (req, res) => {
    try {
        const data = await loadCSV(PENETRATION_FILE);

        const result = data.map(row => ({
            state: row.STATE,
            penetration_pct: parseFloat(row.PENETRATION_PCT) || null,
            total_enrollment: parseInt(row.TOTAL_ENROLLMENT) || 0,
            population: parseInt(row.POPULATION) || null
        }));

        console.log(`📊 Penetration API: Returning ${result.length} states`);
        res.json(result);

    } catch (error) {
        console.error('❌ Penetration API Error:', error.message);
        res.status(500).json({
            error: 'Failed to load penetration data',
            message: error.message
        });
    }
});

/**
 * GET /api/penetration/eei
 * Returns Enrollment Efficiency Index data
 */
router.get('/eei', async (req, res) => {
    try {
        const data = await loadCSV(EEI_FILE);

        const result = data.map(row => ({
            state: row.STATE,
            actual_enrollment: parseInt(row.ACTUAL_ENROLLMENT) || 0,
            expected_enrollment: parseInt(row.EXPECTED_ENROLLMENT) || null,
            eei: parseFloat(row.EEI) || null
        }));

        // Compute statistics
        const withEEI = result.filter(r => r.eei !== null);
        const withoutEEI = result.filter(r => r.eei === null);

        console.log(`📊 EEI API: Returning ${result.length} states (${withEEI.length} with EEI, ${withoutEEI.length} missing)`);

        res.json({
            success: true,
            count: result.length,
            statesWithEEI: withEEI.length,
            statesMissingEEI: withoutEEI.length,
            data: result
        });

    } catch (error) {
        console.error('❌ EEI API Error:', error.message);
        res.status(500).json({
            success: false,
            error: 'Failed to load EEI data',
            message: error.message
        });
    }
});

module.exports = router;

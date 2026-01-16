/**
 * Penetration Routes
 * Serves processed Aadhaar penetration data from CSV
 */

const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');
const csv = require('csv-parser');

// Path to penetration CSV
const PENETRATION_FILE = path.join(__dirname, '../data/features/penetration_by_state.csv');

/**
 * Load and parse CSV file
 */
function loadPenetrationCSV() {
    return new Promise((resolve, reject) => {
        // Check if file exists
        if (!fs.existsSync(PENETRATION_FILE)) {
            reject(new Error('Penetration data file not found'));
            return;
        }

        const records = [];

        fs.createReadStream(PENETRATION_FILE)
            .pipe(csv())
            .on('data', (row) => {
                records.push({
                    state: row.STATE,
                    penetration_pct: parseFloat(row.PENETRATION_PCT) || null,
                    total_enrollment: parseInt(row.TOTAL_ENROLLMENT) || 0,
                    population: parseInt(row.POPULATION) || null
                });
            })
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
        const data = await loadPenetrationCSV();

        console.log(`📊 Penetration API: Returning ${data.length} states`);

        res.json(data);

    } catch (error) {
        console.error('❌ Penetration API Error:', error.message);
        res.status(500).json({
            error: 'Failed to load penetration data',
            message: error.message
        });
    }
});

module.exports = router;

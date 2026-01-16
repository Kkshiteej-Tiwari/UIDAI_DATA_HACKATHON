/**
 * Geospatial Routes
 * Geographic hotspot detection, penetration calculation, and mapping endpoints
 */

const express = require('express');
const router = express.Router();
const axios = require('axios');
const { DISTRICT_POPULATION, STATE_POPULATION } = require('../data/census-population');

const UIDAI_API_KEY = process.env.UIDAI_API_KEY;
const UIDAI_BASE_URL = process.env.UIDAI_BASE_URL || 'https://api.data.gov.in/resource';

// Aadhaar Monthly Enrollment Resource ID
const ENROLLMENT_RESOURCE_ID = 'ecd49b12-3084-4521-8f7e-ca8bf72069ba';

/**
 * GET /api/geospatial/penetration
 * Compute Aadhaar penetration rates by joining enrollment with census data
 */
router.get('/penetration', async (req, res) => {
    const { limit = 500, state } = req.query;

    try {
        console.log('\n' + '='.repeat(60));
        console.log('📊 COMPUTING AADHAAR PENETRATION RATES');
        console.log('='.repeat(60));

        // Step 1: Fetch enrollment data from UIDAI API
        console.log('\n1️⃣ Fetching enrollment data from UIDAI API...');

        const params = {
            'api-key': UIDAI_API_KEY,
            format: 'json',
            limit: parseInt(limit)
        };

        if (state) {
            params['filters[state]'] = state;
        }

        const response = await axios.get(`${UIDAI_BASE_URL}/${ENROLLMENT_RESOURCE_ID}`, { params });
        const records = response.data.records || [];

        console.log(`   Fetched ${records.length} enrollment records`);

        // Step 2: Aggregate enrollments by state+district
        console.log('\n2️⃣ Aggregating enrollments by state + district...');

        const aggregated = {};

        records.forEach(record => {
            const stateName = record.state || record.State;
            const districtName = record.district || record.District;

            if (!stateName || !districtName) return;

            const key = `${stateName}|${districtName}`;

            // Calculate total from age groups
            const age0_5 = parseInt(record.age_0_5) || 0;
            const age5_17 = parseInt(record.age_5_17) || 0;
            const age18Plus = parseInt(record.age_18_greater) || 0;
            const total = age0_5 + age5_17 + age18Plus;

            if (!aggregated[key]) {
                aggregated[key] = {
                    state: stateName,
                    district: districtName,
                    enrollment: 0,
                    recordCount: 0
                };
            }

            aggregated[key].enrollment += total;
            aggregated[key].recordCount += 1;
        });

        const aggregatedList = Object.values(aggregated);
        console.log(`   Aggregated into ${aggregatedList.length} state-district combinations`);

        // Step 3: Join with census population data
        console.log('\n3️⃣ Joining with Census 2011 population data...');

        const results = [];
        const invalidRows = [];
        const unmatchedDistricts = [];

        aggregatedList.forEach(item => {
            // Normalize names for matching
            const stateNormalized = normalizeStateName(item.state);
            const districtNormalized = normalizeDistrictName(item.district);

            // Look up population
            let population = null;

            if (DISTRICT_POPULATION[stateNormalized]) {
                // Try exact match first
                population = DISTRICT_POPULATION[stateNormalized][districtNormalized];

                // Try fuzzy match if not found
                if (!population) {
                    const districtKeys = Object.keys(DISTRICT_POPULATION[stateNormalized]);
                    const match = districtKeys.find(d =>
                        d.toLowerCase().includes(districtNormalized.toLowerCase()) ||
                        districtNormalized.toLowerCase().includes(d.toLowerCase())
                    );
                    if (match) {
                        population = DISTRICT_POPULATION[stateNormalized][match];
                    }
                }
            }

            // If no district population, try state-level
            if (!population && STATE_POPULATION[stateNormalized]) {
                // Use state population / estimated districts (rough estimate)
                population = Math.round(STATE_POPULATION[stateNormalized] / 30);
            }

            // Compute penetration
            let penetration = null;
            let isValid = true;
            let validationNote = null;

            if (population && population > 0) {
                penetration = (item.enrollment / population) * 100;

                // Validate penetration ∈ [0, 100]
                if (penetration < 0 || penetration > 100) {
                    isValid = false;
                    validationNote = `Invalid penetration: ${penetration.toFixed(2)}% (out of range [0,100])`;
                    invalidRows.push({
                        state: item.state,
                        district: item.district,
                        enrollment: item.enrollment,
                        population,
                        penetration,
                        reason: validationNote
                    });
                    console.log(`   ⚠️ ${validationNote}`);
                }
            } else {
                isValid = false;
                validationNote = 'Population data not available';
                unmatchedDistricts.push({
                    state: item.state,
                    district: item.district,
                    enrollment: item.enrollment
                });
            }

            results.push({
                state: item.state,
                district: item.district,
                enrollment: item.enrollment,
                population: population || null,
                penetration: penetration !== null ? parseFloat(penetration.toFixed(4)) : null,
                isValid,
                validationNote
            });
        });

        // Step 4: Sort and find low-penetration districts
        const validResults = results.filter(r => r.isValid && r.penetration !== null);
        validResults.sort((a, b) => a.penetration - b.penetration);

        const lowPenetration = validResults.slice(0, 3);

        console.log('\n4️⃣ 3 Low-Penetration Districts:');
        lowPenetration.forEach((item, i) => {
            console.log(`   ${i + 1}. ${item.district}, ${item.state}: ${item.penetration.toFixed(2)}% (${item.enrollment}/${item.population})`);
        });

        // Step 5: Summary statistics
        const avgPenetration = validResults.length > 0
            ? validResults.reduce((sum, r) => sum + r.penetration, 0) / validResults.length
            : 0;

        console.log('\n5️⃣ Summary:');
        console.log(`   Total districts processed: ${results.length}`);
        console.log(`   Valid penetration calculations: ${validResults.length}`);
        console.log(`   Invalid rows: ${invalidRows.length}`);
        console.log(`   Unmatched districts: ${unmatchedDistricts.length}`);
        console.log(`   Average penetration: ${avgPenetration.toFixed(2)}%`);
        console.log('='.repeat(60) + '\n');

        res.json({
            success: true,
            summary: {
                totalDistricts: results.length,
                validCalculations: validResults.length,
                invalidRows: invalidRows.length,
                unmatchedDistricts: unmatchedDistricts.length,
                averagePenetration: parseFloat(avgPenetration.toFixed(2))
            },
            lowPenetrationExamples: lowPenetration,
            invalidRows: invalidRows.slice(0, 10),
            unmatchedDistricts: unmatchedDistricts.slice(0, 10),
            results: results
        });

    } catch (error) {
        console.error('\n❌ Penetration Calculation Error:');
        console.error('   Message:', error.message);
        console.error('   Full Error:', error);

        res.status(500).json({
            success: false,
            error: 'Failed to compute penetration rates',
            message: error.message
        });
    }
});

/**
 * Helper: Normalize state names for matching
 */
function normalizeStateName(name) {
    if (!name) return '';

    const mappings = {
        'andhra pradesh': 'Andhra Pradesh',
        'arunachal pradesh': 'Arunachal Pradesh',
        'assam': 'Assam',
        'bihar': 'Bihar',
        'chhattisgarh': 'Chhattisgarh',
        'delhi': 'Delhi',
        'goa': 'Goa',
        'gujarat': 'Gujarat',
        'haryana': 'Haryana',
        'himachal pradesh': 'Himachal Pradesh',
        'jharkhand': 'Jharkhand',
        'karnataka': 'Karnataka',
        'kerala': 'Kerala',
        'madhya pradesh': 'Madhya Pradesh',
        'maharashtra': 'Maharashtra',
        'manipur': 'Manipur',
        'meghalaya': 'Meghalaya',
        'mizoram': 'Mizoram',
        'nagaland': 'Nagaland',
        'odisha': 'Odisha',
        'orissa': 'Odisha',
        'punjab': 'Punjab',
        'rajasthan': 'Rajasthan',
        'sikkim': 'Sikkim',
        'tamil nadu': 'Tamil Nadu',
        'telangana': 'Telangana',
        'tripura': 'Tripura',
        'uttar pradesh': 'Uttar Pradesh',
        'uttarakhand': 'Uttarakhand',
        'west bengal': 'West Bengal'
    };

    const lower = name.toLowerCase().trim();
    return mappings[lower] || name;
}

/**
 * Helper: Normalize district names for matching
 */
function normalizeDistrictName(name) {
    if (!name) return '';
    return name.trim();
}

/**
 * GET /api/geospatial/census-population
 * Get census population data for reference
 */
router.get('/census-population', (req, res) => {
    const { state } = req.query;

    if (state) {
        const stateNormalized = normalizeStateName(state);
        const districts = DISTRICT_POPULATION[stateNormalized] || {};
        const stateTotal = STATE_POPULATION[stateNormalized] || null;

        res.json({
            success: true,
            state: stateNormalized,
            statePopulation: stateTotal,
            districts: Object.entries(districts).map(([name, pop]) => ({
                district: name,
                population: pop
            }))
        });
    } else {
        res.json({
            success: true,
            availableStates: Object.keys(DISTRICT_POPULATION),
            statePopulations: STATE_POPULATION
        });
    }
});

/**
 * GET /api/geospatial/hotspots
 * Get geographic hotspots based on enrollment density
 */
router.get('/hotspots', async (req, res) => {
    try {
        const { threshold = 1000, state } = req.query;

        res.json({
            success: true,
            message: 'Hotspots endpoint ready - use /penetration for computed data',
            parameters: {
                threshold: parseInt(threshold),
                state: state || 'all'
            }
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

/**
 * GET /api/geospatial/heatmap
 * Get heatmap data for enrollment coverage
 */
router.get('/heatmap', async (req, res) => {
    try {
        res.json({
            success: true,
            message: 'Heatmap endpoint ready - use /penetration for computed data'
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

module.exports = router;

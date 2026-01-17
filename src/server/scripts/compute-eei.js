/**
 * Enrollment Efficiency Index (EEI) Computation
 * 
 * EEI compares how much a state is enrolling relative to its expected share.
 * 
 * Formula:
 * Expected Enrollment = (state_population / national_population) × national_enrollment
 * EEI = actual_enrollment / expected_enrollment
 * 
 * Interpretation:
 * EEI > 1   → state enrolling more than expected (overperforming)
 * EEI ≈ 1   → state on track
 * EEI < 1   → state underperforming
 */

const fs = require('fs');
const path = require('path');
const csv = require('csv-parser');
const { createObjectCsvWriter } = require('csv-writer');

// Paths
const FEATURES_DIR = path.join(__dirname, '../data/features');
const INPUT_FILE = path.join(FEATURES_DIR, 'penetration_by_state.csv');
const OUTPUT_FILE = path.join(FEATURES_DIR, 'enrollment_efficiency_by_state.csv');

/**
 * Load CSV file
 */
async function loadCSV(filePath) {
    return new Promise((resolve, reject) => {
        const records = [];
        fs.createReadStream(filePath)
            .pipe(csv())
            .on('data', (row) => records.push(row))
            .on('end', () => resolve(records))
            .on('error', (error) => reject(error));
    });
}

/**
 * Compute EEI for all states
 */
async function computeEEI() {
    console.log('\n' + '='.repeat(60));
    console.log('📊 ENROLLMENT EFFICIENCY INDEX (EEI) COMPUTATION');
    console.log('='.repeat(60));

    // Load state data
    console.log('\n📂 Loading state data...');
    const stateData = await loadCSV(INPUT_FILE);
    console.log(`   Loaded ${stateData.length} states`);

    // Step 1: Compute national totals (only from states with valid data)
    console.log('\n📈 Step 1: Computing national totals...');

    let national_population = 0;
    let national_enrollment = 0;
    let statesWithData = 0;
    let statesWithoutData = [];

    stateData.forEach(row => {
        const population = parseInt(row.POPULATION) || 0;
        const enrollment = parseInt(row.TOTAL_ENROLLMENT) || 0;

        if (population > 0) {
            national_population += population;
            national_enrollment += enrollment;
            statesWithData++;
        } else {
            statesWithoutData.push(row.STATE);
        }
    });

    console.log(`   National Population: ${national_population.toLocaleString()}`);
    console.log(`   National Enrollment: ${national_enrollment.toLocaleString()}`);
    console.log(`   States with data: ${statesWithData}`);
    console.log(`   States without data: ${statesWithoutData.length}`);

    if (statesWithoutData.length > 0) {
        console.log(`   Missing: ${statesWithoutData.slice(0, 5).join(', ')}${statesWithoutData.length > 5 ? '...' : ''}`);
    }

    // Step 2: Compute EEI for each state
    console.log('\n📊 Step 2: Computing EEI for each state...');

    const results = [];
    const eeiValues = [];

    stateData.forEach(row => {
        const state = row.STATE;
        const actual_enrollment = parseInt(row.TOTAL_ENROLLMENT) || 0;
        const population = parseInt(row.POPULATION) || 0;

        let expected_enrollment = null;
        let eei = null;

        if (population > 0 && national_population > 0 && national_enrollment > 0) {
            // Expected = (state_pop / national_pop) × national_enrollment
            expected_enrollment = (population / national_population) * national_enrollment;

            // EEI = actual / expected
            if (expected_enrollment > 0) {
                eei = actual_enrollment / expected_enrollment;
                eeiValues.push(eei);
            }
        }

        results.push({
            state: state,
            actual_enrollment: actual_enrollment,
            expected_enrollment: expected_enrollment !== null ? Math.round(expected_enrollment) : '',
            eei: eei !== null ? parseFloat(eei.toFixed(4)) : ''
        });
    });

    // Step 3: Compute EEI statistics
    console.log('\n📉 Step 3: EEI Statistics...');

    if (eeiValues.length > 0) {
        const minEEI = Math.min(...eeiValues);
        const maxEEI = Math.max(...eeiValues);
        const meanEEI = eeiValues.reduce((a, b) => a + b, 0) / eeiValues.length;

        console.log(`   EEI Min: ${minEEI.toFixed(4)}`);
        console.log(`   EEI Max: ${maxEEI.toFixed(4)}`);
        console.log(`   EEI Mean: ${meanEEI.toFixed(4)}`);

        // Categorize states
        const overperforming = eeiValues.filter(e => e > 1.2).length;
        const onTrack = eeiValues.filter(e => e >= 0.8 && e <= 1.2).length;
        const underperforming = eeiValues.filter(e => e < 0.8).length;

        console.log(`\n📋 EEI Categories:`);
        console.log(`   Overperforming (EEI > 1.2): ${overperforming} states`);
        console.log(`   On Track (0.8 ≤ EEI ≤ 1.2): ${onTrack} states`);
        console.log(`   Underperforming (EEI < 0.8): ${underperforming} states`);

        // Top 5 and Bottom 5
        const sortedResults = results
            .filter(r => r.eei !== '')
            .sort((a, b) => b.eei - a.eei);

        console.log(`\n🏆 Top 5 Performing States:`);
        sortedResults.slice(0, 5).forEach((r, i) => {
            console.log(`   ${i + 1}. ${r.state}: EEI = ${r.eei}`);
        });

        console.log(`\n⚠️ Bottom 5 Performing States:`);
        sortedResults.slice(-5).reverse().forEach((r, i) => {
            console.log(`   ${i + 1}. ${r.state}: EEI = ${r.eei}`);
        });
    }

    // Step 4: Write output CSV
    console.log('\n📄 Step 4: Writing output file...');

    const csvWriter = createObjectCsvWriter({
        path: OUTPUT_FILE,
        header: [
            { id: 'state', title: 'STATE' },
            { id: 'actual_enrollment', title: 'ACTUAL_ENROLLMENT' },
            { id: 'expected_enrollment', title: 'EXPECTED_ENROLLMENT' },
            { id: 'eei', title: 'EEI' }
        ]
    });

    await csvWriter.writeRecords(results);
    console.log(`   ✅ Written to: ${OUTPUT_FILE}`);
    console.log(`   Records: ${results.length}`);

    console.log('\n' + '='.repeat(60));
    console.log('✅ EEI COMPUTATION COMPLETE');
    console.log('='.repeat(60) + '\n');

    return results;
}

// Run
computeEEI().catch(console.error);

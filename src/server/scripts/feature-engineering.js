/**
 * Enhanced Feature Engineering for ML
 * 
 * Computes:
 * - Growth rate (month-over-month)
 * - Seasonality index
 * - Risk score (low penetration + high population = high risk)
 * - ML-ready feature matrix
 */

const fs = require('fs');
const path = require('path');
const csv = require('csv-parser');
const { createObjectCsvWriter } = require('csv-writer');

// Paths
const FEATURES_DIR = path.join(__dirname, '../data/features');
const ML_DIR = path.join(__dirname, '../data/ml');

// Ensure ML directory exists
if (!fs.existsSync(ML_DIR)) {
    fs.mkdirSync(ML_DIR, { recursive: true });
}

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
 * Compute risk score
 * Higher score = higher priority for intervention
 * Factors:
 *   - Low penetration (weight: 40%)
 *   - High population (weight: 30%)
 *   - Low velocity (weight: 30%)
 */
function computeRiskScore(penetration, population, velocity, maxPop, maxVel) {
    // Normalize values to 0-1 range
    const penetrationScore = penetration !== null ?
        Math.max(0, 1 - (penetration / 100)) : 1; // Lower penetration = higher risk

    const populationScore = population && maxPop ?
        population / maxPop : 0; // Higher population = higher priority

    const velocityScore = velocity !== null && maxVel ?
        Math.max(0, 1 - (velocity / maxVel)) : 0.5; // Lower velocity = higher risk

    // Weighted sum
    const riskScore = (penetrationScore * 0.4) +
        (populationScore * 0.3) +
        (velocityScore * 0.3);

    return Math.round(riskScore * 100) / 100;
}

/**
 * Compute growth rate (simulated from velocity)
 */
function computeGrowthRate(currentEnrollment, velocity, months) {
    if (!velocity || !months || months < 2) return null;

    // Estimate previous month enrollment
    const previousEstimate = currentEnrollment - velocity;
    if (previousEstimate <= 0) return null;

    // Growth rate = (current - previous) / previous * 100
    const growthRate = ((currentEnrollment - previousEstimate) / previousEstimate) * 100;
    return Math.round(growthRate * 100) / 100;
}

/**
 * Compute seasonality index (placeholder - would need monthly data)
 */
function computeSeasonalityIndex(months) {
    // Simplified: based on months of data
    // Higher variation = higher seasonality
    if (!months || months < 3) return null;

    // Return normalized index (0-1)
    // This would typically be computed from monthly variance
    return Math.round((1 - (1 / months)) * 100) / 100;
}

/**
 * Categorize penetration level
 */
function categorizePenetration(penetration) {
    if (penetration === null) return 'UNKNOWN';
    if (penetration >= 90) return 'HIGH';
    if (penetration >= 70) return 'MEDIUM';
    if (penetration >= 50) return 'LOW';
    return 'CRITICAL';
}

/**
 * Create binary features for ML
 */
function createBinaryFeatures(row) {
    const population = parseInt(row.POPULATION) || 0;
    const velocity = parseInt(row.MONTHLY_VELOCITY) || 0;
    const penetration = parseFloat(row.PENETRATION_PCT) || 0;

    return {
        is_high_population: population > 5000000 ? 1 : 0,
        is_low_penetration: penetration < 1 ? 1 : 0,
        is_high_velocity: velocity > 10000 ? 1 : 0,
        has_population_data: row.POPULATION ? 1 : 0,
        has_penetration_data: row.PENETRATION_PCT ? 1 : 0
    };
}

/**
 * Main feature engineering function
 */
async function enhanceFeatures() {
    console.log('\n' + '='.repeat(60));
    console.log('🔬 ENHANCED FEATURE ENGINEERING');
    console.log('='.repeat(60));

    // Load state and district data
    console.log('\n📂 Loading processed data...');
    const stateData = await loadCSV(path.join(FEATURES_DIR, 'penetration_by_state.csv'));
    const districtData = await loadCSV(path.join(FEATURES_DIR, 'penetration_by_district.csv'));

    console.log(`   States: ${stateData.length}`);
    console.log(`   Districts: ${districtData.length}`);

    // Find max values for normalization
    const maxPop = Math.max(...stateData.map(r => parseInt(r.POPULATION) || 0));
    const maxVel = Math.max(...stateData.map(r => parseInt(r.MONTHLY_VELOCITY) || 0));

    console.log(`   Max population: ${maxPop.toLocaleString()}`);
    console.log(`   Max velocity: ${maxVel.toLocaleString()}`);

    // Enhance state features
    console.log('\n📊 Computing enhanced state features...');
    const enhancedStates = stateData.map(row => {
        const population = parseInt(row.POPULATION) || null;
        const velocity = parseInt(row.MONTHLY_VELOCITY) || null;
        const penetration = parseFloat(row.PENETRATION_PCT) || null;
        const enrollment = parseInt(row.TOTAL_ENROLLMENT) || 0;
        const months = parseInt(row.MONTHS_OF_DATA) || 0;

        const riskScore = computeRiskScore(penetration, population, velocity, maxPop, maxVel);
        const growthRate = computeGrowthRate(enrollment, velocity, months);
        const seasonality = computeSeasonalityIndex(months);
        const category = categorizePenetration(penetration);
        const binaryFeatures = createBinaryFeatures(row);

        return {
            state: row.STATE,
            total_enrollment: enrollment,
            population: population || '',
            penetration_pct: penetration || '',
            monthly_velocity: velocity || '',
            growth_rate_pct: growthRate || '',
            seasonality_index: seasonality || '',
            risk_score: riskScore,
            penetration_category: category,
            ...binaryFeatures
        };
    });

    // Sort by risk score (highest first)
    enhancedStates.sort((a, b) => b.risk_score - a.risk_score);

    // Enhance district features
    console.log('📊 Computing enhanced district features...');
    const maxDistPop = Math.max(...districtData.map(r => parseInt(r.POPULATION) || 0));
    const maxDistVel = Math.max(...districtData.map(r => parseInt(r.MONTHLY_VELOCITY) || 0));

    const enhancedDistricts = districtData.map(row => {
        const population = parseInt(row.POPULATION) || null;
        const velocity = parseInt(row.MONTHLY_VELOCITY) || null;
        const penetration = parseFloat(row.PENETRATION_PCT) || null;
        const enrollment = parseInt(row.TOTAL_ENROLLMENT) || 0;
        const months = parseInt(row.MONTHS_OF_DATA) || 0;

        const riskScore = computeRiskScore(penetration, population, velocity, maxDistPop, maxDistVel);
        const growthRate = computeGrowthRate(enrollment, velocity, months);
        const category = categorizePenetration(penetration);
        const binaryFeatures = createBinaryFeatures(row);

        return {
            state: row.STATE,
            district: row.DISTRICT,
            total_enrollment: enrollment,
            population: population || '',
            penetration_pct: penetration || '',
            monthly_velocity: velocity || '',
            growth_rate_pct: growthRate || '',
            risk_score: riskScore,
            penetration_category: category,
            ...binaryFeatures
        };
    });

    // Sort by risk score
    enhancedDistricts.sort((a, b) => b.risk_score - a.risk_score);

    // Write enhanced state features
    console.log('\n📄 Writing enhanced features...');
    const stateWriter = createObjectCsvWriter({
        path: path.join(ML_DIR, 'state_features_ml.csv'),
        header: [
            { id: 'state', title: 'STATE' },
            { id: 'total_enrollment', title: 'TOTAL_ENROLLMENT' },
            { id: 'population', title: 'POPULATION' },
            { id: 'penetration_pct', title: 'PENETRATION_PCT' },
            { id: 'monthly_velocity', title: 'MONTHLY_VELOCITY' },
            { id: 'growth_rate_pct', title: 'GROWTH_RATE_PCT' },
            { id: 'seasonality_index', title: 'SEASONALITY_INDEX' },
            { id: 'risk_score', title: 'RISK_SCORE' },
            { id: 'penetration_category', title: 'PENETRATION_CATEGORY' },
            { id: 'is_high_population', title: 'IS_HIGH_POPULATION' },
            { id: 'is_low_penetration', title: 'IS_LOW_PENETRATION' },
            { id: 'is_high_velocity', title: 'IS_HIGH_VELOCITY' },
            { id: 'has_population_data', title: 'HAS_POPULATION_DATA' },
            { id: 'has_penetration_data', title: 'HAS_PENETRATION_DATA' }
        ]
    });
    await stateWriter.writeRecords(enhancedStates);
    console.log(`   ✅ state_features_ml.csv (${enhancedStates.length} records)`);

    // Write enhanced district features
    const districtWriter = createObjectCsvWriter({
        path: path.join(ML_DIR, 'district_features_ml.csv'),
        header: [
            { id: 'state', title: 'STATE' },
            { id: 'district', title: 'DISTRICT' },
            { id: 'total_enrollment', title: 'TOTAL_ENROLLMENT' },
            { id: 'population', title: 'POPULATION' },
            { id: 'penetration_pct', title: 'PENETRATION_PCT' },
            { id: 'monthly_velocity', title: 'MONTHLY_VELOCITY' },
            { id: 'growth_rate_pct', title: 'GROWTH_RATE_PCT' },
            { id: 'risk_score', title: 'RISK_SCORE' },
            { id: 'penetration_category', title: 'PENETRATION_CATEGORY' },
            { id: 'is_high_population', title: 'IS_HIGH_POPULATION' },
            { id: 'is_low_penetration', title: 'IS_LOW_PENETRATION' },
            { id: 'is_high_velocity', title: 'IS_HIGH_VELOCITY' },
            { id: 'has_population_data', title: 'HAS_POPULATION_DATA' },
            { id: 'has_penetration_data', title: 'HAS_PENETRATION_DATA' }
        ]
    });
    await districtWriter.writeRecords(enhancedDistricts);
    console.log(`   ✅ district_features_ml.csv (${enhancedDistricts.length} records)`);

    // Write high-risk districts (top 100)
    const highRiskWriter = createObjectCsvWriter({
        path: path.join(ML_DIR, 'high_risk_districts.csv'),
        header: [
            { id: 'state', title: 'STATE' },
            { id: 'district', title: 'DISTRICT' },
            { id: 'risk_score', title: 'RISK_SCORE' },
            { id: 'penetration_pct', title: 'PENETRATION_PCT' },
            { id: 'population', title: 'POPULATION' },
            { id: 'penetration_category', title: 'PENETRATION_CATEGORY' }
        ]
    });
    await highRiskWriter.writeRecords(enhancedDistricts.slice(0, 100));
    console.log(`   ✅ high_risk_districts.csv (top 100)`);

    // Summary
    const criticalStates = enhancedStates.filter(s => s.penetration_category === 'CRITICAL').length;
    const lowStates = enhancedStates.filter(s => s.penetration_category === 'LOW').length;
    const avgRisk = enhancedStates.reduce((sum, s) => sum + s.risk_score, 0) / enhancedStates.length;

    console.log('\n📈 Summary Statistics:');
    console.log(`   Critical penetration states: ${criticalStates}`);
    console.log(`   Low penetration states: ${lowStates}`);
    console.log(`   Average risk score: ${avgRisk.toFixed(2)}`);
    console.log(`   High-risk districts identified: ${enhancedDistricts.filter(d => d.risk_score > 0.7).length}`);

    console.log('\n' + '='.repeat(60));
    console.log('✅ ENHANCED FEATURES COMPLETE');
    console.log('='.repeat(60));
    console.log('\n📄 Output files:');
    console.log(`   • ${path.join(ML_DIR, 'state_features_ml.csv')}`);
    console.log(`   • ${path.join(ML_DIR, 'district_features_ml.csv')}`);
    console.log(`   • ${path.join(ML_DIR, 'high_risk_districts.csv')}`);
    console.log('');
}

// Run
enhanceFeatures().catch(console.error);

/**
 * UIDAI Data Pipeline
 * 
 * TASK 1: Data Ingestion - Read all CSVs from raw/enrollment/
 * TASK 2: Cleaning & Normalization - Normalize state/district names
 * TASK 3: Aggregation - Aggregate by state and state+district
 * TASK 4: Feature Engineering - Compute penetration and velocity
 */

const fs = require('fs');
const path = require('path');
const csv = require('csv-parser');
const { createObjectCsvWriter } = require('csv-writer');
const {
    normalizeStateName,
    normalizeDistrictName,
    parseNumericValue,
    parseDate
} = require('./normalize');
const { DISTRICT_POPULATION, STATE_POPULATION } = require('../data/census-population');

// Paths
const RAW_DIR = path.join(__dirname, '../data/raw/enrollment');
const PROCESSED_DIR = path.join(__dirname, '../data/processed');
const FEATURES_DIR = path.join(__dirname, '../data/features');

// Statistics tracking
const stats = {
    csvFound: 0,
    csvProcessed: 0,
    csvSkipped: 0,
    totalRecords: 0,
    statesFound: new Set(),
    districtsFound: new Set(),
    malformedFiles: []
};

// Aggregation containers
const stateAggregation = {};       // { STATE: { total, byMonth: {} } }
const districtAggregation = {};    // { STATE|DISTRICT: { state, district, total, byMonth: {} } }

/**
 * TASK 1: Read all CSV files from raw/enrollment directory
 */
async function readCSVFile(filePath) {
    return new Promise((resolve, reject) => {
        const records = [];
        let hasError = false;

        fs.createReadStream(filePath)
            .on('error', (error) => {
                hasError = true;
                reject(error);
            })
            .pipe(csv())
            .on('data', (row) => {
                records.push(row);
            })
            .on('end', () => {
                if (!hasError) {
                    resolve(records);
                }
            })
            .on('error', (error) => {
                reject(error);
            });
    });
}

/**
 * TASK 2: Clean and normalize a single record
 */
function cleanRecord(record) {
    const state = normalizeStateName(record.state);
    const district = normalizeDistrictName(record.district);

    if (!state) {
        return null; // Skip records without state
    }

    const dateInfo = parseDate(record.date);

    // Parse age group enrollments
    const age_0_5 = parseNumericValue(record.age_0_5);
    const age_5_17 = parseNumericValue(record.age_5_17);
    const age_18_plus = parseNumericValue(record.age_18_greater || record.age_18_plus);
    const totalEnrollment = age_0_5 + age_5_17 + age_18_plus;

    return {
        date: dateInfo?.date || null,
        month: dateInfo?.month || null,
        year: dateInfo?.year || null,
        state,
        district: district || 'UNKNOWN',
        pincode: record.pincode || null,
        age_0_5,
        age_5_17,
        age_18_plus,
        totalEnrollment
    };
}

/**
 * TASK 3: Aggregate enrollment data
 */
function aggregateRecord(record) {
    if (!record.state) return;

    // Track unique states and districts
    stats.statesFound.add(record.state);
    if (record.district && record.district !== 'UNKNOWN') {
        stats.districtsFound.add(`${record.state}|${record.district}`);
    }

    // Aggregate by state
    if (!stateAggregation[record.state]) {
        stateAggregation[record.state] = {
            state: record.state,
            total_enrollment: 0,
            age_0_5: 0,
            age_5_17: 0,
            age_18_plus: 0,
            record_count: 0,
            byMonth: {}
        };
    }

    stateAggregation[record.state].total_enrollment += record.totalEnrollment;
    stateAggregation[record.state].age_0_5 += record.age_0_5;
    stateAggregation[record.state].age_5_17 += record.age_5_17;
    stateAggregation[record.state].age_18_plus += record.age_18_plus;
    stateAggregation[record.state].record_count += 1;

    // Track by month for velocity calculation
    if (record.month) {
        if (!stateAggregation[record.state].byMonth[record.month]) {
            stateAggregation[record.state].byMonth[record.month] = 0;
        }
        stateAggregation[record.state].byMonth[record.month] += record.totalEnrollment;
    }

    // Aggregate by state + district
    const districtKey = `${record.state}|${record.district}`;
    if (!districtAggregation[districtKey]) {
        districtAggregation[districtKey] = {
            state: record.state,
            district: record.district,
            total_enrollment: 0,
            age_0_5: 0,
            age_5_17: 0,
            age_18_plus: 0,
            record_count: 0,
            byMonth: {}
        };
    }

    districtAggregation[districtKey].total_enrollment += record.totalEnrollment;
    districtAggregation[districtKey].age_0_5 += record.age_0_5;
    districtAggregation[districtKey].age_5_17 += record.age_5_17;
    districtAggregation[districtKey].age_18_plus += record.age_18_plus;
    districtAggregation[districtKey].record_count += 1;

    if (record.month) {
        if (!districtAggregation[districtKey].byMonth[record.month]) {
            districtAggregation[districtKey].byMonth[record.month] = 0;
        }
        districtAggregation[districtKey].byMonth[record.month] += record.totalEnrollment;
    }
}

/**
 * TASK 4: Compute penetration and velocity
 */
function computeFeatures() {
    const stateFeatures = [];
    const districtFeatures = [];

    // State-level features
    Object.values(stateAggregation).forEach(stateData => {
        // Find matching population (try different name formats)
        let population = null;
        const stateName = stateData.state;

        // Try to find population in census data
        Object.keys(STATE_POPULATION).forEach(censusState => {
            if (censusState.toUpperCase() === stateName) {
                population = STATE_POPULATION[censusState];
            }
        });

        // Compute penetration (leave blank if no population)
        const penetration = population ?
            ((stateData.total_enrollment / population) * 100).toFixed(6) :
            null;

        // Compute velocity (average monthly enrollment)
        const months = Object.keys(stateData.byMonth);
        const avgVelocity = months.length > 0 ?
            Math.round(stateData.total_enrollment / months.length) :
            null;

        stateFeatures.push({
            state: stateData.state,
            total_enrollment: stateData.total_enrollment,
            age_0_5: stateData.age_0_5,
            age_5_17: stateData.age_5_17,
            age_18_plus: stateData.age_18_plus,
            population: population || '',
            penetration_pct: penetration || '',
            monthly_velocity: avgVelocity || '',
            months_of_data: months.length
        });
    });

    // District-level features
    Object.values(districtAggregation).forEach(districtData => {
        // Find matching population
        let population = null;
        const stateName = districtData.state;
        const districtName = districtData.district;

        // Try to find population in census data
        Object.keys(DISTRICT_POPULATION).forEach(censusState => {
            if (censusState.toUpperCase() === stateName) {
                const districts = DISTRICT_POPULATION[censusState];
                Object.keys(districts).forEach(censusDistrict => {
                    if (censusDistrict.toUpperCase() === districtName) {
                        population = districts[censusDistrict];
                    }
                });
            }
        });

        // Compute penetration
        const penetration = population ?
            ((districtData.total_enrollment / population) * 100).toFixed(6) :
            null;

        // Compute velocity
        const months = Object.keys(districtData.byMonth);
        const avgVelocity = months.length > 0 ?
            Math.round(districtData.total_enrollment / months.length) :
            null;

        districtFeatures.push({
            state: districtData.state,
            district: districtData.district,
            total_enrollment: districtData.total_enrollment,
            age_0_5: districtData.age_0_5,
            age_5_17: districtData.age_5_17,
            age_18_plus: districtData.age_18_plus,
            population: population || '',
            penetration_pct: penetration || '',
            monthly_velocity: avgVelocity || '',
            months_of_data: months.length
        });
    });

    return { stateFeatures, districtFeatures };
}

/**
 * Write aggregated data to CSV
 */
async function writeEnrollmentMaster() {
    // Ensure directory exists
    if (!fs.existsSync(PROCESSED_DIR)) {
        fs.mkdirSync(PROCESSED_DIR, { recursive: true });
    }

    const masterRecords = [];

    // Add district-level data
    Object.values(districtAggregation).forEach(data => {
        masterRecords.push({
            state: data.state,
            district: data.district,
            total_enrollment: data.total_enrollment,
            age_0_5: data.age_0_5,
            age_5_17: data.age_5_17,
            age_18_plus: data.age_18_plus,
            record_count: data.record_count
        });
    });

    const csvWriter = createObjectCsvWriter({
        path: path.join(PROCESSED_DIR, 'enrollment_master.csv'),
        header: [
            { id: 'state', title: 'STATE' },
            { id: 'district', title: 'DISTRICT' },
            { id: 'total_enrollment', title: 'TOTAL_ENROLLMENT' },
            { id: 'age_0_5', title: 'AGE_0_5' },
            { id: 'age_5_17', title: 'AGE_5_17' },
            { id: 'age_18_plus', title: 'AGE_18_PLUS' },
            { id: 'record_count', title: 'RECORD_COUNT' }
        ]
    });

    await csvWriter.writeRecords(masterRecords);
    console.log(`📄 Output: ${path.join(PROCESSED_DIR, 'enrollment_master.csv')}`);
    console.log(`   Records: ${masterRecords.length}`);
}

/**
 * Write feature files
 */
async function writeFeatureFiles(stateFeatures, districtFeatures) {
    // Ensure directory exists
    if (!fs.existsSync(FEATURES_DIR)) {
        fs.mkdirSync(FEATURES_DIR, { recursive: true });
    }

    // State penetration file
    const stateWriter = createObjectCsvWriter({
        path: path.join(FEATURES_DIR, 'penetration_by_state.csv'),
        header: [
            { id: 'state', title: 'STATE' },
            { id: 'total_enrollment', title: 'TOTAL_ENROLLMENT' },
            { id: 'age_0_5', title: 'AGE_0_5' },
            { id: 'age_5_17', title: 'AGE_5_17' },
            { id: 'age_18_plus', title: 'AGE_18_PLUS' },
            { id: 'population', title: 'POPULATION' },
            { id: 'penetration_pct', title: 'PENETRATION_PCT' },
            { id: 'monthly_velocity', title: 'MONTHLY_VELOCITY' },
            { id: 'months_of_data', title: 'MONTHS_OF_DATA' }
        ]
    });

    await stateWriter.writeRecords(stateFeatures);
    console.log(`📄 Output: ${path.join(FEATURES_DIR, 'penetration_by_state.csv')}`);
    console.log(`   States: ${stateFeatures.length}`);

    // District penetration file
    const districtWriter = createObjectCsvWriter({
        path: path.join(FEATURES_DIR, 'penetration_by_district.csv'),
        header: [
            { id: 'state', title: 'STATE' },
            { id: 'district', title: 'DISTRICT' },
            { id: 'total_enrollment', title: 'TOTAL_ENROLLMENT' },
            { id: 'age_0_5', title: 'AGE_0_5' },
            { id: 'age_5_17', title: 'AGE_5_17' },
            { id: 'age_18_plus', title: 'AGE_18_PLUS' },
            { id: 'population', title: 'POPULATION' },
            { id: 'penetration_pct', title: 'PENETRATION_PCT' },
            { id: 'monthly_velocity', title: 'MONTHLY_VELOCITY' },
            { id: 'months_of_data', title: 'MONTHS_OF_DATA' }
        ]
    });

    await districtWriter.writeRecords(districtFeatures);
    console.log(`📄 Output: ${path.join(FEATURES_DIR, 'penetration_by_district.csv')}`);
    console.log(`   Districts: ${districtFeatures.length}`);
}

/**
 * Main pipeline execution
 */
async function runPipeline() {
    console.log('\n' + '='.repeat(60));
    console.log('🚀 UIDAI DATA PIPELINE - Starting');
    console.log('='.repeat(60));
    console.log(`📁 Input Directory: ${RAW_DIR}`);
    console.log(`📁 Output Directory: ${PROCESSED_DIR}`);
    console.log(`📁 Features Directory: ${FEATURES_DIR}`);
    console.log('');

    // TASK 1: Find all CSV files
    console.log('📂 TASK 1: Data Ingestion');
    console.log('-'.repeat(40));

    let csvFiles = [];
    try {
        const files = fs.readdirSync(RAW_DIR);
        csvFiles = files.filter(f => f.endsWith('.csv'));
        stats.csvFound = csvFiles.length;
        console.log(`   CSV files found: ${stats.csvFound}`);
    } catch (error) {
        console.error(`❌ Error reading directory: ${error.message}`);
        return;
    }

    if (csvFiles.length === 0) {
        console.log('   ⚠️ No CSV files found. Exiting.');
        return;
    }

    // Process each CSV file
    for (const file of csvFiles) {
        const filePath = path.join(RAW_DIR, file);
        console.log(`   Processing: ${file}`);

        try {
            const records = await readCSVFile(filePath);
            console.log(`   ✅ Read ${records.length.toLocaleString()} records`);

            // TASK 2 & 3: Clean and aggregate each record
            let validRecords = 0;
            records.forEach(record => {
                const cleaned = cleanRecord(record);
                if (cleaned) {
                    aggregateRecord(cleaned);
                    validRecords++;
                }
            });

            stats.totalRecords += validRecords;
            stats.csvProcessed++;
            console.log(`   ✅ Valid records: ${validRecords.toLocaleString()}`);

        } catch (error) {
            console.log(`   ⚠️ Skipped (malformed): ${error.message}`);
            stats.csvSkipped++;
            stats.malformedFiles.push({ file, error: error.message });
        }
    }

    // Summary after ingestion
    console.log('\n📊 TASK 2: Cleaning & Normalization - Complete');
    console.log('-'.repeat(40));
    console.log(`   Total records processed: ${stats.totalRecords.toLocaleString()}`);

    console.log('\n📈 TASK 3: Aggregation');
    console.log('-'.repeat(40));
    console.log(`   States found: ${stats.statesFound.size}`);
    console.log(`   Districts found: ${stats.districtsFound.size}`);

    // Write enrollment master
    await writeEnrollmentMaster();

    // TASK 4: Feature Engineering
    console.log('\n🔬 TASK 4: Feature Engineering');
    console.log('-'.repeat(40));
    const { stateFeatures, districtFeatures } = computeFeatures();
    await writeFeatureFiles(stateFeatures, districtFeatures);

    // Final summary
    console.log('\n' + '='.repeat(60));
    console.log('✅ PIPELINE COMPLETE');
    console.log('='.repeat(60));
    console.log(`📂 CSVs processed: ${stats.csvProcessed}/${stats.csvFound}`);
    console.log(`⚠️ CSVs skipped: ${stats.csvSkipped}`);
    console.log(`📍 States found: ${stats.statesFound.size}`);
    console.log(`🏘️ Districts found: ${stats.districtsFound.size}`);
    console.log(`📄 Total records: ${stats.totalRecords.toLocaleString()}`);

    if (stats.malformedFiles.length > 0) {
        console.log('\n⚠️ Malformed files:');
        stats.malformedFiles.forEach(f => {
            console.log(`   - ${f.file}: ${f.error}`);
        });
    }

    console.log('\n📄 Output files:');
    console.log(`   • ${path.join(PROCESSED_DIR, 'enrollment_master.csv')}`);
    console.log(`   • ${path.join(FEATURES_DIR, 'penetration_by_state.csv')}`);
    console.log(`   • ${path.join(FEATURES_DIR, 'penetration_by_district.csv')}`);
    console.log('='.repeat(60) + '\n');
}

// Run the pipeline
runPipeline().catch(error => {
    console.error('❌ Pipeline failed:', error);
    process.exit(1);
});

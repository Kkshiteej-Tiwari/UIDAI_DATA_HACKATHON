// ===================================
// UIDAI Analytics Dashboard - Skeleton
// ===================================

// Configuration
const CONFIG = {
    apiKeys: {
        uidai: '579b464db66ec23bdd0000015cfbfd5b9e5a4b366992c1f538e4a2b8',
        grok: [
            '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',
            'gsk_3hihq9LUPAFws7KSvQftWGdyb3FYrHdaFKxeqc9kwI94dgWZTMr',
            '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',
            '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'
        ]
    },
    features: {
        geographicHotspots: true,
        dashboard: false,
        anomalyDetection: false,
        genderTracker: false,
        riskPredictor: false,
        enrollmentForecast: false
    }
};

// ===================================
// Initialize App
// ===================================
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 UIDAI Analytics Dashboard initialized');
    console.log('📊 Active Features:', getActiveFeatures());

    initializeFeatureCards();
    initializeDataSources();
    addInteractiveEffects();
});

// ===================================
// Feature Management
// ===================================
function getActiveFeatures() {
    return Object.entries(CONFIG.features)
        .filter(([key, value]) => value)
        .map(([key]) => key);
}

function initializeFeatureCards() {
    const cards = document.querySelectorAll('.feature-card');

    cards.forEach(card => {
        card.addEventListener('click', handleFeatureClick);
    });

    console.log(`✅ Initialized ${cards.length} feature cards`);
}

function handleFeatureClick(event) {
    const card = event.currentTarget;
    const isDisabled = card.classList.contains('disabled');
    const featureName = card.querySelector('h3').textContent;

    if (isDisabled) {
        showNotification(`${featureName} is currently disabled`, 'info');
        return;
    }

    if (card.id === 'geographic-hotspots') {
        console.log('🗺️ Geographic Hotspots clicked - initializing map view');
        showGeographicHotspotsView();
    }
}

// ===================================
// Geographic Hotspots Map View
// ===================================
let map = null;

function showGeographicHotspotsView() {
    // Get main content container
    const mainContent = document.querySelector('.main-content');

    // Save original content for back button
    if (!window.originalDashboardContent) {
        window.originalDashboardContent = mainContent.innerHTML;
    }

    // Replace content with map view
    mainContent.innerHTML = `
        <div class="map-view-container">
            <div class="map-header">
                <button class="back-button" onclick="returnToDashboard()">
                    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                        <path d="M12 4L6 10L12 16" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    Back to Dashboard
                </button>
                <h2>Geographic Hotspots - Enrollment Coverage Map</h2>
            </div>
            
            <div id="map"></div>
            
            <div class="loading-overlay" id="loading-overlay">
                <div class="loading-content">
                    <div class="loading-spinner"></div>
                    <h3>Fetching UIDAI enrollment data...</h3>
                    <p>Connecting to UIDAI APIs</p>
                </div>
            </div>
        </div>
    `;

    // Initialize map after DOM is ready
    setTimeout(() => {
        initializeMap();
    }, 100);
}

function initializeMap() {
    console.log('📍 Initializing Leaflet map with dark basemap');

    // Initialize map centered on India
    map = L.map('map', {
        center: [22.5937, 78.9629], // Center of India (adjusted)
        zoom: 5,
        zoomControl: true,
        attributionControl: true
    });

    // Add dark basemap (CartoDB Dark Matter)
    const tileLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);

    console.log('✅ Map initialized successfully');

    // Fetch data and then load GeoJSON overlay
    fetchEnrollmentData().then(() => {
        loadDistrictGeoJSON();
    });
}

// ===================================
// District GeoJSON Choropleth
// ===================================
let geojsonLayer = null;
let stateDataMap = new Map(); // Map keyed by normalized state name

// State name normalization mapping (GeoJSON name -> API name)
const STATE_NAME_MAPPING = {
    'ANDAMAN AND NICOBAR': 'ANDAMAN AND NICOBAR ISLANDS',
    'ANDAMAN & NICOBAR': 'ANDAMAN AND NICOBAR ISLANDS',
    'DADRA AND NAGAR HAVELI': 'DADRA AND NAGAR HAVELI AND DAMAN AND DIU',
    'DAMAN AND DIU': 'DADRA AND NAGAR HAVELI AND DAMAN AND DIU',
    'NCT OF DELHI': 'DELHI',
    'NATIONAL CAPITAL TERRITORY OF DELHI': 'DELHI',
    'ORISSA': 'ODISHA',
    'UTTARANCHAL': 'UTTARAKHAND',
    'PONDICHERRY': 'PUDUCHERRY',
    'CHATTISGARH': 'CHHATTISGARH',
    'JAMMU AND KASHMIR': 'JAMMU AND KASHMIR',
    'JAMMU & KASHMIR': 'JAMMU AND KASHMIR'
};

/**
 * Normalize state name for consistent lookup
 */
function normalizeStateNameForLookup(name) {
    if (!name) return '';
    let normalized = name.toUpperCase().trim().replace(/\s+/g, ' ');
    return STATE_NAME_MAPPING[normalized] || normalized;
}

async function loadDistrictGeoJSON() {
    console.log('\n' + '='.repeat(60));
    console.log('🗺️ LOADING MAP DATA (EEI)');
    console.log('='.repeat(60));

    try {
        // Step 1: Fetch EEI data from /api/penetration/eei
        console.log('\n📥 Step 1: Fetching EEI data from /api/penetration/eei...');
        const dataResponse = await fetch('/api/penetration/eei');

        if (!dataResponse.ok) {
            throw new Error(`Failed to fetch EEI data: ${dataResponse.status}`);
        }

        const eeiResult = await dataResponse.json();
        console.log(`✅ EEI data received: ${eeiResult.count} states`);

        // Step 2: Store in Map keyed by normalized state name
        console.log('\n📊 Step 2: Building state data Map...');
        stateDataMap.clear();

        let statesWithEEI = 0;
        let statesMissingData = 0;
        const eeiValues = [];

        eeiResult.data.forEach(item => {
            const normalizedName = normalizeStateNameForLookup(item.state);

            if (item.eei !== null) {
                statesWithEEI++;
                eeiValues.push({ state: item.state, eei: item.eei });
            } else {
                statesMissingData++;
            }

            stateDataMap.set(normalizedName, {
                state: item.state,
                eei: item.eei,
                actual_enrollment: item.actual_enrollment,
                expected_enrollment: item.expected_enrollment
            });
        });

        console.log(`   Map created with ${stateDataMap.size} entries`);
        window.stateDataMap = stateDataMap; // Store globally for debugging

        // Validation Logging
        console.log('\n🔍 EEI Validation Stats:');
        console.log(`   States with EEI computed: ${statesWithEEI}`);
        console.log(`   States missing data: ${statesMissingData}`);

        if (eeiValues.length > 0) {
            eeiValues.sort((a, b) => b.eei - a.eei);

            console.log('\n🏆 Top 5 States by EEI:');
            eeiValues.slice(0, 5).forEach((item, i) => {
                console.log(`   ${i + 1}. ${item.state}: ${item.eei.toFixed(2)}`);
            });

            console.log('\n⚠️ Bottom 5 States by EEI:');
            eeiValues.slice(-5).reverse().forEach((item, i) => {
                console.log(`   ${i + 1}. ${item.state}: ${item.eei.toFixed(2)}`);
            });
        }

        // Step 3: Fetch GeoJSON
        console.log('\n📥 Step 3: Fetching GeoJSON boundaries...');
        const geojsonUrl = 'https://raw.githubusercontent.com/geohacker/india/master/state/india_state.geojson';

        const response = await fetch(geojsonUrl);
        if (!response.ok) {
            throw new Error(`Failed to fetch GeoJSON: ${response.status}`);
        }

        const geojson = await response.json();
        const totalGeoJSONStates = geojson.features.length;
        console.log(`✅ GeoJSON loaded: ${totalGeoJSONStates} features`);

        // Step 4: Create choropleth layer
        console.log('\n🎨 Step 4: Creating choropleth layer...');
        geojsonLayer = L.geoJSON(geojson, {
            style: (feature) => getFeatureStyleFromMap(feature),
            onEachFeature: (feature, layer) => bindFeatureEventsFromMap(feature, layer)
        }).addTo(map);

        // Add legend
        addLegend();

        // Hide loading overlay
        hideLoadingOverlay();

        console.log('\n' + '='.repeat(60));
        console.log('✅ MAP RENDERING COMPLETE (EEI Applied)');
        console.log('='.repeat(60) + '\n');

    } catch (error) {
        console.error('❌ Map Data Load Error:', error);
        hideLoadingOverlay();
        showNotification('Failed to load map data', 'error');
    }
}

/**
 * Get feature style using EEI
 */
function getFeatureStyleFromMap(feature) {
    const geoName = feature.properties.NAME_1 || feature.properties.name || feature.properties.ST_NM || '';
    const normalizedName = normalizeStateNameForLookup(geoName);
    const data = stateDataMap.get(normalizedName);

    // Check if data exists and has valid EEI
    const hasData = data && data.eei !== null && !isNaN(data.eei);

    if (hasData) {
        const color = getEEIColor(data.eei);
        return {
            fillColor: color,
            weight: 1.5,
            opacity: 1,
            color: '#6b7280',
            fillOpacity: 0.7
        };
    } else {
        // No data - grey with dashed border
        return {
            fillColor: '#4B5563',
            weight: 1,
            opacity: 1,
            color: '#374151',
            dashArray: '5, 5',
            fillOpacity: 0.4
        };
    }
}

/**
 * Get color based on Enrollment Efficiency Index
 * - EEI > 1.2 → Green (Over-performing)
 * - 0.8 <= EEI <= 1.2 → Yellow (On track)
 * - EEI < 0.8 → Red (Under-performing)
 */
function getEEIColor(eei) {
    if (eei === null || eei === undefined || isNaN(eei)) return '#4B5563';

    if (eei > 1.2) return '#22c55e'; // Green
    if (eei >= 0.8) return '#eab308'; // Yellow
    return '#ef4444'; // Red
}

/**
 * Bind tooltip and events using Map lookup
 */
/**
 * Bind tooltip showing EEI details
 */
function bindFeatureEventsFromMap(feature, layer) {
    const geoName = feature.properties.NAME_1 || feature.properties.name || feature.properties.ST_NM || '';
    const normalizedName = normalizeStateNameForLookup(geoName);
    const data = stateDataMap.get(normalizedName);

    const hasData = data && data.eei !== null && !isNaN(data.eei);

    // Determine interpretation
    let interpretation = '';
    let interpColor = '';

    if (hasData) {
        if (data.eei > 1.2) {
            interpretation = 'Over-performing';
            interpColor = '#22c55e';
        } else if (data.eei >= 0.8) {
            interpretation = 'On track';
            interpColor = '#eab308';
        } else {
            interpretation = 'Under-performing';
            interpColor = '#ef4444';
        }
    }

    let tooltipContent;

    if (hasData) {
        tooltipContent = `
            <div class="map-tooltip">
                <strong>${geoName}</strong><br/>
                <span>EEI: <b style="color: ${interpColor}">${data.eei.toFixed(2)}</b></span><br/>
                <span style="font-size: 0.85rem; color: ${interpColor}; margin-bottom: 6px; display: block;">${interpretation}</span>
                <div style="border-top: 1px solid #444; margin: 4px 0;"></div>
                <span>Actual: ${data.actual_enrollment?.toLocaleString() || 0}</span><br/>
                <span>Expected: ${data.expected_enrollment?.toLocaleString() || 0}</span><br/>
                <span style="font-size: 0.75rem; color: #888; margin-top: 4px; display: block; line-height: 1.2;">
                    EEI compares enrollment activity vs expected based on population size.
                </span>
            </div>
        `;
    } else {
        tooltipContent = `
            <div class="map-tooltip unavailable">
                <strong>${geoName}</strong><br/>
                <span class="unavailable-msg">⚠️ Data unavailable</span><br/>
                <span style="font-size: 0.75rem; color: #888;">No population or enrollment data found.</span>
            </div>
        `;
    }

    layer.bindTooltip(tooltipContent, {
        permanent: false,
        direction: 'auto',
        className: hasData ? 'custom-tooltip' : 'custom-tooltip unavailable-tooltip'
    });

    // Highlight on hover
    layer.on({
        mouseover: (e) => {
            const layer = e.target;
            layer.setStyle({
                weight: 3,
                color: '#a855f7',
                fillOpacity: 0.9
            });
            layer.bringToFront();
        },
        mouseout: (e) => {
            geojsonLayer.resetStyle(e.target);
        },
        click: (e) => {
            map.fitBounds(e.target.getBounds());
        }
    });
}

/**
 * Get color based on penetration percentage
 * Rules:
 * - null/undefined/NaN → GREY
 * - < 70 → RED
 * - 70-90 → YELLOW  
 * - >= 90 → GREEN
 */
function getPenetrationColorScale(penetration) {
    // Null, undefined, or NaN → Grey
    if (penetration === null || penetration === undefined || isNaN(penetration)) {
        return '#4B5563'; // Grey - no data
    }

    // Ensure it's a number
    const value = Number(penetration);
    if (isNaN(value)) {
        return '#4B5563'; // Grey - invalid
    }

    // Apply color scale based on actual percentages
    if (value < 70) {
        return '#ef4444'; // Red (low penetration < 70%)
    } else if (value < 90) {
        return '#eab308'; // Yellow (medium 70-90%)
    } else {
        return '#22c55e'; // Green (high >= 90%)
    }
}

// Aggregate penetration data by state
function aggregatePenetrationByState(data) {
    const stateData = {};

    data.forEach(item => {
        if (!item.state || !item.isValid) return;

        const stateName = normalizeStateName(item.state);

        if (!stateData[stateName]) {
            stateData[stateName] = {
                totalEnrollment: 0,
                totalPopulation: 0,
                districts: []
            };
        }

        stateData[stateName].totalEnrollment += item.enrollment || 0;
        stateData[stateName].totalPopulation += item.population || 0;
        stateData[stateName].districts.push(item.district);
    });

    // Calculate state-level penetration
    Object.keys(stateData).forEach(state => {
        const s = stateData[state];
        s.penetration = s.totalPopulation > 0
            ? (s.totalEnrollment / s.totalPopulation) * 100
            : 0;
    });

    return stateData;
}

// Normalize state name for matching
function normalizeStateName(name) {
    if (!name) return '';
    const mappings = {
        'andhra pradesh': 'Andhra Pradesh',
        'arunachal pradesh': 'Arunachal Pradesh',
        'assam': 'Assam',
        'bihar': 'Bihar',
        'chhattisgarh': 'Chhattisgarh',
        'delhi': 'NCT of Delhi',
        'nct of delhi': 'NCT of Delhi',
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
        'west bengal': 'West Bengal',
        'jammu and kashmir': 'Jammu & Kashmir',
        'jammu & kashmir': 'Jammu & Kashmir'
    };
    const lower = name.toLowerCase().trim();
    return mappings[lower] || name;
}

// Check if penetration value is valid (not null, undefined, NaN)
function isValidPenetration(penetration) {
    return penetration !== null &&
        penetration !== undefined &&
        !isNaN(penetration) &&
        typeof penetration === 'number';
}

// Get color based on penetration rate (smooth gradient)
function getPenetrationColor(penetration, hasData = true) {
    // Return grey for missing/invalid data
    if (!hasData || !isValidPenetration(penetration)) {
        return '#4B5563'; // Grey for unavailable data
    }

    // For demo purposes, scale the very low percentages to visible colors
    // Real penetration values are < 1%, so we'll use a different scale
    const scaledPenetration = Math.min(penetration * 100, 100); // Scale up for visibility

    if (scaledPenetration < 70) {
        // Red gradient (0-70)
        const intensity = scaledPenetration / 70;
        return `rgb(${239 - Math.floor(intensity * 50)}, ${68 + Math.floor(intensity * 100)}, ${68 + Math.floor(intensity * 50)})`;
    } else if (scaledPenetration < 90) {
        // Yellow gradient (70-90)
        const intensity = (scaledPenetration - 70) / 20;
        return `rgb(${234 - Math.floor(intensity * 100)}, ${179 + Math.floor(intensity * 18)}, ${8 + Math.floor(intensity * 80)})`;
    } else {
        // Green gradient (90-100)
        const intensity = (scaledPenetration - 90) / 10;
        return `rgb(${34 - Math.floor(intensity * 10)}, ${197 + Math.floor(intensity * 40)}, ${94 - Math.floor(intensity * 10)})`;
    }
}

// Style function for GeoJSON features
function getFeatureStyle(feature, stateData) {
    const stateName = feature.properties.NAME_1 || feature.properties.name || feature.properties.ST_NM;
    const normalizedName = normalizeStateName(stateName);
    const data = stateData[normalizedName];

    // Check if we have valid data for this state
    const hasData = data && isValidPenetration(data.penetration);
    const penetration = hasData ? data.penetration : null;
    const fillColor = getPenetrationColor(penetration, hasData);

    return {
        fillColor: fillColor,
        weight: hasData ? 1.5 : 1,
        opacity: 1,
        color: hasData ? '#6b7280' : '#4b5563',
        dashArray: hasData ? null : '5, 5', // Dashed border for unavailable data
        fillOpacity: hasData ? 0.7 : 0.4
    };
}

// Bind hover/click events to features
function bindFeatureEvents(feature, layer, stateData) {
    const stateName = feature.properties.NAME_1 || feature.properties.name || feature.properties.ST_NM;
    const normalizedName = normalizeStateName(stateName);
    const data = stateData[normalizedName];

    // Check if we have valid data
    const hasData = data && isValidPenetration(data.penetration);

    // Tooltip content - different for available vs unavailable data
    let tooltipContent;

    if (hasData) {
        tooltipContent = `
            <div class="map-tooltip">
                <strong>${stateName}</strong><br/>
                <span>Penetration: <b>${data.penetration.toFixed(4)}%</b></span><br/>
                <span>Enrollment: ${data.totalEnrollment?.toLocaleString() || 0}</span><br/>
                <span>Population: ${data.totalPopulation?.toLocaleString() || 0}</span><br/>
                <span>Districts: ${data.districts?.length || 0}</span>
            </div>
        `;
    } else {
        tooltipContent = `
            <div class="map-tooltip unavailable">
                <strong>${stateName}</strong><br/>
                <span class="unavailable-msg">⚠️ Data unavailable – join pending</span>
            </div>
        `;
    }

    layer.bindTooltip(tooltipContent, {
        permanent: false,
        direction: 'auto',
        className: hasData ? 'custom-tooltip' : 'custom-tooltip unavailable-tooltip'
    });

    // Highlight on hover
    layer.on({
        mouseover: (e) => {
            const layer = e.target;
            layer.setStyle({
                weight: 3,
                color: '#a855f7',
                fillOpacity: 0.9
            });
            layer.bringToFront();
        },
        mouseout: (e) => {
            geojsonLayer.resetStyle(e.target);
        },
        click: (e) => {
            map.fitBounds(e.target.getBounds());
        }
    });
}

// Add legend to map
function addLegend() {
    const legend = L.control({ position: 'bottomright' });

    legend.onAdd = function (map) {
        const div = L.DomUtil.create('div', 'map-legend');
        div.innerHTML = `
            <h4>Enrollment Efficiency Index</h4>
            <div class="legend-subtitle" style="font-size: 0.7rem; color: #aaa; margin-bottom: 8px; line-height: 1.2;">
                Compares actual enrollment to expected <br>enrollment based on population share.
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background: #22c55e;"></span>
                <span>&gt; 1.2 (Over-performing)</span>
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background: #eab308;"></span>
                <span>0.8 - 1.2 (On track)</span>
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background: #ef4444;"></span>
                <span>&lt; 0.8 (Under-performing)</span>
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background: #374151;"></span>
                <span>No Data</span>
            </div>
        `;
        return div;
    };

    legend.addTo(map);
    console.log('📍 Legend added to map');
}

// ===================================
// UIDAI Enrollment Data Fetch
// ===================================
async function fetchEnrollmentData() {
    console.log('\n' + '='.repeat(60));
    console.log('📊 FETCHING UIDAI ENROLLMENT DATA');
    console.log('='.repeat(60));

    try {
        // Call backend API
        const response = await fetch('/api/enrollment/uidai-data?limit=50');

        // 1) Log HTTP status
        console.log(`\n1️⃣ HTTP Status: ${response.status}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        // 2) Log raw response keys
        console.log(`\n2️⃣ Response Keys (Object.keys): ${Object.keys(data).join(', ')}`);

        // 3) Log first 3 records (sample)
        console.log('\n3️⃣ First 3 Records (Sample):');
        if (data.sampleRecords && data.sampleRecords.length > 0) {
            data.sampleRecords.forEach((record, i) => {
                console.log(`   Record ${i + 1}:`, record);
            });
        } else {
            console.log('   No records returned');
        }

        // 4) Extract and log parsed fields
        console.log('\n4️⃣ Parsed Fields (state_name, district_name, total_enrollments, month):');
        if (data.parsedRecords && data.parsedRecords.length > 0) {
            data.parsedRecords.slice(0, 3).forEach((record, i) => {
                console.log(`   Parsed ${i + 1}:`, {
                    state_name: record.state_name,
                    district_name: record.district_name,
                    total_enrollments: record.total_enrollments,
                    month: record.month
                });
            });
        }

        // Check for district-level data
        if (data.hasDistrictData === false) {
            console.log('\n⚠️ District-level enrollment not available in this endpoint');
        }

        // Log available fields from the dataset
        console.log('\n5️⃣ Available Fields in Dataset:', data.availableFields);

        console.log('\n' + '='.repeat(60));
        console.log('✅ UIDAI Data Fetch Complete');
        console.log(`   Total Records: ${data.totalCount || 'N/A'}`);
        console.log(`   Has District Data: ${data.hasDistrictData}`);
        console.log('='.repeat(60) + '\n');

        // Store data for later visualization
        window.enrollmentData = data;

        // Compute penetration rates after enrollment data is fetched
        await computePenetrationRates();

    } catch (error) {
        console.error('\n❌ UIDAI API Error:');
        console.error('   Message:', error.message);
        console.error('   Full Error:', error);

        // Show toast notification
        showNotification('UIDAI API unreachable – check credentials or CORS', 'error');
    }
}

// ===================================
// Penetration Rate Calculation
// ===================================
async function computePenetrationRates() {
    console.log('\n' + '='.repeat(60));
    console.log('📈 COMPUTING AADHAAR PENETRATION RATES');
    console.log('='.repeat(60));

    try {
        // Call backend penetration endpoint
        const response = await fetch('/api/geospatial/penetration?limit=500');

        // 1) Log HTTP status
        console.log(`\n1️⃣ HTTP Status: ${response.status}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        // 2) Log response keys
        console.log(`\n2️⃣ Response Keys: ${Object.keys(data).join(', ')}`);

        // 3) Log summary statistics
        console.log('\n3️⃣ Penetration Summary:');
        console.log(`   Total districts processed: ${data.summary.totalDistricts}`);
        console.log(`   Valid calculations: ${data.summary.validCalculations}`);
        console.log(`   Invalid rows: ${data.summary.invalidRows}`);
        console.log(`   Unmatched districts: ${data.summary.unmatchedDistricts}`);
        console.log(`   Average penetration: ${data.summary.averagePenetration}%`);

        // 4) Log 3 low-penetration examples
        console.log('\n4️⃣ 3 Low-Penetration Districts:');
        if (data.lowPenetrationExamples && data.lowPenetrationExamples.length > 0) {
            data.lowPenetrationExamples.forEach((item, i) => {
                console.log(`   ${i + 1}. ${item.district}, ${item.state}`);
                console.log(`      Enrollment: ${item.enrollment.toLocaleString()}`);
                console.log(`      Population: ${item.population.toLocaleString()}`);
                console.log(`      Penetration: ${item.penetration.toFixed(2)}%`);
            });
        } else {
            console.log('   No valid penetration data available');
        }

        // 5) Log invalid rows if any
        if (data.invalidRows && data.invalidRows.length > 0) {
            console.log('\n5️⃣ Invalid Rows (out of range or errors):');
            data.invalidRows.forEach((row, i) => {
                console.log(`   ⚠️ ${row.district}, ${row.state}: ${row.reason}`);
            });
        }

        // 6) Log sample output structure
        console.log('\n6️⃣ Sample Output Structure (first 3):');
        const sampleResults = data.results.filter(r => r.isValid).slice(0, 3);
        sampleResults.forEach((item, i) => {
            console.log(`   ${i + 1}.`, {
                state: item.state,
                district: item.district,
                enrollment: item.enrollment,
                population: item.population,
                penetration: item.penetration
            });
        });

        console.log('\n' + '='.repeat(60));
        console.log('✅ PENETRATION CALCULATION COMPLETE');
        console.log('='.repeat(60) + '\n');

        // Store for visualization
        window.penetrationData = data;

    } catch (error) {
        console.error('\n❌ Penetration Calculation Error:');
        console.error('   Message:', error.message);
        console.error('   Full Error:', error);

        showNotification('Failed to compute penetration rates', 'error');
    }
}

// Hide loading overlay function
function hideLoadingOverlay() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.opacity = '0';
        overlay.style.transition = 'opacity 0.3s ease-out';
        setTimeout(() => {
            overlay.style.display = 'none';
        }, 300);
    }
}

function returnToDashboard() {
    const mainContent = document.querySelector('.main-content');

    // Destroy map instance
    if (map) {
        map.remove();
        map = null;
    }

    // Restore original dashboard content
    if (window.originalDashboardContent) {
        mainContent.innerHTML = window.originalDashboardContent;
    }

    // Re-initialize feature cards
    initializeFeatureCards();
    initializeDataSources();
    addInteractiveEffects();

    console.log('🏠 Returned to dashboard');
}

// Export for inline onclick
window.returnToDashboard = returnToDashboard;

// ===================================
// Data Sources Management
// ===================================
function initializeDataSources() {
    const dataSources = document.querySelectorAll('.data-source-card');

    dataSources.forEach(source => {
        source.addEventListener('click', handleDataSourceClick);
    });

    console.log(`✅ Initialized ${dataSources.length} data sources`);
}

function handleDataSourceClick(event) {
    const card = event.currentTarget;
    const sourceName = card.querySelector('h3').textContent;

    showNotification(`📡 ${sourceName} - API connection ready`, 'info');
    console.log(`Data source clicked: ${sourceName}`);
}

// ===================================
// Interactive Effects
// ===================================
function addInteractiveEffects() {
    // Add particle effect on hover for active cards
    const activeCards = document.querySelectorAll('.feature-card.active');

    activeCards.forEach(card => {
        card.addEventListener('mouseenter', () => {
            createParticleEffect(card);
        });
    });

    // Add ripple effect on click
    document.querySelectorAll('.feature-card, .data-source-card').forEach(card => {
        card.addEventListener('click', (e) => {
            createRippleEffect(e, card);
        });
    });
}

function createParticleEffect(element) {
    // Placeholder for particle effect - to be implemented
    console.log('✨ Particle effect triggered');
}

function createRippleEffect(event, element) {
    const ripple = document.createElement('span');
    const rect = element.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = event.clientX - rect.left - size / 2;
    const y = event.clientY - rect.top - size / 2;

    ripple.style.width = ripple.style.height = `${size}px`;
    ripple.style.left = `${x}px`;
    ripple.style.top = `${y}px`;
    ripple.classList.add('ripple');

    element.appendChild(ripple);

    setTimeout(() => {
        ripple.remove();
    }, 600);
}

// ===================================
// Notification System
// ===================================
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;

    // Style the notification
    Object.assign(notification.style, {
        position: 'fixed',
        top: '20px',
        right: '20px',
        padding: '1rem 1.5rem',
        borderRadius: '12px',
        background: type === 'success'
            ? 'linear-gradient(135deg, #10B981 0%, #34D399 100%)'
            : type === 'info'
                ? 'linear-gradient(135deg, #3B82F6 0%, #2DD4BF 100%)'
                : 'linear-gradient(135deg, #F59E0B 0%, #FBBF24 100%)',
        color: 'white',
        fontWeight: '600',
        fontSize: '0.875rem',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.2)',
        zIndex: '1000',
        animation: 'slideIn 0.3s ease-out',
        backdropFilter: 'blur(10px)'
    });

    document.body.appendChild(notification);

    // Auto remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// ===================================
// Utility Functions
// ===================================
function logSystemInfo() {
    console.log('='.repeat(50));
    console.log('UIDAI Analytics Dashboard - System Info');
    console.log('='.repeat(50));
    console.log('API Keys Configured:', {
        UIDAI: CONFIG.apiKeys.uidai ? '✅ Set' : '❌ Not Set',
        Grok: `✅ ${CONFIG.apiKeys.grok.length} keys configured`
    });
    console.log('Features Status:', CONFIG.features);
    console.log('='.repeat(50));
}

// Call on load
logSystemInfo();

// ===================================
// CSS Animations (injected via JS)
// ===================================
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
    
    .ripple {
        position: absolute;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.3);
        transform: scale(0);
        animation: ripple-animation 0.6s ease-out;
        pointer-events: none;
    }
    
    @keyframes ripple-animation {
        to {
            transform: scale(2);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// ===================================
// Export for debugging
// ===================================
window.UIDAI = {
    config: CONFIG,
    showNotification,
    getActiveFeatures
};

console.log('💡 Tip: Access window.UIDAI for debugging');

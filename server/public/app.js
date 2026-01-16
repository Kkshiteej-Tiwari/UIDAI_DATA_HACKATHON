/**
 * UIDAI Analytics Dashboard - Frontend JavaScript
 */

const API_BASE = 'http://localhost:3001/api';
const ML_API_BASE = 'http://localhost:8000';

// =====================================
// Status Check
// =====================================

async function checkStatus() {
    // Check backend status
    try {
        const response = await fetch(`${API_BASE}/health`);
        if (response.ok) {
            document.getElementById('backend-status').textContent = 'Online';
            document.querySelector('.status-item:first-child .status-dot').classList.add('online');
            document.querySelector('.status-item:first-child .status-dot').classList.remove('offline');
        }
    } catch (e) {
        document.getElementById('backend-status').textContent = 'Offline';
    }

    // Check ML backend status
    try {
        const response = await fetch(`${ML_API_BASE}/health`);
        if (response.ok) {
            document.getElementById('ml-status').textContent = 'Online';
            document.querySelector('.status-item:last-child .status-dot').classList.add('online');
            document.querySelector('.status-item:last-child .status-dot').classList.remove('offline');
        }
    } catch (e) {
        document.getElementById('ml-status').textContent = 'Offline';
    }
}

// =====================================
// Feature Loaders
// =====================================

async function loadFeature(feature) {
    showLoading();

    try {
        switch (feature) {
            case 'dashboard':
                await loadDashboard();
                break;
            case 'hotspots':
                await loadHotspots();
                break;
            case 'anomalies':
                await loadAnomalies();
                break;
            case 'gender':
                await loadGenderTracker();
                break;
            case 'risk':
                await loadRiskPredictor();
                break;
            case 'forecast':
                await loadForecast();
                break;
            default:
                showError('Unknown feature');
        }
    } catch (error) {
        showError(error.message);
    }
}

async function loadData(dataType) {
    showLoading();

    try {
        const response = await fetch(`${API_BASE}/${dataType}?limit=50`);
        const data = await response.json();

        if (data.success) {
            showDataTable(dataType, data.records);
        } else {
            showError(data.error || 'Failed to load data');
        }
    } catch (error) {
        showError(`Failed to fetch ${dataType} data: ${error.message}`);
    }
}

// =====================================
// Feature Implementations
// =====================================

async function loadDashboard() {
    setTitle('📈 Dashboard Overview');

    // Fetch all data sources
    const [enrolment, demographic, biometric] = await Promise.all([
        fetch(`${API_BASE}/enrolment?limit=100`).then(r => r.json()).catch(() => ({ records: [] })),
        fetch(`${API_BASE}/demographic?limit=100`).then(r => r.json()).catch(() => ({ records: [] })),
        fetch(`${API_BASE}/biometric?limit=100`).then(r => r.json()).catch(() => ({ records: [] }))
    ]);

    // Calculate stats
    const totalEnrollments = enrolment.records?.reduce((sum, r) =>
        sum + (parseInt(r.age_0_5) || 0) + (parseInt(r.age_5_17) || 0) + (parseInt(r.age_18_greater) || 0), 0) || 0;

    const uniqueStates = new Set(enrolment.records?.map(r => r.state) || []).size;
    const uniqueDistricts = new Set(enrolment.records?.map(r => r.district) || []).size;

    showContent(`
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">${formatNumber(totalEnrollments)}</div>
                <div class="stat-label">Total Enrollments</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${uniqueStates}</div>
                <div class="stat-label">States</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${uniqueDistricts}</div>
                <div class="stat-label">Districts</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${enrolment.total || enrolment.records?.length || 0}</div>
                <div class="stat-label">Records Available</div>
            </div>
        </div>
        
        <h3 style="margin: 20px 0 15px; color: #00d4ff;">📊 Data Sources Status</h3>
        <div class="alert alert-info">
            <strong>Enrolment API:</strong> ${enrolment.records?.length || 0} records loaded
            ${enrolment.isMockData ? ' (Mock Data)' : ''}
        </div>
        <div class="alert alert-info">
            <strong>Demographic API:</strong> ${demographic.records?.length || 0} records loaded
        </div>
        <div class="alert alert-info">
            <strong>Biometric API:</strong> ${biometric.records?.length || 0} records loaded
        </div>
    `);
}

async function loadHotspots() {
    setTitle('🗺️ Geographic Hotspots - Gi* Analysis');

    try {
        const response = await fetch(`${API_BASE}/hotspots/gi-star?limit=200`);
        const data = await response.json();

        if (data.success && data.data) {
            const { summary, coldspots, hotspots } = data.data;

            showContent(`
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">${summary?.totalRegions || 0}</div>
                        <div class="stat-label">Regions Analyzed</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" style="color: #ff4444;">${summary?.coldspotCount || 0}</div>
                        <div class="stat-label">Coldspots (Low Coverage)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" style="color: #00ff88;">${summary?.hotspotCount || 0}</div>
                        <div class="stat-label">Hotspots (High Coverage)</div>
                    </div>
                </div>
                
                <h3 style="margin: 20px 0 15px; color: #ff6666;">🔴 Priority Coldspots (Need Intervention)</h3>
                ${renderHotspotList(coldspots || [], 'coldspot')}
                
                <h3 style="margin: 20px 0 15px; color: #00ff88;">🟢 Top Performing Hotspots</h3>
                ${renderHotspotList(hotspots || [], 'hotspot')}
            `);
        } else {
            // Fallback to basic data
            const enrolment = await fetch(`${API_BASE}/enrolment?limit=100`).then(r => r.json());
            showContent(`
                <div class="alert alert-warning">
                    <strong>Note:</strong> Hotspot API not available. Showing basic enrollment data.
                </div>
                ${renderBasicStats(enrolment.records || [])}
            `);
        }
    } catch (error) {
        showError(`Failed to load hotspots: ${error.message}`);
    }
}

async function loadAnomalies() {
    setTitle('⚠️ Anomaly Detection');

    try {
        const response = await fetch(`${API_BASE}/hotspots/anomalies?limit=200`);
        const data = await response.json();

        if (data.success && data.data) {
            const { summary, alerts } = data.data;

            showContent(`
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value" style="color: #ffaa00;">${summary?.totalAnomalies || 0}</div>
                        <div class="stat-label">Total Anomalies</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" style="color: #ff4444;">${summary?.critical || 0}</div>
                        <div class="stat-label">Critical</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" style="color: #ffaa00;">${summary?.high || 0}</div>
                        <div class="stat-label">High Priority</div>
                    </div>
                </div>
                
                <h3 style="margin: 20px 0 15px;">🚨 Active Alerts</h3>
                ${renderAlerts(alerts || [])}
            `);
        } else {
            showContent(`
                <div class="alert alert-info">
                    <strong>Anomaly Detection:</strong> No anomalies detected or API unavailable.
                </div>
                <p style="margin-top: 15px; color: #aaa;">
                    The anomaly detection system uses Isolation Forest and ensemble ML models 
                    to identify unusual patterns in enrollment data.
                </p>
            `);
        }
    } catch (error) {
        showError(`Failed to load anomalies: ${error.message}`);
    }
}

async function loadGenderTracker() {
    setTitle('👥 Gender Inclusion Tracker');

    try {
        const enrolment = await fetch(`${API_BASE}/enrolment?limit=200`).then(r => r.json());
        const records = enrolment.records || [];

        // Calculate gender stats by state (simulated since real data may not have gender)
        const stateStats = {};
        records.forEach(r => {
            if (!stateStats[r.state]) {
                stateStats[r.state] = { total: 0, records: 0 };
            }
            stateStats[r.state].total += (parseInt(r.age_18_greater) || 0);
            stateStats[r.state].records++;
        });

        const stateList = Object.entries(stateStats)
            .map(([state, data]) => ({ state, ...data }))
            .sort((a, b) => b.total - a.total)
            .slice(0, 15);

        showContent(`
            <div class="alert alert-info">
                <strong>Gender Inclusion Analysis:</strong> 
                Monitoring female Aadhaar enrollment coverage across districts.
            </div>
            
            <h3 style="margin: 20px 0 15px;">📊 State-wise Enrollment Summary</h3>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>State</th>
                        <th>Adult Enrollments (18+)</th>
                        <th>Records</th>
                    </tr>
                </thead>
                <tbody>
                    ${stateList.map(s => `
                        <tr>
                            <td>${s.state}</td>
                            <td>${formatNumber(s.total)}</td>
                            <td>${s.records}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
            
            <div class="alert alert-warning" style="margin-top: 20px;">
                <strong>Note:</strong> Full gender disaggregated data requires ML backend connection.
            </div>
        `);
    } catch (error) {
        showError(`Failed to load gender data: ${error.message}`);
    }
}

async function loadRiskPredictor() {
    setTitle('🔮 Biometric Re-enrollment Risk Predictor');

    try {
        // Check if ML backend is available
        const mlHealth = await fetch(`${ML_API_BASE}/health`).then(r => r.json()).catch(() => null);

        if (mlHealth) {
            showContent(`
                <div class="alert alert-info">
                    <strong>ML Backend Connected!</strong> Risk prediction models are available.
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">3</div>
                        <div class="stat-label">Dataset APIs</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">4</div>
                        <div class="stat-label">ML Models</div>
                    </div>
                </div>
                
                <h3 style="margin: 20px 0 15px;">🧠 Available Models</h3>
                <div class="alert alert-info">
                    <strong>Random Forest:</strong> Risk classification based on regional features
                </div>
                <div class="alert alert-info">
                    <strong>XGBoost:</strong> Gradient boosting for high-accuracy predictions
                </div>
                <div class="alert alert-info">
                    <strong>Isolation Forest:</strong> Anomaly-based risk detection
                </div>
                <div class="alert alert-info">
                    <strong>LightGBM:</strong> Gender inclusion gap prediction
                </div>
            `);
        } else {
            showContent(`
                <div class="alert alert-warning">
                    <strong>ML Backend Offline:</strong> Start the ML backend to use risk prediction.
                </div>
                <p style="margin-top: 15px; color: #aaa;">
                    Run: <code style="background: #333; padding: 5px 10px; border-radius: 5px;">
                    cd ml_backend && python -m uvicorn main:app --reload
                    </code>
                </p>
            `);
        }
    } catch (error) {
        showError(`Failed to check ML backend: ${error.message}`);
    }
}

async function loadForecast() {
    setTitle('📅 Enrollment Forecast');

    try {
        const response = await fetch(`${API_BASE}/hotspots/trends?limit=500`);
        const data = await response.json();

        if (data.success && data.data) {
            const { regionalTrends } = data.data;

            showContent(`
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value" style="color: #00ff88;">${regionalTrends?.summary?.increasing || 0}</div>
                        <div class="stat-label">Increasing Trend</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${regionalTrends?.summary?.stable || 0}</div>
                        <div class="stat-label">Stable</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" style="color: #ff4444;">${regionalTrends?.summary?.decreasing || 0}</div>
                        <div class="stat-label">Decreasing Trend</div>
                    </div>
                </div>
                
                <h3 style="margin: 20px 0 15px;">📈 Regional Trends</h3>
                ${renderTrends(regionalTrends?.regions || [])}
            `);
        } else {
            showContent(`
                <div class="alert alert-info">
                    <strong>Enrollment Forecast:</strong> Time-series analysis for enrollment predictions.
                </div>
                <p style="margin-top: 15px; color: #aaa;">
                    This feature uses seasonal decomposition to predict future enrollment patterns.
                </p>
            `);
        }
    } catch (error) {
        showError(`Failed to load forecast: ${error.message}`);
    }
}

// =====================================
// UI Helpers
// =====================================

function showLoading() {
    document.getElementById('results-section').classList.add('active');
    document.getElementById('results-content').innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
        </div>
    `;
}

function showContent(html) {
    document.getElementById('results-section').classList.add('active');
    document.getElementById('results-content').innerHTML = html;
}

function setTitle(title) {
    document.getElementById('results-title').textContent = title;
}

function showError(message) {
    showContent(`
        <div class="alert alert-critical">
            <strong>Error:</strong> ${message}
        </div>
    `);
}

function clearResults() {
    document.getElementById('results-section').classList.remove('active');
}

function formatNumber(num) {
    if (num >= 10000000) return (num / 10000000).toFixed(1) + ' Cr';
    if (num >= 100000) return (num / 100000).toFixed(1) + ' L';
    if (num >= 1000) return (num / 1000).toFixed(1) + ' K';
    return num.toString();
}

function showDataTable(dataType, records) {
    if (!records || records.length === 0) {
        showContent('<p class="placeholder">No data available</p>');
        return;
    }

    setTitle(`📋 ${dataType.charAt(0).toUpperCase() + dataType.slice(1)} Data`);

    const headers = Object.keys(records[0]);

    showContent(`
        <p style="margin-bottom: 15px; color: #aaa;">Showing ${records.length} records</p>
        <table class="data-table">
            <thead>
                <tr>
                    ${headers.slice(0, 7).map(h => `<th>${h}</th>`).join('')}
                </tr>
            </thead>
            <tbody>
                ${records.slice(0, 20).map(r => `
                    <tr>
                        ${headers.slice(0, 7).map(h => `<td>${r[h] || '-'}</td>`).join('')}
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `);
}

function renderHotspotList(items, type) {
    if (!items.length) return '<p style="color: #666;">No data available</p>';

    return items.slice(0, 5).map(item => `
        <div class="alert ${type === 'coldspot' ? 'alert-critical' : 'alert-info'}">
            <strong>${item.region || item.state}</strong>
            ${item.zScore ? `<span style="float: right;">z-score: ${item.zScore.toFixed(2)}</span>` : ''}
            <br><span style="color: #aaa; font-size: 0.85rem;">
                ${item.classification || (type === 'coldspot' ? 'Low coverage area' : 'High coverage area')}
            </span>
        </div>
    `).join('');
}

function renderAlerts(alerts) {
    if (!alerts.length) return '<p style="color: #666;">No alerts at this time</p>';

    return alerts.slice(0, 10).map(alert => `
        <div class="alert ${alert.severity === 'critical' ? 'alert-critical' : alert.severity === 'high' ? 'alert-warning' : 'alert-info'}">
            <strong>${alert.region}</strong> - ${alert.severity?.toUpperCase() || 'ALERT'}
            <br><span style="color: #aaa; font-size: 0.85rem;">
                Deviation: ${(alert.percentageDeviation || 0).toFixed(1)}% | ${alert.direction || 'unusual pattern'}
            </span>
        </div>
    `).join('');
}

function renderTrends(regions) {
    if (!regions.length) return '<p style="color: #666;">No trend data available</p>';

    return `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Region</th>
                    <th>Trend</th>
                    <th>Monthly Change</th>
                </tr>
            </thead>
            <tbody>
                ${regions.slice(0, 15).map(r => `
                    <tr>
                        <td>${r.region}</td>
                        <td style="color: ${r.trend === 'increasing' ? '#00ff88' : r.trend === 'decreasing' ? '#ff4444' : '#aaa'};">
                            ${r.trend === 'increasing' ? '📈' : r.trend === 'decreasing' ? '📉' : '➡️'} ${r.trend}
                        </td>
                        <td>${(r.monthlyChange || 0).toFixed(1)}%</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

function renderBasicStats(records) {
    const stateStats = {};
    records.forEach(r => {
        if (!stateStats[r.state]) stateStats[r.state] = 0;
        stateStats[r.state] += (parseInt(r.age_18_greater) || 0);
    });

    const sorted = Object.entries(stateStats)
        .sort((a, b) => a[1] - b[1])
        .slice(0, 10);

    return `
        <h3 style="margin: 15px 0;">States with Lowest Enrollment (Potential Coldspots)</h3>
        <table class="data-table">
            <thead>
                <tr><th>State</th><th>Adult Enrollments</th></tr>
            </thead>
            <tbody>
                ${sorted.map(([state, count]) => `
                    <tr><td>${state}</td><td>${formatNumber(count)}</td></tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

// =====================================
// Initialize
// =====================================

document.addEventListener('DOMContentLoaded', () => {
    checkStatus();
    // Recheck status every 30 seconds
    setInterval(checkStatus, 30000);
});

/**
 * UIDAI Analytics Dashboard - Frontend JavaScript
 */

const API_BASE = 'http://localhost:3001/api';
const ML_API_BASE = 'http://localhost:8001';

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

    // Check ML backend status (via Node.js proxy to avoid CORS)
    try {
        const response = await fetch(`${API_BASE}/ml/api/health`);
        if (response.ok) {
            document.getElementById('ml-status').textContent = 'Online';
            document.querySelector('.status-item:last-child .status-dot').classList.add('online');
            document.querySelector('.status-item:last-child .status-dot').classList.remove('offline');
        } else {
            document.getElementById('ml-status').textContent = 'Offline';
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
            case 'gender':
                await loadGenderTracker();
                break;
            case 'map':
                await loadGenderGapMap();
                break;
            case 'vulnerable':
                await loadVulnerableGroups();
                break;
            case 'simulator':
                await loadImpactSimulator();
                break;
            default:
                showError('Unknown feature');
        }
    } catch (error) {
        showError(error.message);
    }
}

// =====================================
// Feature Implementations
// =====================================

async function loadGenderTracker() {
    setTitle('👥 Gender Inclusion Tracker');
    showLoading();

    try {
        // Fetch gender analysis data from new API
        const response = await fetch(`${API_BASE}/gender/high-risk?limit=500`);
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to fetch gender data');
        }

        const { riskDistribution, districts } = data.data;
        const totalHighRisk = data.data.totalHighRisk || 0;

        // Fetch state-level coverage
        const coverageResponse = await fetch(`${API_BASE}/gender/coverage?limit=500`);
        const coverageData = await coverageResponse.json();
        
        const stateAnalysis = coverageData.data?.stateAnalysis || [];
        const summary = coverageData.data?.summary || {};

        showContent(`
            <div class="alert alert-info">
                <strong>🎯 Gender Inclusion Analysis:</strong> 
                Monitoring female Aadhaar enrollment coverage to identify and address the digital gender gap.
            </div>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">${summary.totalStates || 0}</div>
                    <div class="stat-label">States Analyzed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${summary.totalDistricts || 0}</div>
                    <div class="stat-label">Districts Analyzed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" style="color: #ff4444;">${totalHighRisk}</div>
                    <div class="stat-label">High-Risk Districts</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${((summary.avgGenderGap || 0) * 100).toFixed(1)}%</div>
                    <div class="stat-label">Avg Gender Gap</div>
                </div>
            </div>

            <!-- Charts Section -->
            <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin: 25px 0;">
                <div style="background: rgba(0,0,0,0.3); border-radius: 15px; padding: 20px;">
                    <h3 style="margin: 0 0 15px; color: #00d4ff;">📊 Male vs Female Coverage by State</h3>
                    <canvas id="genderBarChart" height="250"></canvas>
                </div>
                <div style="background: rgba(0,0,0,0.3); border-radius: 15px; padding: 20px;">
                    <h3 style="margin: 0 0 15px; color: #ff6666;">⚠️ Risk Distribution</h3>
                    <canvas id="riskDoughnutChart" height="250"></canvas>
                </div>
            </div>

            <h3 style="margin: 25px 0 15px; color: #00d4ff;">📊 State-wise Gender Coverage</h3>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>State</th>
                        <th>Male Coverage</th>
                        <th>Female Coverage</th>
                        <th>Gender Gap</th>
                        <th>F:M Ratio</th>
                    </tr>
                </thead>
                <tbody>
                    ${stateAnalysis.slice(0, 10).map(s => `
                        <tr>
                            <td>${s.state}</td>
                            <td>${(s.maleCoverageRatio * 100).toFixed(1)}%</td>
                            <td style="color: ${s.femaleCoverageRatio < 0.46 ? '#ff4444' : '#00ff88'};">
                                ${(s.femaleCoverageRatio * 100).toFixed(1)}%
                            </td>
                            <td style="color: ${s.genderGap > 0.05 ? '#ff4444' : '#aaa'};">
                                ${(s.genderGap * 100).toFixed(1)}%
                            </td>
                            <td>${s.femaleToMaleRatio.toFixed(3)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>

            <h3 style="margin: 25px 0 15px; color: #ff6666;">⚠️ High-Risk Districts (Priority Intervention)</h3>
            ${districts.slice(0, 5).map(d => `
                <div class="alert ${d.riskLevel === 'CRITICAL' ? 'alert-critical' : d.riskLevel === 'HIGH' ? 'alert-warning' : 'alert-info'}">
                    <strong>${d.district}, ${d.state}</strong>
                    <span style="float: right; padding: 2px 8px; border-radius: 4px; 
                        background: ${d.riskLevel === 'CRITICAL' ? '#ff0000' : d.riskLevel === 'HIGH' ? '#ff9900' : '#ffcc00'}; 
                        color: white; font-size: 0.8rem;">
                        ${d.riskLevel}
                    </span>
                    <br>
                    <span style="color: #aaa; font-size: 0.85rem;">
                        Female Coverage: ${(d.femaleCoverageRatio * 100).toFixed(1)}% | 
                        Gender Gap: ${(d.genderGap * 100).toFixed(1)}% |
                        Risk Score: ${d.riskScore}
                    </span>
                </div>
            `).join('')}

            <div style="margin-top: 20px; text-align: center;">
                <button onclick="loadGenderRecommendations()" 
                    style="padding: 12px 24px; background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%); 
                    border: none; border-radius: 8px; color: white; font-size: 1rem; cursor: pointer;">
                    🤖 Get AI Recommendations
                </button>
            </div>
        `);

        // Create Bar Chart for Male vs Female Coverage
        const barCtx = document.getElementById('genderBarChart').getContext('2d');
        new Chart(barCtx, {
            type: 'bar',
            data: {
                labels: stateAnalysis.slice(0, 8).map(s => s.state.substring(0, 10)),
                datasets: [
                    {
                        label: 'Male Coverage %',
                        data: stateAnalysis.slice(0, 8).map(s => (s.maleCoverageRatio * 100).toFixed(1)),
                        backgroundColor: 'rgba(54, 162, 235, 0.8)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Female Coverage %',
                        data: stateAnalysis.slice(0, 8).map(s => (s.femaleCoverageRatio * 100).toFixed(1)),
                        backgroundColor: 'rgba(255, 99, 132, 0.8)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { labels: { color: '#fff' } }
                },
                scales: {
                    x: { ticks: { color: '#aaa' }, grid: { color: '#333' } },
                    y: { ticks: { color: '#aaa' }, grid: { color: '#333' }, beginAtZero: true, max: 100 }
                }
            }
        });

        // Create Doughnut Chart for Risk Distribution
        const doughnutCtx = document.getElementById('riskDoughnutChart').getContext('2d');
        new Chart(doughnutCtx, {
            type: 'doughnut',
            data: {
                labels: ['Critical', 'High', 'Moderate', 'Low Risk'],
                datasets: [{
                    data: [
                        riskDistribution?.critical || 0,
                        riskDistribution?.high || 0,
                        riskDistribution?.moderate || 0,
                        Math.max(0, (summary.totalDistricts || 0) - totalHighRisk)
                    ],
                    backgroundColor: ['#ff0000', '#ff9900', '#ffcc00', '#00ff88'],
                    borderWidth: 2,
                    borderColor: '#1a1a2e'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { 
                        position: 'bottom',
                        labels: { color: '#fff', padding: 15 } 
                    }
                }
            }
        });

    } catch (error) {
        showError(`Failed to load gender data: ${error.message}`);
    }
}

async function loadGenderRecommendations() {
    showLoading();
    setTitle('🤖 AI-Powered Recommendations');

    try {
        const response = await fetch(`${API_BASE}/gender/recommendations?limit=500`);
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to get recommendations');
        }

        const recommendations = data.data.recommendations || {};
        const aiGenerated = data.data.aiGenerated;

        showContent(`
            <div class="alert ${aiGenerated ? 'alert-info' : 'alert-warning'}">
                <strong>${aiGenerated ? '🤖 AI-Generated' : '📋 Standard'} Recommendations</strong>
                ${aiGenerated ? ' - Powered by Grok AI' : ' - AI unavailable, using built-in recommendations'}
            </div>

            <h3 style="margin: 20px 0 15px; color: #00d4ff;">📌 Overall Strategy</h3>
            <div class="alert alert-info">
                ${recommendations.overallStrategy || 'Focus on women-centric enrollment drives in high-risk districts.'}
            </div>

            <h3 style="margin: 20px 0 15px; color: #00ff88;">✅ Priority Actions</h3>
            <ol style="padding-left: 25px; color: #ccc;">
                ${(recommendations.priorityActions || []).map(action => `
                    <li style="margin: 10px 0; padding: 8px; background: rgba(0,255,136,0.1); border-radius: 5px;">
                        ${action}
                    </li>
                `).join('')}
            </ol>

            <h3 style="margin: 20px 0 15px; color: #ffcc00;">🏘️ District-Specific Recommendations</h3>
            ${Object.entries(recommendations.districtRecommendations || {}).slice(0, 8).map(([district, recs]) => `
                <div class="alert alert-info">
                    <strong>${district}</strong>
                    <ul style="margin: 5px 0 0 20px; font-size: 0.9rem;">
                        ${(Array.isArray(recs) ? recs : [recs]).map(r => `<li>${r}</li>`).join('')}
                    </ul>
                </div>
            `).join('')}

            <div style="margin-top: 20px; text-align: center;">
                <button onclick="loadGenderTracker()" 
                    style="padding: 10px 20px; background: #333; border: 1px solid #555; 
                    border-radius: 8px; color: white; cursor: pointer;">
                    ← Back to Gender Tracker
                </button>
            </div>
        `);

    } catch (error) {
        showError(`Failed to get recommendations: ${error.message}`);
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

// =====================================
// NEW FEATURES
// =====================================

async function loadGenderGapMap() {
    setTitle('🗺️ Gender Gap Map - India');

    try {
        const response = await fetch(`${API_BASE}/gender/coverage?limit=500`);
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to fetch data');
        }

        const stateAnalysis = data.data?.stateAnalysis || [];

        // Create a visual table-based map representation
        showContent(`
            <div class="alert alert-info">
                <strong>🗺️ Interactive Gender Gap Map:</strong> 
                Visual representation of gender coverage by state. Click on any state for details.
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 20px 0;">
                ${stateAnalysis.map(s => {
                    const gapPercent = s.genderGap * 100;
                    const color = gapPercent > 5 ? '#ff4444' : gapPercent > 3 ? '#ff9900' : gapPercent > 1 ? '#ffcc00' : '#00ff88';
                    return `
                        <div onclick="showStateDetails('${s.state}')" 
                            style="background: linear-gradient(135deg, ${color}22 0%, ${color}44 100%);
                            border: 2px solid ${color}; border-radius: 10px; padding: 15px; cursor: pointer;
                            transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" 
                            onmouseout="this.style.transform='scale(1)'">
                            <div style="font-weight: bold; color: white;">${s.state}</div>
                            <div style="font-size: 1.5rem; color: ${color};">${(s.genderGap * 100).toFixed(1)}%</div>
                            <div style="font-size: 0.8rem; color: #aaa;">Gender Gap</div>
                            <div style="font-size: 0.7rem; color: #888; margin-top: 5px;">
                                F: ${(s.femaleCoverageRatio * 100).toFixed(0)}% | M: ${(s.maleCoverageRatio * 100).toFixed(0)}%
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>

            <h3 style="margin: 25px 0 15px; color: #00d4ff;">📊 Legend</h3>
            <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                <span><span style="display: inline-block; width: 20px; height: 20px; background: #ff4444; border-radius: 5px;"></span> Critical (>5%)</span>
                <span><span style="display: inline-block; width: 20px; height: 20px; background: #ff9900; border-radius: 5px;"></span> High (3-5%)</span>
                <span><span style="display: inline-block; width: 20px; height: 20px; background: #ffcc00; border-radius: 5px;"></span> Moderate (1-3%)</span>
                <span><span style="display: inline-block; width: 20px; height: 20px; background: #00ff88; border-radius: 5px;"></span> Low (<1%)</span>
            </div>
        `);

    } catch (error) {
        showError(`Failed to load map: ${error.message}`);
    }
}

async function showStateDetails(stateName) {
    showLoading();
    setTitle(`📍 ${stateName} - Gender Analysis`);

    try {
        const response = await fetch(`${API_BASE}/gender/coverage?limit=500`);
        const data = await response.json();
        
        const stateData = data.data?.stateAnalysis?.find(s => s.state === stateName);
        const districts = data.data?.districtAnalysis?.filter(d => d.state === stateName) || [];

        if (!stateData) {
            showError('State data not found');
            return;
        }

        showContent(`
            <button onclick="loadGenderGapMap()" style="margin-bottom: 20px; padding: 8px 16px; background: #333; border: 1px solid #555; border-radius: 5px; color: white; cursor: pointer;">
                ← Back to Map
            </button>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">${(stateData.femaleCoverageRatio * 100).toFixed(1)}%</div>
                    <div class="stat-label">Female Coverage</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${(stateData.maleCoverageRatio * 100).toFixed(1)}%</div>
                    <div class="stat-label">Male Coverage</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" style="color: ${stateData.genderGap > 0.03 ? '#ff4444' : '#00ff88'};">
                        ${(stateData.genderGap * 100).toFixed(1)}%
                    </div>
                    <div class="stat-label">Gender Gap</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${stateData.districtCount}</div>
                    <div class="stat-label">Districts</div>
                </div>
            </div>

            <h3 style="margin: 25px 0 15px; color: #00d4ff;">📍 Districts in ${stateName}</h3>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>District</th>
                        <th>Female %</th>
                        <th>Male %</th>
                        <th>Gap</th>
                    </tr>
                </thead>
                <tbody>
                    ${districts.slice(0, 15).map(d => `
                        <tr>
                            <td>${d.district}</td>
                            <td style="color: ${d.femaleCoverageRatio < 0.46 ? '#ff4444' : '#00ff88'};">
                                ${(d.femaleCoverageRatio * 100).toFixed(1)}%
                            </td>
                            <td>${(d.maleCoverageRatio * 100).toFixed(1)}%</td>
                            <td style="color: ${d.genderGap > 0.05 ? '#ff4444' : '#aaa'};">
                                ${(d.genderGap * 100).toFixed(1)}%
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `);

    } catch (error) {
        showError(`Failed to load state details: ${error.message}`);
    }
}

async function loadVulnerableGroups() {
    setTitle('👵 Vulnerable Groups Inclusion Tracker');

    try {
        const response = await fetch(`${API_BASE}/vulnerable/analysis?limit=500`);
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to fetch data');
        }

        const { summary, stateAnalysis, highRiskByGroup } = data.data;

        showContent(`
            <div class="alert alert-info">
                <strong>👵🧒🧑‍🦽 Multi-Vulnerable Group Analysis:</strong> 
                Tracking inclusion for children (0-5), youth (5-17), adults, elderly (60+), and disabled populations.
            </div>

            <div class="stats-grid">
                <div class="stat-card" style="background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%);">
                    <div class="stat-value">${formatNumber(summary.nationalStats.children)}</div>
                    <div class="stat-label">Children (0-5)</div>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #2196F3 0%, #1565C0 100%);">
                    <div class="stat-value">${formatNumber(summary.nationalStats.youth)}</div>
                    <div class="stat-label">Youth (5-17)</div>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #9C27B0 0%, #6A1B9A 100%);">
                    <div class="stat-value">${formatNumber(summary.nationalStats.elderly)}</div>
                    <div class="stat-label">Elderly (60+)</div>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #FF9800 0%, #E65100 100%);">
                    <div class="stat-value">${formatNumber(summary.nationalStats.disabled)}</div>
                    <div class="stat-label">Disabled</div>
                </div>
            </div>

            <div class="stat-card" style="margin: 20px 0; text-align: center;">
                <div class="stat-value" style="font-size: 3rem; color: ${summary.avgInclusionScore > 70 ? '#00ff88' : summary.avgInclusionScore > 50 ? '#ffcc00' : '#ff4444'};">
                    ${summary.avgInclusionScore.toFixed(0)}
                </div>
                <div class="stat-label">National Inclusion Score (out of 100)</div>
            </div>

            <!-- Charts Section -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 25px 0;">
                <div style="background: rgba(0,0,0,0.3); border-radius: 15px; padding: 20px;">
                    <h3 style="margin: 0 0 15px; color: #00d4ff;">📊 Enrollment by Vulnerable Group</h3>
                    <canvas id="vulnerableBarChart" height="200"></canvas>
                </div>
                <div style="background: rgba(0,0,0,0.3); border-radius: 15px; padding: 20px;">
                    <h3 style="margin: 0 0 15px; color: #ff9900;">🎯 Inclusion Score Radar</h3>
                    <canvas id="inclusionRadarChart" height="200"></canvas>
                </div>
            </div>

            <h3 style="margin: 25px 0 15px; color: #ff6666;">⚠️ High-Risk Districts by Group</h3>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px;">
                <div style="background: rgba(76,175,80,0.1); border: 1px solid #4CAF50; border-radius: 10px; padding: 15px;">
                    <h4 style="color: #4CAF50;">🧒 Children (0-5) - At Risk</h4>
                    ${(highRiskByGroup?.children || []).slice(0, 5).map(d => `
                        <div style="padding: 5px 0; border-bottom: 1px solid #333;">
                            ${d.district}, ${d.state}
                            <span style="float: right; color: #ff4444;">${d.groups?.children?.coverageScore || 0}%</span>
                        </div>
                    `).join('') || '<p style="color: #666;">No high-risk districts</p>'}
                </div>

                <div style="background: rgba(156,39,176,0.1); border: 1px solid #9C27B0; border-radius: 10px; padding: 15px;">
                    <h4 style="color: #9C27B0;">👵 Elderly (60+) - At Risk</h4>
                    ${(highRiskByGroup?.elderly || []).slice(0, 5).map(d => `
                        <div style="padding: 5px 0; border-bottom: 1px solid #333;">
                            ${d.district}, ${d.state}
                            <span style="float: right; color: #ff4444;">${d.groups?.elderly?.coverageScore || 0}%</span>
                        </div>
                    `).join('') || '<p style="color: #666;">No high-risk districts</p>'}
                </div>

                <div style="background: rgba(255,152,0,0.1); border: 1px solid #FF9800; border-radius: 10px; padding: 15px;">
                    <h4 style="color: #FF9800;">🧑‍🦽 Disabled - At Risk</h4>
                    ${(highRiskByGroup?.disabled || []).slice(0, 5).map(d => `
                        <div style="padding: 5px 0; border-bottom: 1px solid #333;">
                            ${d.district}, ${d.state}
                            <span style="float: right; color: #ff4444;">${d.groups?.disabled?.coverageScore || 0}%</span>
                        </div>
                    `).join('') || '<p style="color: #666;">No high-risk districts</p>'}
                </div>
            </div>

            <h3 style="margin: 25px 0 15px; color: #00d4ff;">📊 State-wise Inclusion Scores</h3>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>State</th>
                        <th>Children</th>
                        <th>Elderly</th>
                        <th>Disabled</th>
                        <th>Overall</th>
                        <th>Risk Level</th>
                    </tr>
                </thead>
                <tbody>
                    ${stateAnalysis.slice(0, 10).map(s => `
                        <tr>
                            <td>${s.state}</td>
                            <td>${s.groups.children.coverageScore}%</td>
                            <td>${s.groups.elderly.coverageScore}%</td>
                            <td>${s.groups.disabled.coverageScore}%</td>
                            <td style="font-weight: bold;">${s.overallInclusionScore}%</td>
                            <td>
                                <span style="padding: 2px 8px; border-radius: 4px; font-size: 0.8rem;
                                    background: ${s.riskLevel === 'CRITICAL' ? '#ff0000' : s.riskLevel === 'HIGH' ? '#ff9900' : s.riskLevel === 'MODERATE' ? '#ffcc00' : '#00ff88'}; 
                                    color: ${s.riskLevel === 'LOW' ? '#000' : '#fff'};">
                                    ${s.riskLevel}
                                </span>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `);

        // Create Bar Chart for Vulnerable Group Enrollment
        const barCtx = document.getElementById('vulnerableBarChart').getContext('2d');
        new Chart(barCtx, {
            type: 'bar',
            data: {
                labels: ['Children (0-5)', 'Youth (5-17)', 'Adults (18+)', 'Elderly (60+)', 'Disabled'],
                datasets: [{
                    label: 'Enrollments',
                    data: [
                        summary.nationalStats.children,
                        summary.nationalStats.youth,
                        summary.nationalStats.adults,
                        summary.nationalStats.elderly,
                        summary.nationalStats.disabled
                    ],
                    backgroundColor: [
                        'rgba(76, 175, 80, 0.8)',
                        'rgba(33, 150, 243, 0.8)',
                        'rgba(0, 212, 255, 0.8)',
                        'rgba(156, 39, 176, 0.8)',
                        'rgba(255, 152, 0, 0.8)'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { ticks: { color: '#aaa' }, grid: { color: '#333' } },
                    y: { ticks: { color: '#aaa' }, grid: { color: '#333' } }
                }
            }
        });

        // Create Radar Chart for Inclusion Scores (top 5 states)
        const radarCtx = document.getElementById('inclusionRadarChart').getContext('2d');
        const top5States = stateAnalysis.slice(0, 5);
        new Chart(radarCtx, {
            type: 'radar',
            data: {
                labels: ['Children', 'Youth', 'Adults', 'Elderly', 'Disabled'],
                datasets: top5States.map((s, i) => ({
                    label: s.state.substring(0, 8),
                    data: [
                        s.groups.children.coverageScore,
                        s.groups.youth.coverageScore,
                        s.groups.adults.coverageScore,
                        s.groups.elderly.coverageScore,
                        s.groups.disabled.coverageScore
                    ],
                    borderColor: ['#ff6384', '#36a2eb', '#ffce56', '#4bc0c0', '#9966ff'][i],
                    backgroundColor: ['#ff638440', '#36a2eb40', '#ffce5640', '#4bc0c040', '#9966ff40'][i],
                    borderWidth: 2
                }))
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { 
                        position: 'bottom',
                        labels: { color: '#fff', boxWidth: 12, padding: 10 } 
                    }
                },
                scales: {
                    r: {
                        angleLines: { color: '#444' },
                        grid: { color: '#333' },
                        pointLabels: { color: '#aaa' },
                        ticks: { color: '#aaa', backdropColor: 'transparent' },
                        suggestedMin: 0,
                        suggestedMax: 100
                    }
                }
            }
        });

    } catch (error) {
        showError(`Failed to load vulnerable groups: ${error.message}`);
    }
}

async function loadImpactSimulator() {
    setTitle('💰 Impact Simulator - ROI Calculator');

    showContent(`
        <div class="alert alert-info">
            <strong>💰 Intervention Impact Simulator:</strong> 
            Calculate projected enrollments and welfare benefits for different intervention strategies.
        </div>

        <div style="background: rgba(0,212,255,0.1); border: 1px solid #00d4ff; border-radius: 10px; padding: 20px; margin: 20px 0;">
            <h3 style="color: #00d4ff; margin-top: 0;">📝 Configure Intervention</h3>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                <div>
                    <label style="display: block; margin-bottom: 5px; color: #aaa;">Intervention Type</label>
                    <select id="sim-intervention" style="width: 100%; padding: 10px; background: #1a1a2e; border: 1px solid #555; border-radius: 5px; color: white;">
                        <option value="CAMP">Women-Only Camps</option>
                        <option value="MOBILE_VAN">Mobile Enrollment Vans</option>
                        <option value="DOORSTEP">Doorstep Service</option>
                        <option value="AWARENESS_CAMPAIGN">Awareness Campaign</option>
                    </select>
                </div>
                <div>
                    <label style="display: block; margin-bottom: 5px; color: #aaa;">Quantity / Number</label>
                    <input type="number" id="sim-quantity" value="10" min="1" max="100" 
                        style="width: 100%; padding: 10px; background: #1a1a2e; border: 1px solid #555; border-radius: 5px; color: white;">
                </div>
                <div>
                    <label style="display: block; margin-bottom: 5px; color: #aaa;">Days (for vans)</label>
                    <input type="number" id="sim-days" value="5" min="1" max="30" 
                        style="width: 100%; padding: 10px; background: #1a1a2e; border: 1px solid #555; border-radius: 5px; color: white;">
                </div>
                <div>
                    <label style="display: block; margin-bottom: 5px; color: #aaa;">Target Group</label>
                    <select id="sim-target" style="width: 100%; padding: 10px; background: #1a1a2e; border: 1px solid #555; border-radius: 5px; color: white;">
                        <option value="WOMEN">Women</option>
                        <option value="ELDERLY">Elderly</option>
                        <option value="CHILDREN">Children</option>
                        <option value="ALL">All Groups</option>
                    </select>
                </div>
            </div>
            
            <button onclick="runSimulation()" 
                style="margin-top: 20px; padding: 12px 30px; background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%); 
                border: none; border-radius: 8px; color: white; font-size: 1rem; cursor: pointer; width: 100%;">
                🚀 Calculate Impact
            </button>
        </div>

        <div id="sim-results" style="display: none;">
            <!-- Results will be displayed here -->
        </div>

        <h3 style="margin: 25px 0 15px; color: #ffcc00;">💡 Quick Presets</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 10px;">
            <button onclick="runPreset('camp5')" class="preset-btn" style="padding: 15px; background: #1a1a2e; border: 1px solid #555; border-radius: 8px; color: white; cursor: pointer; text-align: left;">
                <strong>Small District</strong><br>
                <span style="color: #aaa; font-size: 0.9rem;">5 camps, women focus</span>
            </button>
            <button onclick="runPreset('mixed')" class="preset-btn" style="padding: 15px; background: #1a1a2e; border: 1px solid #555; border-radius: 8px; color: white; cursor: pointer; text-align: left;">
                <strong>Medium District</strong><br>
                <span style="color: #aaa; font-size: 0.9rem;">10 camps + mobile vans</span>
            </button>
            <button onclick="runPreset('intensive')" class="preset-btn" style="padding: 15px; background: #1a1a2e; border: 1px solid #555; border-radius: 8px; color: white; cursor: pointer; text-align: left;">
                <strong>Large District</strong><br>
                <span style="color: #aaa; font-size: 0.9rem;">20 camps, intensive drive</span>
            </button>
        </div>
    `);
}

async function runSimulation() {
    const intervention = document.getElementById('sim-intervention').value;
    const quantity = parseInt(document.getElementById('sim-quantity').value);
    const days = parseInt(document.getElementById('sim-days').value);
    const targetGroup = document.getElementById('sim-target').value;

    const resultsDiv = document.getElementById('sim-results');
    resultsDiv.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    resultsDiv.style.display = 'block';

    try {
        const response = await fetch(`${API_BASE}/simulate/intervention`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ intervention, quantity, days, targetGroup })
        });
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Simulation failed');
        }

        const result = data.data;
        const benefits = result.benefitsUnlocked;

        resultsDiv.innerHTML = `
            <h3 style="margin: 20px 0 15px; color: #00ff88;">📊 Simulation Results</h3>
            
            <div class="stats-grid">
                <div class="stat-card" style="background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%);">
                    <div class="stat-value">${formatNumber(result.projections.totalReach)}</div>
                    <div class="stat-label">People Reached</div>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);">
                    <div class="stat-value">${formatNumber(result.projections.projectedEnrollments)}</div>
                    <div class="stat-label">Projected Enrollments</div>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #ff9900 0%, #cc7700 100%);">
                    <div class="stat-value">₹${formatNumber(result.projections.totalCost)}</div>
                    <div class="stat-label">Total Cost</div>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #9C27B0 0%, #6A1B9A 100%);">
                    <div class="stat-value">${benefits.totalAnnualFormatted}</div>
                    <div class="stat-label">Annual Benefits Unlocked</div>
                </div>
            </div>

            <div class="stats-grid" style="margin-top: 15px;">
                <div class="stat-card">
                    <div class="stat-value" style="color: ${parseFloat(result.roi.value) > 100 ? '#00ff88' : '#ffcc00'};">
                        ${result.roi.value}
                    </div>
                    <div class="stat-label">Return on Investment</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${result.roi.breakEvenMonths}</div>
                    <div class="stat-label">Months to Break Even</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">₹${result.projections.costPerEnrollment}</div>
                    <div class="stat-label">Cost per Enrollment</div>
                </div>
            </div>

            <div class="alert ${result.roi.recommendation === 'HIGHLY RECOMMENDED' ? 'alert-info' : 'alert-warning'}" style="margin-top: 20px;">
                <strong>📋 Recommendation:</strong> ${result.roi.recommendation}
            </div>

            <h4 style="margin: 20px 0 10px; color: #00d4ff;">💰 Welfare Benefits Breakdown</h4>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Benefit</th>
                        <th>Beneficiaries</th>
                        <th>Annual Value</th>
                    </tr>
                </thead>
                <tbody>
                    ${benefits.benefits.map(b => `
                        <tr>
                            <td>${b.name}</td>
                            <td>${formatNumber(b.beneficiaries)} (${b.eligiblePercent}%)</td>
                            <td>₹${formatNumber(b.annualValue)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;

    } catch (error) {
        resultsDiv.innerHTML = `
            <div class="alert alert-critical">
                <strong>Error:</strong> ${error.message}
            </div>
        `;
    }
}

async function runPreset(preset) {
    let intervention, quantity, days, targetGroup;

    switch (preset) {
        case 'camp5':
            intervention = 'CAMP';
            quantity = 5;
            days = 1;
            targetGroup = 'WOMEN';
            break;
        case 'mixed':
            intervention = 'CAMP';
            quantity = 10;
            days = 5;
            targetGroup = 'ALL';
            break;
        case 'intensive':
            intervention = 'CAMP';
            quantity = 20;
            days = 10;
            targetGroup = 'WOMEN';
            break;
    }

    // Update form values
    document.getElementById('sim-intervention').value = intervention;
    document.getElementById('sim-quantity').value = quantity;
    document.getElementById('sim-days').value = days;
    document.getElementById('sim-target').value = targetGroup;

    // Run simulation
    await runSimulation();
}

// =====================================
// Initialize
// =====================================

document.addEventListener('DOMContentLoaded', () => {
    checkStatus();
    // Recheck status every 30 seconds
    setInterval(checkStatus, 30000);
});

/**
 * Gender Analysis Service
 * Computes gender coverage ratios and identifies high-risk districts
 */

import Groq from 'groq-sdk';

// Grok API keys rotation
const GROK_KEYS = [
    process.env.GROK_API_KEY_1,
    process.env.GROK_API_KEY_2,
    process.env.GROK_API_KEY_3,
    process.env.GROK_API_KEY_4,
    process.env.GROK_API_KEY_5
].filter(Boolean);

let currentKeyIndex = 0;

function getNextGrokClient() {
    const key = GROK_KEYS[currentKeyIndex];
    currentKeyIndex = (currentKeyIndex + 1) % GROK_KEYS.length;
    return new Groq({ apiKey: key });
}

/**
 * Compute gender coverage ratios from enrollment data
 * @param {Array} records - Enrollment records
 * @returns {Object} Coverage analysis by state/district
 */
export function computeGenderCoverage(records) {
    if (!records || records.length === 0) {
        return { success: false, error: 'No records provided' };
    }

    const stateStats = {};
    const districtStats = {};

    records.forEach(record => {
        const state = record.state || 'Unknown';
        const district = record.district || 'Unknown';
        
        // Parse age group counts
        const age0_5 = parseInt(record.age_0_5) || 0;
        const age5_17 = parseInt(record.age_5_17) || 0;
        const age18Plus = parseInt(record.age_18_greater) || 0;
        const total = age0_5 + age5_17 + age18Plus;

        // Since actual gender data may not be available, estimate based on national ratios
        // National average: ~51.5% male, ~48.5% female
        // Apply regional variation factors
        const genderRatio = getRegionalGenderRatio(state, district);
        const maleEstimate = Math.round(total * genderRatio.male);
        const femaleEstimate = Math.round(total * genderRatio.female);

        // State aggregation
        if (!stateStats[state]) {
            stateStats[state] = {
                state,
                totalEnrollment: 0,
                maleEstimate: 0,
                femaleEstimate: 0,
                districts: new Set(),
                records: 0
            };
        }
        stateStats[state].totalEnrollment += total;
        stateStats[state].maleEstimate += maleEstimate;
        stateStats[state].femaleEstimate += femaleEstimate;
        stateStats[state].districts.add(district);
        stateStats[state].records++;

        // District aggregation
        const distKey = `${state}|${district}`;
        if (!districtStats[distKey]) {
            districtStats[distKey] = {
                state,
                district,
                totalEnrollment: 0,
                maleEstimate: 0,
                femaleEstimate: 0,
                records: 0
            };
        }
        districtStats[distKey].totalEnrollment += total;
        districtStats[distKey].maleEstimate += maleEstimate;
        districtStats[distKey].femaleEstimate += femaleEstimate;
        districtStats[distKey].records++;
    });

    // Calculate coverage ratios
    const stateAnalysis = Object.values(stateStats).map(s => ({
        state: s.state,
        totalEnrollment: s.totalEnrollment,
        maleEnrollment: s.maleEstimate,
        femaleEnrollment: s.femaleEstimate,
        maleCoverageRatio: s.totalEnrollment > 0 ? (s.maleEstimate / s.totalEnrollment) : 0,
        femaleCoverageRatio: s.totalEnrollment > 0 ? (s.femaleEstimate / s.totalEnrollment) : 0,
        genderGap: s.totalEnrollment > 0 ? ((s.maleEstimate - s.femaleEstimate) / s.totalEnrollment) : 0,
        femaleToMaleRatio: s.maleEstimate > 0 ? (s.femaleEstimate / s.maleEstimate) : 0,
        districtCount: s.districts.size,
        records: s.records
    })).sort((a, b) => a.femaleCoverageRatio - b.femaleCoverageRatio);

    const districtAnalysis = Object.values(districtStats).map(d => ({
        state: d.state,
        district: d.district,
        totalEnrollment: d.totalEnrollment,
        maleEnrollment: d.maleEstimate,
        femaleEnrollment: d.femaleEstimate,
        maleCoverageRatio: d.totalEnrollment > 0 ? (d.maleEstimate / d.totalEnrollment) : 0,
        femaleCoverageRatio: d.totalEnrollment > 0 ? (d.femaleEstimate / d.totalEnrollment) : 0,
        genderGap: d.totalEnrollment > 0 ? ((d.maleEstimate - d.femaleEstimate) / d.totalEnrollment) : 0,
        femaleToMaleRatio: d.maleEstimate > 0 ? (d.femaleEstimate / d.maleEstimate) : 0,
        records: d.records
    })).sort((a, b) => a.femaleCoverageRatio - b.femaleCoverageRatio);

    return {
        success: true,
        summary: {
            totalRecords: records.length,
            totalStates: stateAnalysis.length,
            totalDistricts: districtAnalysis.length,
            nationalMaleCoverage: stateAnalysis.reduce((sum, s) => sum + s.maleEnrollment, 0),
            nationalFemaleCoverage: stateAnalysis.reduce((sum, s) => sum + s.femaleEnrollment, 0),
            avgGenderGap: stateAnalysis.reduce((sum, s) => sum + s.genderGap, 0) / stateAnalysis.length
        },
        stateAnalysis,
        districtAnalysis
    };
}

/**
 * Get regional gender ratio based on state/district
 * Applies known regional variations in gender ratios
 */
function getRegionalGenderRatio(state, district) {
    // Regional gender ratio variations based on Census data patterns
    const stateFactors = {
        'Haryana': { male: 0.535, female: 0.465 },
        'Punjab': { male: 0.530, female: 0.470 },
        'Jammu And Kashmir': { male: 0.530, female: 0.470 },
        'Rajasthan': { male: 0.528, female: 0.472 },
        'Uttar Pradesh': { male: 0.525, female: 0.475 },
        'Bihar': { male: 0.524, female: 0.476 },
        'Gujarat': { male: 0.522, female: 0.478 },
        'Madhya Pradesh': { male: 0.520, female: 0.480 },
        'Maharashtra': { male: 0.518, female: 0.482 },
        'Delhi': { male: 0.530, female: 0.470 },
        'Kerala': { male: 0.485, female: 0.515 },
        'Tamil Nadu': { male: 0.498, female: 0.502 },
        'Andhra Pradesh': { male: 0.502, female: 0.498 },
        'Karnataka': { male: 0.510, female: 0.490 },
        'West Bengal': { male: 0.512, female: 0.488 },
        'Odisha': { male: 0.508, female: 0.492 }
    };

    // Default national average
    const defaultRatio = { male: 0.515, female: 0.485 };
    
    // Find matching state (case-insensitive partial match)
    const stateLower = state?.toLowerCase() || '';
    for (const [key, value] of Object.entries(stateFactors)) {
        if (stateLower.includes(key.toLowerCase()) || key.toLowerCase().includes(stateLower)) {
            return value;
        }
    }
    
    return defaultRatio;
}

/**
 * Identify high-risk districts for female exclusion
 * @param {Array} districtAnalysis - District-level coverage data
 * @param {number} threshold - Female coverage ratio threshold (default 0.46)
 * @returns {Array} High-risk districts with risk scores
 */
export function identifyHighRiskDistricts(districtAnalysis, threshold = 0.46) {
    if (!districtAnalysis || districtAnalysis.length === 0) {
        return [];
    }

    const highRisk = districtAnalysis
        .filter(d => d.femaleCoverageRatio < threshold)
        .map(d => ({
            ...d,
            riskScore: calculateRiskScore(d),
            riskLevel: getRiskLevel(d.femaleCoverageRatio),
            interventionPriority: getInterventionPriority(d)
        }))
        .sort((a, b) => b.riskScore - a.riskScore);

    return highRisk;
}

/**
 * Calculate composite risk score
 */
function calculateRiskScore(district) {
    // Risk factors:
    // 1. Low female coverage ratio (40%)
    // 2. Wide gender gap (30%)
    // 3. Low absolute female enrollment (20%)
    // 4. Population size factor (10%)

    const coverageScore = Math.max(0, (0.50 - district.femaleCoverageRatio) * 100);
    const gapScore = Math.max(0, district.genderGap * 100);
    const enrollmentScore = Math.min(10, 10 - Math.log10(district.femaleEnrollment + 1));
    
    return Math.round(
        (coverageScore * 0.4) +
        (gapScore * 0.3) +
        (enrollmentScore * 0.2) +
        (5 * 0.1) // Base population factor
    );
}

/**
 * Get risk level classification
 */
function getRiskLevel(femaleCoverageRatio) {
    if (femaleCoverageRatio < 0.40) return 'CRITICAL';
    if (femaleCoverageRatio < 0.44) return 'HIGH';
    if (femaleCoverageRatio < 0.46) return 'MODERATE';
    return 'LOW';
}

/**
 * Get intervention priority
 */
function getInterventionPriority(district) {
    const riskLevel = getRiskLevel(district.femaleCoverageRatio);
    const priorities = {
        'CRITICAL': 1,
        'HIGH': 2,
        'MODERATE': 3,
        'LOW': 4
    };
    return priorities[riskLevel] || 4;
}

/**
 * Generate intervention recommendations for a district
 */
export function generateRecommendations(district) {
    const recommendations = [];
    const riskLevel = getRiskLevel(district.femaleCoverageRatio);

    // Women-only camps
    if (riskLevel === 'CRITICAL' || riskLevel === 'HIGH') {
        recommendations.push({
            type: 'WOMEN_ONLY_CAMP',
            title: 'Women-Only Enrollment Camps',
            description: `Organize dedicated Aadhaar enrollment camps for women in ${district.district}, ${district.state}`,
            priority: 'HIGH',
            estimatedImpact: 'High',
            targetBeneficiaries: Math.round(district.maleEnrollment - district.femaleEnrollment),
            suggestedLocations: ['Community Centers', 'Anganwadi Centers', 'Schools', 'SHG Meeting Points']
        });
    }

    // Mobile enrollment vans
    if (district.totalEnrollment < 10000 || riskLevel !== 'LOW') {
        recommendations.push({
            type: 'MOBILE_VAN',
            title: 'Mobile Enrollment Van Deployment',
            description: `Deploy mobile Aadhaar enrollment vans to reach remote areas in ${district.district}`,
            priority: riskLevel === 'CRITICAL' ? 'HIGH' : 'MEDIUM',
            estimatedImpact: 'Medium-High',
            coverage: 'Remote and underserved areas'
        });
    }

    // Awareness campaigns
    recommendations.push({
        type: 'AWARENESS',
        title: 'Gender-Focused Awareness Campaign',
        description: `Launch awareness campaign highlighting benefits of Aadhaar for women (LPG subsidy, pension, bank accounts)`,
        priority: 'MEDIUM',
        estimatedImpact: 'Medium',
        channels: ['Local Radio', 'Community Meetings', 'ASHA Workers', 'Anganwadi Workers']
    });

    // SHG partnerships
    if (riskLevel !== 'LOW') {
        recommendations.push({
            type: 'SHG_PARTNERSHIP',
            title: 'Self-Help Group Partnership',
            description: 'Partner with local SHGs to identify and assist unenrolled women',
            priority: 'MEDIUM',
            estimatedImpact: 'High',
            approach: 'Peer-to-peer outreach through SHG networks'
        });
    }

    // Language support
    recommendations.push({
        type: 'LANGUAGE_SUPPORT',
        title: 'Regional Language Support',
        description: `Provide enrollment assistance in local language with female operators`,
        priority: 'MEDIUM',
        estimatedImpact: 'Medium'
    });

    return recommendations;
}

/**
 * Use Grok AI to generate contextual recommendations
 */
export async function generateAIRecommendations(highRiskDistricts) {
    if (!GROK_KEYS.length || highRiskDistricts.length === 0) {
        return generateFallbackRecommendations(highRiskDistricts);
    }

    try {
        const client = getNextGrokClient();
        
        const districtSummary = highRiskDistricts.slice(0, 10).map(d => 
            `${d.district}, ${d.state}: ${(d.femaleCoverageRatio * 100).toFixed(1)}% female coverage, ${d.riskLevel} risk`
        ).join('\n');

        const prompt = `You are an expert in gender inclusion and digital identity programs in India. 

Analyze these high-risk districts for female Aadhaar enrollment gaps and provide specific, actionable recommendations:

${districtSummary}

For each district, consider:
1. Cultural barriers to women's enrollment
2. Infrastructure challenges  
3. Effective outreach strategies
4. Success stories from similar regions

Provide 3-5 specific, implementable recommendations for UIDAI to improve female enrollment in these areas. Focus on:
- Women-only enrollment camps
- Mobile van deployment
- Partnerships with ASHA, Anganwadi workers
- Self-help group engagement
- Regional language support

Format your response as JSON with structure:
{
  "overallStrategy": "...",
  "priorityActions": [...],
  "districtRecommendations": {
    "district_name": ["recommendation1", "recommendation2"]
  }
}`;

        const completion = await client.chat.completions.create({
            messages: [{ role: 'user', content: prompt }],
            model: 'llama-3.3-70b-versatile',
            temperature: 0.7,
            max_tokens: 2000
        });

        const response = completion.choices[0]?.message?.content;
        
        // Try to parse JSON from response
        try {
            const jsonMatch = response.match(/\{[\s\S]*\}/);
            if (jsonMatch) {
                return {
                    success: true,
                    aiGenerated: true,
                    recommendations: JSON.parse(jsonMatch[0])
                };
            }
        } catch (parseError) {
            // Return raw text if JSON parsing fails
            return {
                success: true,
                aiGenerated: true,
                recommendations: {
                    overallStrategy: response,
                    priorityActions: [],
                    districtRecommendations: {}
                }
            };
        }

        return {
            success: true,
            aiGenerated: true,
            recommendations: { rawResponse: response }
        };

    } catch (error) {
        console.error('Grok AI error:', error.message);
        return generateFallbackRecommendations(highRiskDistricts);
    }
}

/**
 * Fallback recommendations when AI is unavailable
 */
function generateFallbackRecommendations(highRiskDistricts) {
    return {
        success: true,
        aiGenerated: false,
        recommendations: {
            overallStrategy: 'Focus on women-centric enrollment drives in identified high-risk districts, leveraging existing ASHA and Anganwadi networks for door-to-door outreach.',
            priorityActions: [
                'Deploy mobile enrollment vans to CRITICAL risk districts within 2 weeks',
                'Organize women-only camps in HIGH risk districts monthly',
                'Train female enrollment operators for all centers',
                'Partner with local SHGs for peer outreach',
                'Launch awareness campaign in regional languages'
            ],
            districtRecommendations: Object.fromEntries(
                highRiskDistricts.slice(0, 10).map(d => [
                    `${d.district}, ${d.state}`,
                    generateRecommendations(d).map(r => r.title)
                ])
            )
        }
    };
}

export default {
    computeGenderCoverage,
    identifyHighRiskDistricts,
    generateRecommendations,
    generateAIRecommendations
};

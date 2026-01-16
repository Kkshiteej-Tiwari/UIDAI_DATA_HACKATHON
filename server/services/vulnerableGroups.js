/**
 * Multi-Vulnerable Group Tracker Service
 * Extends gender analysis to track elderly, children, and other vulnerable groups
 */

/**
 * Compute inclusion scores for all vulnerable groups
 * @param {Array} records - Enrollment records
 * @returns {Object} Analysis by vulnerable group
 */
export function computeVulnerableGroupAnalysis(records) {
    if (!records || records.length === 0) {
        return { success: false, error: 'No records provided' };
    }

    const stateStats = {};
    const districtStats = {};

    records.forEach(record => {
        const state = record.state || 'Unknown';
        const district = record.district || 'Unknown';
        
        // Parse age group counts
        const children = parseInt(record.age_0_5) || 0;      // Children (0-5)
        const youth = parseInt(record.age_5_17) || 0;        // Youth (5-17)
        const adults = parseInt(record.age_18_greater) || 0; // Adults (18+)
        const total = children + youth + adults;

        // Estimate elderly from adult population (approx 15% of adults are 60+)
        const elderlyEstimate = Math.round(adults * 0.15);
        // Estimate disabled population (approx 2.2% of population based on Census 2011)
        const disabledEstimate = Math.round(total * 0.022);

        // State aggregation
        if (!stateStats[state]) {
            stateStats[state] = {
                state,
                children: 0,
                youth: 0,
                adults: 0,
                elderly: 0,
                disabled: 0,
                total: 0,
                districts: new Set()
            };
        }
        stateStats[state].children += children;
        stateStats[state].youth += youth;
        stateStats[state].adults += adults;
        stateStats[state].elderly += elderlyEstimate;
        stateStats[state].disabled += disabledEstimate;
        stateStats[state].total += total;
        stateStats[state].districts.add(district);

        // District aggregation
        const distKey = `${state}|${district}`;
        if (!districtStats[distKey]) {
            districtStats[distKey] = {
                state,
                district,
                children: 0,
                youth: 0,
                adults: 0,
                elderly: 0,
                disabled: 0,
                total: 0
            };
        }
        districtStats[distKey].children += children;
        districtStats[distKey].youth += youth;
        districtStats[distKey].adults += adults;
        districtStats[distKey].elderly += elderlyEstimate;
        districtStats[distKey].disabled += disabledEstimate;
        districtStats[distKey].total += total;
    });

    // Calculate inclusion scores and coverage for each state
    const stateAnalysis = Object.values(stateStats).map(s => {
        const scores = calculateInclusionScores(s);
        return {
            state: s.state,
            districtCount: s.districts.size,
            totalEnrollment: s.total,
            groups: {
                children: { enrolled: s.children, ...scores.children },
                youth: { enrolled: s.youth, ...scores.youth },
                adults: { enrolled: s.adults, ...scores.adults },
                elderly: { enrolled: s.elderly, ...scores.elderly },
                disabled: { enrolled: s.disabled, ...scores.disabled }
            },
            overallInclusionScore: scores.overall,
            riskLevel: getInclusionRiskLevel(scores.overall)
        };
    }).sort((a, b) => a.overallInclusionScore - b.overallInclusionScore);

    // Calculate for districts
    const districtAnalysis = Object.values(districtStats).map(d => {
        const scores = calculateInclusionScores(d);
        return {
            state: d.state,
            district: d.district,
            totalEnrollment: d.total,
            groups: {
                children: { enrolled: d.children, ...scores.children },
                youth: { enrolled: d.youth, ...scores.youth },
                adults: { enrolled: d.adults, ...scores.adults },
                elderly: { enrolled: d.elderly, ...scores.elderly },
                disabled: { enrolled: d.disabled, ...scores.disabled }
            },
            overallInclusionScore: scores.overall,
            riskLevel: getInclusionRiskLevel(scores.overall)
        };
    }).sort((a, b) => a.overallInclusionScore - b.overallInclusionScore);

    // Find high-risk districts for each group
    const highRiskByGroup = {
        children: districtAnalysis.filter(d => d.groups.children.coverageScore < 40).slice(0, 10),
        elderly: districtAnalysis.filter(d => d.groups.elderly.coverageScore < 40).slice(0, 10),
        disabled: districtAnalysis.filter(d => d.groups.disabled.coverageScore < 40).slice(0, 10)
    };

    return {
        success: true,
        summary: {
            totalRecords: records.length,
            totalStates: stateAnalysis.length,
            totalDistricts: districtAnalysis.length,
            nationalStats: {
                children: stateAnalysis.reduce((sum, s) => sum + s.groups.children.enrolled, 0),
                youth: stateAnalysis.reduce((sum, s) => sum + s.groups.youth.enrolled, 0),
                adults: stateAnalysis.reduce((sum, s) => sum + s.groups.adults.enrolled, 0),
                elderly: stateAnalysis.reduce((sum, s) => sum + s.groups.elderly.enrolled, 0),
                disabled: stateAnalysis.reduce((sum, s) => sum + s.groups.disabled.enrolled, 0)
            },
            avgInclusionScore: stateAnalysis.reduce((sum, s) => sum + s.overallInclusionScore, 0) / stateAnalysis.length
        },
        stateAnalysis,
        districtAnalysis,
        highRiskByGroup
    };
}

/**
 * Calculate inclusion scores for a region
 */
function calculateInclusionScores(stats) {
    const total = stats.total || 1;
    
    // Expected percentages based on national demographics
    const expected = {
        children: 0.12,    // 12% of population is 0-5
        youth: 0.25,       // 25% is 5-17
        adults: 0.63,      // 63% is 18+
        elderly: 0.10,     // 10% is 60+
        disabled: 0.022    // 2.2% has disability
    };

    // Actual percentages
    const actual = {
        children: stats.children / total,
        youth: stats.youth / total,
        adults: stats.adults / total,
        elderly: stats.elderly / total,
        disabled: stats.disabled / total
    };

    // Coverage scores (how well each group is represented vs expected)
    const scores = {};
    let totalScore = 0;

    for (const group of Object.keys(expected)) {
        const ratio = actual[group] / expected[group];
        const coverageScore = Math.min(100, Math.round(ratio * 100));
        const gap = expected[group] - actual[group];
        
        scores[group] = {
            coverageScore,
            expectedPercent: (expected[group] * 100).toFixed(1),
            actualPercent: (actual[group] * 100).toFixed(1),
            gap: (gap * 100).toFixed(2),
            status: coverageScore >= 80 ? 'GOOD' : coverageScore >= 50 ? 'MODERATE' : 'LOW'
        };
        
        totalScore += coverageScore;
    }

    scores.overall = Math.round(totalScore / 5);

    return scores;
}

/**
 * Get risk level based on inclusion score
 */
function getInclusionRiskLevel(score) {
    if (score < 40) return 'CRITICAL';
    if (score < 60) return 'HIGH';
    if (score < 80) return 'MODERATE';
    return 'LOW';
}

/**
 * Generate recommendations for improving inclusion of vulnerable groups
 */
export function generateVulnerableGroupRecommendations(district) {
    const recommendations = [];

    // Children recommendations
    if (district.groups?.children?.status === 'LOW') {
        recommendations.push({
            group: 'Children (0-5)',
            type: 'ANGANWADI_PARTNERSHIP',
            title: 'Anganwadi Center Enrollment Drive',
            description: 'Partner with Anganwadi centers to enroll children during immunization drives',
            priority: 'HIGH'
        });
    }

    // Elderly recommendations
    if (district.groups?.elderly?.status === 'LOW') {
        recommendations.push({
            group: 'Elderly (60+)',
            type: 'DOORSTEP_SERVICE',
            title: 'Doorstep Enrollment for Seniors',
            description: 'Mobile enrollment teams visiting homes of elderly citizens',
            priority: 'HIGH'
        });
        recommendations.push({
            group: 'Elderly (60+)',
            type: 'PENSION_LINKAGE',
            title: 'Old Age Pension Camp Integration',
            description: 'Conduct Aadhaar enrollment at pension distribution camps',
            priority: 'MEDIUM'
        });
    }

    // Disabled recommendations
    if (district.groups?.disabled?.status === 'LOW') {
        recommendations.push({
            group: 'Disabled',
            type: 'ACCESSIBILITY',
            title: 'Accessible Enrollment Centers',
            description: 'Ensure all centers have ramps, wheelchair access, and trained staff',
            priority: 'HIGH'
        });
        recommendations.push({
            group: 'Disabled',
            type: 'SPECIAL_CAMP',
            title: 'Special Camps at Disability Centers',
            description: 'Conduct enrollment at rehabilitation centers and special schools',
            priority: 'MEDIUM'
        });
    }

    return recommendations;
}

export default {
    computeVulnerableGroupAnalysis,
    generateVulnerableGroupRecommendations
};

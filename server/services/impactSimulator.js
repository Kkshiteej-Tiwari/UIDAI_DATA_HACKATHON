/**
 * Impact Simulator / ROI Calculator Service
 * Estimates impact of interventions on enrollment and welfare benefits
 */

// Welfare benefit values (in INR)
const WELFARE_BENEFITS = {
    LPG_SUBSIDY: 500,           // Monthly LPG subsidy per beneficiary
    PENSION: 1000,              // Monthly old age pension
    SCHOLARSHIP: 2000,          // Annual scholarship for students
    JAN_DHAN_ACCESS: 10000,     // Average bank account benefit
    MGNREGA_WAGES: 3000,        // Monthly MGNREGA wages
    CROP_INSURANCE: 5000,       // Annual crop insurance benefit
    HEALTH_INSURANCE: 500000,   // Ayushman Bharat coverage
    RATION_SUBSIDY: 1200        // Monthly ration card benefit
};

// Average costs per intervention
const INTERVENTION_COSTS = {
    CAMP: {
        cost: 25000,            // Cost per camp
        capacity: 500,          // People served per camp
        successRate: 0.85       // 85% of attendees get enrolled
    },
    MOBILE_VAN: {
        cost: 15000,            // Daily cost per van
        capacity: 100,          // People served per day
        successRate: 0.90
    },
    DOORSTEP: {
        cost: 500,              // Cost per doorstep visit
        capacity: 5,            // People per visit
        successRate: 0.95
    },
    AWARENESS_CAMPAIGN: {
        cost: 50000,            // Cost per campaign
        reach: 5000,            // People reached
        conversionRate: 0.15    // 15% come for enrollment
    }
};

/**
 * Simulate impact of deploying interventions
 * @param {Object} params - Simulation parameters
 * @returns {Object} Projected impact and ROI
 */
export function simulateIntervention(params) {
    const {
        intervention,           // 'CAMP', 'MOBILE_VAN', 'DOORSTEP', 'AWARENESS_CAMPAIGN'
        quantity,               // Number of interventions
        days = 1,               // Days of operation (for mobile vans)
        district,               // District info (optional)
        targetGroup = 'WOMEN'   // 'WOMEN', 'ELDERLY', 'CHILDREN', 'DISABLED', 'ALL'
    } = params;

    const config = INTERVENTION_COSTS[intervention];
    if (!config) {
        return { success: false, error: 'Invalid intervention type' };
    }

    // Calculate reach and enrollments
    let totalReach, projectedEnrollments, totalCost;

    if (intervention === 'MOBILE_VAN') {
        totalReach = config.capacity * quantity * days;
        projectedEnrollments = Math.round(totalReach * config.successRate);
        totalCost = config.cost * quantity * days;
    } else if (intervention === 'AWARENESS_CAMPAIGN') {
        totalReach = config.reach * quantity;
        projectedEnrollments = Math.round(totalReach * config.conversionRate);
        totalCost = config.cost * quantity;
    } else {
        totalReach = config.capacity * quantity;
        projectedEnrollments = Math.round(totalReach * config.successRate);
        totalCost = config.cost * quantity;
    }

    // Calculate welfare benefits unlocked
    const benefitsUnlocked = calculateWelfareBenefits(projectedEnrollments, targetGroup);

    // Calculate gender gap improvement (if applicable)
    let genderGapImprovement = null;
    if (district && targetGroup === 'WOMEN') {
        genderGapImprovement = calculateGenderGapImprovement(
            district.femaleEnrollment || 0,
            district.maleEnrollment || 0,
            projectedEnrollments
        );
    }

    // Calculate ROI
    const annualBenefitValue = benefitsUnlocked.totalAnnualValue;
    const roi = ((annualBenefitValue - totalCost) / totalCost * 100).toFixed(1);

    return {
        success: true,
        input: {
            intervention,
            quantity,
            days,
            targetGroup
        },
        projections: {
            totalReach,
            projectedEnrollments,
            successRate: (config.successRate * 100).toFixed(0) + '%',
            totalCost,
            costPerEnrollment: Math.round(totalCost / projectedEnrollments)
        },
        benefitsUnlocked,
        genderGapImprovement,
        roi: {
            value: roi + '%',
            breakEvenMonths: Math.ceil(totalCost / (annualBenefitValue / 12)),
            recommendation: parseFloat(roi) > 100 ? 'HIGHLY RECOMMENDED' : 
                           parseFloat(roi) > 50 ? 'RECOMMENDED' : 'CONSIDER ALTERNATIVES'
        }
    };
}

/**
 * Calculate welfare benefits for new enrollees
 */
function calculateWelfareBenefits(enrollments, targetGroup) {
    const benefits = [];
    let totalMonthly = 0;
    let totalAnnual = 0;

    // Different benefits based on target group
    if (targetGroup === 'WOMEN' || targetGroup === 'ALL') {
        benefits.push({
            name: 'LPG Subsidy (Ujjwala)',
            eligiblePercent: 70,
            beneficiaries: Math.round(enrollments * 0.7),
            monthlyValue: WELFARE_BENEFITS.LPG_SUBSIDY,
            annualValue: WELFARE_BENEFITS.LPG_SUBSIDY * 12 * Math.round(enrollments * 0.7)
        });
        benefits.push({
            name: 'Jan Dhan Bank Account',
            eligiblePercent: 90,
            beneficiaries: Math.round(enrollments * 0.9),
            oneTimeValue: WELFARE_BENEFITS.JAN_DHAN_ACCESS,
            annualValue: WELFARE_BENEFITS.JAN_DHAN_ACCESS * Math.round(enrollments * 0.9)
        });
    }

    if (targetGroup === 'ELDERLY' || targetGroup === 'ALL') {
        benefits.push({
            name: 'Old Age Pension',
            eligiblePercent: 80,
            beneficiaries: Math.round(enrollments * 0.8),
            monthlyValue: WELFARE_BENEFITS.PENSION,
            annualValue: WELFARE_BENEFITS.PENSION * 12 * Math.round(enrollments * 0.8)
        });
    }

    if (targetGroup === 'CHILDREN' || targetGroup === 'ALL') {
        benefits.push({
            name: 'Education Scholarship',
            eligiblePercent: 60,
            beneficiaries: Math.round(enrollments * 0.6),
            annualValue: WELFARE_BENEFITS.SCHOLARSHIP * Math.round(enrollments * 0.6)
        });
    }

    if (targetGroup === 'ALL' || targetGroup === 'WOMEN') {
        benefits.push({
            name: 'Ayushman Bharat Health Coverage',
            eligiblePercent: 85,
            beneficiaries: Math.round(enrollments * 0.85),
            coverageValue: WELFARE_BENEFITS.HEALTH_INSURANCE,
            annualValue: 0 // Coverage, not direct cash
        });
        benefits.push({
            name: 'Ration Card (PDS)',
            eligiblePercent: 75,
            beneficiaries: Math.round(enrollments * 0.75),
            monthlyValue: WELFARE_BENEFITS.RATION_SUBSIDY,
            annualValue: WELFARE_BENEFITS.RATION_SUBSIDY * 12 * Math.round(enrollments * 0.75)
        });
    }

    // Calculate totals
    benefits.forEach(b => {
        if (b.monthlyValue) totalMonthly += b.monthlyValue * b.beneficiaries;
        totalAnnual += b.annualValue || 0;
    });

    return {
        benefits,
        totalMonthlyValue: totalMonthly,
        totalAnnualValue: totalAnnual,
        totalAnnualFormatted: formatCurrency(totalAnnual)
    };
}

/**
 * Calculate gender gap improvement
 */
function calculateGenderGapImprovement(currentFemale, currentMale, newFemaleEnrollments) {
    const total = currentFemale + currentMale;
    if (total === 0) return null;

    const currentRatio = currentFemale / (currentFemale + currentMale);
    const newFemale = currentFemale + newFemaleEnrollments;
    const newRatio = newFemale / (newFemale + currentMale);
    const improvement = newRatio - currentRatio;

    return {
        currentFemaleRatio: (currentRatio * 100).toFixed(1) + '%',
        projectedFemaleRatio: (newRatio * 100).toFixed(1) + '%',
        improvement: (improvement * 100).toFixed(2) + '%',
        currentGap: ((0.5 - currentRatio) * 100).toFixed(1) + '%',
        projectedGap: ((0.5 - newRatio) * 100).toFixed(1) + '%',
        gapReduction: ((currentRatio - 0.5 + improvement) / (currentRatio - 0.5) * 100).toFixed(0) + '%'
    };
}

/**
 * Format currency in Indian format
 */
function formatCurrency(amount) {
    if (amount >= 10000000) {
        return '₹' + (amount / 10000000).toFixed(2) + ' Cr';
    } else if (amount >= 100000) {
        return '₹' + (amount / 100000).toFixed(2) + ' L';
    } else if (amount >= 1000) {
        return '₹' + (amount / 1000).toFixed(1) + ' K';
    }
    return '₹' + amount;
}

/**
 * Run multiple simulation scenarios
 */
export function compareScenarios(scenarios) {
    return scenarios.map((scenario, index) => ({
        scenario: index + 1,
        name: scenario.name || `Scenario ${index + 1}`,
        ...simulateIntervention(scenario)
    }));
}

/**
 * Get optimal intervention mix for a budget
 */
export function optimizeForBudget(budget, targetEnrollments, targetGroup = 'WOMEN') {
    const results = [];

    // Try different combinations
    const combinations = [
        { camps: Math.floor(budget / INTERVENTION_COSTS.CAMP.cost), vans: 0 },
        { camps: 0, vans: Math.floor(budget / (INTERVENTION_COSTS.MOBILE_VAN.cost * 5)) * 5 }, // 5-day van deployment
        { camps: Math.floor(budget * 0.6 / INTERVENTION_COSTS.CAMP.cost), 
          vans: Math.floor(budget * 0.4 / (INTERVENTION_COSTS.MOBILE_VAN.cost * 5)) * 5 }
    ];

    combinations.forEach((combo, i) => {
        let totalEnrollments = 0;
        let totalCost = 0;

        if (combo.camps > 0) {
            const campResult = simulateIntervention({ intervention: 'CAMP', quantity: combo.camps, targetGroup });
            totalEnrollments += campResult.projections.projectedEnrollments;
            totalCost += campResult.projections.totalCost;
        }

        if (combo.vans > 0) {
            const vanResult = simulateIntervention({ intervention: 'MOBILE_VAN', quantity: combo.vans / 5, days: 5, targetGroup });
            totalEnrollments += vanResult.projections.projectedEnrollments;
            totalCost += vanResult.projections.totalCost;
        }

        results.push({
            name: i === 0 ? 'Camps Only' : i === 1 ? 'Mobile Vans Only' : 'Mixed Strategy',
            camps: combo.camps,
            vanDays: combo.vans,
            totalCost,
            projectedEnrollments: totalEnrollments,
            meetsTarget: totalEnrollments >= targetEnrollments
        });
    });

    // Sort by enrollments
    results.sort((a, b) => b.projectedEnrollments - a.projectedEnrollments);

    return {
        budget,
        targetEnrollments,
        recommendations: results,
        bestOption: results[0]
    };
}

export default {
    simulateIntervention,
    compareScenarios,
    optimizeForBudget
};

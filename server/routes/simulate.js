/**
 * Impact Simulator API Routes
 * Endpoints for ROI calculation and intervention planning
 */

import express from 'express';
import { getEnrolmentData } from '../services/dataGovApi.js';
import { computeGenderCoverage } from '../services/genderAnalysis.js';
import {
    simulateIntervention,
    compareScenarios,
    optimizeForBudget
} from '../services/impactSimulator.js';

const router = express.Router();

/**
 * POST /api/simulate/intervention
 * Simulate impact of a single intervention
 */
router.post('/intervention', async (req, res) => {
    try {
        const { intervention, quantity, days, district, targetGroup } = req.body;
        
        if (!intervention || !quantity) {
            return res.status(400).json({
                success: false,
                error: 'Missing required fields: intervention, quantity'
            });
        }

        // If district name provided, fetch actual district data
        let districtData = null;
        if (district) {
            const enrolmentData = await getEnrolmentData({ limit: 500 });
            if (enrolmentData.success) {
                const coverage = computeGenderCoverage(enrolmentData.records);
                districtData = coverage.districtAnalysis.find(d => 
                    d.district?.toLowerCase().includes(district.toLowerCase())
                );
            }
        }

        const result = simulateIntervention({
            intervention,
            quantity: parseInt(quantity),
            days: parseInt(days) || 1,
            district: districtData,
            targetGroup: targetGroup || 'WOMEN'
        });
        
        res.json({
            success: true,
            data: result,
            metadata: {
                timestamp: new Date().toISOString()
            }
        });

    } catch (error) {
        console.error('Simulation error:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to run simulation',
            message: error.message
        });
    }
});

/**
 * POST /api/simulate/compare
 * Compare multiple intervention scenarios
 */
router.post('/compare', async (req, res) => {
    try {
        const { scenarios } = req.body;
        
        if (!scenarios || !Array.isArray(scenarios)) {
            return res.status(400).json({
                success: false,
                error: 'Missing or invalid scenarios array'
            });
        }

        const results = compareScenarios(scenarios);
        
        res.json({
            success: true,
            data: {
                scenarios: results,
                bestScenario: results.reduce((best, current) => 
                    parseFloat(current.roi?.value) > parseFloat(best.roi?.value) ? current : best
                , results[0])
            },
            metadata: {
                timestamp: new Date().toISOString()
            }
        });

    } catch (error) {
        console.error('Comparison error:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to compare scenarios',
            message: error.message
        });
    }
});

/**
 * POST /api/simulate/optimize
 * Find optimal intervention mix for a budget
 */
router.post('/optimize', async (req, res) => {
    try {
        const { budget, targetEnrollments, targetGroup } = req.body;
        
        if (!budget) {
            return res.status(400).json({
                success: false,
                error: 'Missing required field: budget'
            });
        }

        const result = optimizeForBudget(
            parseInt(budget),
            parseInt(targetEnrollments) || 1000,
            targetGroup || 'WOMEN'
        );
        
        res.json({
            success: true,
            data: result,
            metadata: {
                timestamp: new Date().toISOString()
            }
        });

    } catch (error) {
        console.error('Optimization error:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to optimize intervention',
            message: error.message
        });
    }
});

/**
 * GET /api/simulate/presets
 * Get preset simulation scenarios
 */
router.get('/presets', (req, res) => {
    const presets = [
        {
            name: 'Small District - Basic',
            intervention: 'CAMP',
            quantity: 5,
            targetGroup: 'WOMEN',
            description: '5 women-only camps for a small district'
        },
        {
            name: 'Medium District - Mixed',
            intervention: 'CAMP',
            quantity: 10,
            days: 5,
            targetGroup: 'ALL',
            description: '10 camps + 5 days of mobile van deployment'
        },
        {
            name: 'Large District - Intensive',
            intervention: 'CAMP',
            quantity: 20,
            days: 10,
            targetGroup: 'WOMEN',
            description: '20 camps + 10 days of mobile van deployment'
        },
        {
            name: 'Elderly Focus',
            intervention: 'DOORSTEP',
            quantity: 200,
            targetGroup: 'ELDERLY',
            description: '200 doorstep visits for elderly enrollment'
        },
        {
            name: 'Awareness Campaign',
            intervention: 'AWARENESS_CAMPAIGN',
            quantity: 3,
            targetGroup: 'ALL',
            description: '3 awareness campaigns before enrollment drives'
        }
    ];

    res.json({
        success: true,
        data: { presets }
    });
});

export default router;

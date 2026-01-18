/**
 * Vulnerable Groups API Routes
 * Endpoints for multi-vulnerable group analysis
 */

import express from 'express';
import { getEnrolmentData } from '../services/dataGovApi.js';
import {
    computeVulnerableGroupAnalysis,
    generateVulnerableGroupRecommendations
} from '../services/vulnerableGroups.js';

const router = express.Router();

/**
 * GET /api/vulnerable/analysis
 * Get inclusion analysis for all vulnerable groups
 */
router.get('/analysis', async (req, res) => {
    try {
        const limit = parseInt(req.query.limit) || 500;
        
        const enrolmentData = await getEnrolmentData({ limit });
        
        if (!enrolmentData.success) {
            return res.status(500).json({
                success: false,
                error: 'Failed to fetch enrollment data'
            });
        }

        const analysis = computeVulnerableGroupAnalysis(enrolmentData.records);
        
        res.json({
            success: true,
            data: analysis,
            metadata: {
                recordsAnalyzed: enrolmentData.records.length,
                timestamp: new Date().toISOString()
            }
        });

    } catch (error) {
        console.error('Vulnerable groups analysis error:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to analyze vulnerable groups',
            message: error.message
        });
    }
});

/**
 * GET /api/vulnerable/high-risk
 * Get high-risk districts for each vulnerable group
 */
router.get('/high-risk', async (req, res) => {
    try {
        const limit = parseInt(req.query.limit) || 500;
        const group = req.query.group || 'all'; // 'children', 'elderly', 'disabled', 'all'
        
        const enrolmentData = await getEnrolmentData({ limit });
        
        if (!enrolmentData.success) {
            return res.status(500).json({
                success: false,
                error: 'Failed to fetch enrollment data'
            });
        }

        const analysis = computeVulnerableGroupAnalysis(enrolmentData.records);
        
        let highRiskData;
        if (group === 'all') {
            highRiskData = analysis.highRiskByGroup;
        } else {
            highRiskData = { [group]: analysis.highRiskByGroup[group] || [] };
        }

        // Add recommendations
        const highRiskWithRecommendations = {};
        for (const [grp, districts] of Object.entries(highRiskData)) {
            highRiskWithRecommendations[grp] = districts.map(d => ({
                ...d,
                recommendations: generateVulnerableGroupRecommendations(d)
            }));
        }

        res.json({
            success: true,
            data: {
                group,
                highRiskDistricts: highRiskWithRecommendations,
                totalHighRisk: Object.values(highRiskData).reduce((sum, arr) => sum + arr.length, 0)
            },
            metadata: {
                timestamp: new Date().toISOString()
            }
        });

    } catch (error) {
        console.error('High-risk vulnerable groups error:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to identify high-risk districts',
            message: error.message
        });
    }
});

/**
 * GET /api/vulnerable/states
 * Get state-level vulnerable group analysis
 */
router.get('/states', async (req, res) => {
    try {
        const limit = parseInt(req.query.limit) || 500;
        
        const enrolmentData = await getEnrolmentData({ limit });
        
        if (!enrolmentData.success) {
            return res.status(500).json({
                success: false,
                error: 'Failed to fetch enrollment data'
            });
        }

        const analysis = computeVulnerableGroupAnalysis(enrolmentData.records);
        
        res.json({
            success: true,
            data: {
                summary: analysis.summary,
                states: analysis.stateAnalysis
            },
            metadata: {
                timestamp: new Date().toISOString()
            }
        });

    } catch (error) {
        console.error('State analysis error:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to get state analysis',
            message: error.message
        });
    }
});

export default router;

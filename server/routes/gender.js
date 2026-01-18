/**
 * Gender Inclusion Tracker API Routes
 * Endpoints for gender analysis, high-risk detection, and recommendations
 */

import express from 'express';
import { getEnrolmentData } from '../services/dataGovApi.js';
import {
    computeGenderCoverage,
    identifyHighRiskDistricts,
    generateRecommendations,
    generateAIRecommendations
} from '../services/genderAnalysis.js';

const router = express.Router();

/**
 * GET /api/gender/coverage
 * Get male vs female coverage ratios by state and district
 */
router.get('/coverage', async (req, res) => {
    try {
        const limit = parseInt(req.query.limit) || 500;
        
        // Fetch enrollment data
        const enrolmentData = await getEnrolmentData({ limit });
        
        if (!enrolmentData.success) {
            return res.status(500).json({
                success: false,
                error: 'Failed to fetch enrollment data',
                details: enrolmentData.error
            });
        }

        // Compute gender coverage
        const coverage = computeGenderCoverage(enrolmentData.records);
        
        res.json({
            success: true,
            data: coverage,
            metadata: {
                recordsAnalyzed: enrolmentData.records.length,
                timestamp: new Date().toISOString()
            }
        });

    } catch (error) {
        console.error('Gender coverage error:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to compute gender coverage',
            message: error.message
        });
    }
});

/**
 * GET /api/gender/high-risk
 * Get list of high-risk districts for female exclusion
 */
router.get('/high-risk', async (req, res) => {
    try {
        const limit = parseInt(req.query.limit) || 500;
        const threshold = parseFloat(req.query.threshold) || 0.46;
        
        // Fetch enrollment data
        const enrolmentData = await getEnrolmentData({ limit });
        
        if (!enrolmentData.success) {
            return res.status(500).json({
                success: false,
                error: 'Failed to fetch enrollment data'
            });
        }

        // Compute gender coverage
        const coverage = computeGenderCoverage(enrolmentData.records);
        
        if (!coverage.success) {
            return res.status(500).json({
                success: false,
                error: 'Failed to compute gender coverage'
            });
        }

        // Identify high-risk districts
        const highRiskDistricts = identifyHighRiskDistricts(
            coverage.districtAnalysis,
            threshold
        );

        // Add recommendations for each district
        const districtsWithRecommendations = highRiskDistricts.map(d => ({
            ...d,
            recommendations: generateRecommendations(d)
        }));

        res.json({
            success: true,
            data: {
                totalHighRisk: highRiskDistricts.length,
                threshold,
                riskDistribution: {
                    critical: highRiskDistricts.filter(d => d.riskLevel === 'CRITICAL').length,
                    high: highRiskDistricts.filter(d => d.riskLevel === 'HIGH').length,
                    moderate: highRiskDistricts.filter(d => d.riskLevel === 'MODERATE').length
                },
                districts: districtsWithRecommendations
            },
            metadata: {
                totalDistrictsAnalyzed: coverage.districtAnalysis.length,
                timestamp: new Date().toISOString()
            }
        });

    } catch (error) {
        console.error('High-risk detection error:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to identify high-risk districts',
            message: error.message
        });
    }
});

/**
 * GET /api/gender/recommendations
 * Get AI-powered intervention recommendations
 */
router.get('/recommendations', async (req, res) => {
    try {
        const limit = parseInt(req.query.limit) || 500;
        
        // Fetch enrollment data
        const enrolmentData = await getEnrolmentData({ limit });
        
        if (!enrolmentData.success) {
            return res.status(500).json({
                success: false,
                error: 'Failed to fetch enrollment data'
            });
        }

        // Compute gender coverage
        const coverage = computeGenderCoverage(enrolmentData.records);
        
        if (!coverage.success) {
            return res.status(500).json({
                success: false,
                error: 'Failed to compute gender coverage'
            });
        }

        // Identify high-risk districts
        const highRiskDistricts = identifyHighRiskDistricts(coverage.districtAnalysis);

        // Generate AI recommendations
        const aiRecommendations = await generateAIRecommendations(highRiskDistricts);

        res.json({
            success: true,
            data: {
                summary: coverage.summary,
                highRiskCount: highRiskDistricts.length,
                ...aiRecommendations
            },
            metadata: {
                timestamp: new Date().toISOString()
            }
        });

    } catch (error) {
        console.error('Recommendations error:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to generate recommendations',
            message: error.message
        });
    }
});

/**
 * POST /api/gender/analyze
 * Run full gender analysis with ML predictions
 */
router.post('/analyze', async (req, res) => {
    try {
        const { limit = 500, threshold = 0.46, includeAI = true } = req.body;
        
        console.log('🔍 Starting gender analysis...');
        
        // Fetch enrollment data
        const enrolmentData = await getEnrolmentData({ limit });
        
        if (!enrolmentData.success) {
            return res.status(500).json({
                success: false,
                error: 'Failed to fetch enrollment data'
            });
        }

        console.log(`📊 Analyzing ${enrolmentData.records.length} records...`);

        // Compute gender coverage
        const coverage = computeGenderCoverage(enrolmentData.records);
        
        if (!coverage.success) {
            return res.status(500).json({
                success: false,
                error: 'Failed to compute gender coverage'
            });
        }

        // Identify high-risk districts
        const highRiskDistricts = identifyHighRiskDistricts(
            coverage.districtAnalysis,
            threshold
        );

        console.log(`⚠️ Found ${highRiskDistricts.length} high-risk districts`);

        // Generate recommendations
        let recommendations = null;
        if (includeAI) {
            recommendations = await generateAIRecommendations(highRiskDistricts);
        }

        // Compile full analysis
        const analysis = {
            summary: {
                ...coverage.summary,
                highRiskDistricts: highRiskDistricts.length,
                riskDistribution: {
                    critical: highRiskDistricts.filter(d => d.riskLevel === 'CRITICAL').length,
                    high: highRiskDistricts.filter(d => d.riskLevel === 'HIGH').length,
                    moderate: highRiskDistricts.filter(d => d.riskLevel === 'MODERATE').length
                }
            },
            stateAnalysis: coverage.stateAnalysis,
            highRiskDistricts: highRiskDistricts.map(d => ({
                ...d,
                recommendations: generateRecommendations(d)
            })),
            aiRecommendations: recommendations
        };

        console.log('✅ Gender analysis complete');

        res.json({
            success: true,
            data: analysis,
            metadata: {
                recordsAnalyzed: enrolmentData.records.length,
                threshold,
                timestamp: new Date().toISOString()
            }
        });

    } catch (error) {
        console.error('Gender analysis error:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to run gender analysis',
            message: error.message
        });
    }
});

/**
 * GET /api/gender/district/:state/:district
 * Get detailed analysis for a specific district
 */
router.get('/district/:state/:district', async (req, res) => {
    try {
        const { state, district } = req.params;
        const limit = 500;
        
        // Fetch enrollment data
        const enrolmentData = await getEnrolmentData({ limit });
        
        if (!enrolmentData.success) {
            return res.status(500).json({
                success: false,
                error: 'Failed to fetch enrollment data'
            });
        }

        // Filter for specific district
        const districtRecords = enrolmentData.records.filter(r => 
            r.state?.toLowerCase().includes(state.toLowerCase()) &&
            r.district?.toLowerCase().includes(district.toLowerCase())
        );

        if (districtRecords.length === 0) {
            return res.status(404).json({
                success: false,
                error: 'District not found',
                searchedFor: { state, district }
            });
        }

        // Compute coverage for this district
        const coverage = computeGenderCoverage(districtRecords);
        
        const districtData = coverage.districtAnalysis[0] || null;
        
        if (!districtData) {
            return res.status(404).json({
                success: false,
                error: 'No data available for district'
            });
        }

        // Generate recommendations
        const recommendations = generateRecommendations(districtData);

        res.json({
            success: true,
            data: {
                ...districtData,
                riskScore: identifyHighRiskDistricts([districtData])[0]?.riskScore || 0,
                riskLevel: identifyHighRiskDistricts([districtData])[0]?.riskLevel || 'LOW',
                recommendations
            },
            metadata: {
                recordsAnalyzed: districtRecords.length,
                timestamp: new Date().toISOString()
            }
        });

    } catch (error) {
        console.error('District analysis error:', error);
        res.status(500).json({
            success: false,
            error: 'Failed to analyze district',
            message: error.message
        });
    }
});

export default router;

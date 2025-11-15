/**
 * Smart Diagnosis Module
 * Analyzes device health and provides AI-powered recommendations
 */

(function() {
    'use strict';

    /**
     * Compute Health Score (0-100) based on device metrics
     * @param {Object} data - Device data object
     * @returns {Object} - { score: number, status: string, recommendation: string }
     */
    function computeHealthScore(data) {
        let score = 0;
        const recommendations = [];

        // Battery Level: 40% weight (0-100% battery = 0-40 points)
        let batteryScore = 0;
        if (data.battery && data.battery.level !== undefined) {
            const batteryLevel = parseFloat(data.battery.level);
            if (!isNaN(batteryLevel)) {
                batteryScore = (batteryLevel / 100) * 40;
                score += batteryScore;

                // Add recommendation for low battery
                if (batteryLevel < 20) {
                    recommendations.push('Plug in your charger immediately.');
                } else if (batteryLevel < 40) {
                    recommendations.push('Consider plugging in your charger soon.');
                }
            }
        } else {
            // Default battery score if not available
            score += 20; // Assume 50% battery
        }

        // RAM Usage: 30% weight (lower usage = better)
        // deviceMemory is in GB, but we need usage percentage
        // For now, we'll estimate based on available RAM tiers
        let ramScore = 0;
        if (data.deviceMemory !== undefined && data.deviceMemory !== null) {
            const ramGB = parseFloat(data.deviceMemory);
            if (!isNaN(ramGB)) {
                // Higher RAM = better (more headroom)
                // Score based on RAM tier: 2GB=10pts, 4GB=20pts, 6GB=25pts, 8GB+=30pts
                if (ramGB >= 8) {
                    ramScore = 30;
                } else if (ramGB >= 6) {
                    ramScore = 25;
                } else if (ramGB >= 4) {
                    ramScore = 20;
                } else if (ramGB >= 2) {
                    ramScore = 15;
                } else {
                    ramScore = 10;
                }
                score += ramScore;

                // Add recommendation for low RAM
                if (ramGB < 4) {
                    recommendations.push('Close background apps to free up RAM.');
                }
            }
        } else {
            // Default RAM score if not available
            score += 15; // Assume moderate RAM
        }

        // Storage Usage: 20% weight (lower usage = better)
        let storageScore = 0;
        if (data.storage) {
            let usagePercent = 0;
            
            // Check for new sandbox format first
            if (data.storage.storageSandboxUsagePercent !== undefined) {
                usagePercent = parseFloat(data.storage.storageSandboxUsagePercent);
            } else if (data.storage.quota && data.storage.usage) {
                // Fallback to old format
                const quota = parseFloat(data.storage.quota);
                const usage = parseFloat(data.storage.usage);
                if (!isNaN(quota) && !isNaN(usage) && quota > 0) {
                    usagePercent = (usage / quota) * 100;
                }
            }

            if (!isNaN(usagePercent)) {
                // Lower usage = higher score
                // 0% usage = 20pts, 100% usage = 0pts
                storageScore = 20 * (1 - usagePercent / 100);
                score += storageScore;

                // Add recommendation for high storage usage
                if (usagePercent > 80) {
                    recommendations.push('Delete unused files to free up space.');
                } else if (usagePercent > 60) {
                    recommendations.push('Consider cleaning up storage space.');
                }
            } else {
                // Default storage score if not available
                score += 10; // Assume moderate usage
            }
        } else {
            // Default storage score if not available
            score += 10; // Assume moderate usage
        }

        // Charging State: 10% bonus if charging
        let chargingBonus = 0;
        if (data.battery && data.battery.charging === true) {
            chargingBonus = 10;
            score += chargingBonus;
        }

        // Clamp score to 0-100
        score = Math.max(0, Math.min(100, Math.round(score)));

        // Classify status
        let status = 'Unknown';
        let statusClass = 'unknown';
        if (score >= 80) {
            status = 'Excellent';
            statusClass = 'excellent';
        } else if (score >= 60) {
            status = 'Good';
            statusClass = 'good';
        } else if (score >= 40) {
            status = 'Moderate';
            statusClass = 'moderate';
        } else {
            status = 'Critical';
            statusClass = 'critical';
        }

        // Generate recommendation
        let recommendation = '';
        if (recommendations.length > 0) {
            recommendation = recommendations.join(' ');
        } else {
            recommendation = 'Your device is performing well.';
        }

        return {
            score: score,
            status: status,
            statusClass: statusClass,
            recommendation: recommendation,
            breakdown: {
                battery: Math.round(batteryScore),
                ram: Math.round(ramScore),
                storage: Math.round(storageScore),
                charging: chargingBonus
            }
        };
    }

    /**
     * Update the AI Health Diagnosis section in the UI
     * @param {Object} data - Device data object
     */
    function updateSmartDiagnosis(data) {
        const diagnosis = computeHealthScore(data);
        
        // Update score
        const scoreEl = document.getElementById('health-score-value');
        if (scoreEl) {
            scoreEl.textContent = `${diagnosis.score}%`;
        }

        // Update status badge
        const statusEl = document.getElementById('health-status-badge');
        if (statusEl) {
            statusEl.textContent = diagnosis.status;
            statusEl.className = `health-status-badge ${diagnosis.statusClass}`;
        }

        // Update recommendation
        const recEl = document.getElementById('health-recommendation');
        if (recEl) {
            recEl.textContent = diagnosis.recommendation;
        }

        // Update card border color
        const cardEl = document.getElementById('ai-health-card');
        if (cardEl) {
            cardEl.className = `result-card animate-slide-up ai-health-card ${diagnosis.statusClass}`;
        }

        console.log('[AI Diagnosis] Updated:', diagnosis);
    }

    // Export functions to global scope
    window.SmartDiagnosis = {
        computeHealthScore: computeHealthScore,
        updateSmartDiagnosis: updateSmartDiagnosis
    };
})();


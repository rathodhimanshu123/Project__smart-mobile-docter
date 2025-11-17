/**
 * Smart Diagnosis Module (rule-based, alias-aware, fallback friendly)
 */
(function() {
    'use strict';

    const DIAG_DEBUG = window.DIAGNOSIS_DEBUG !== undefined ? window.DIAGNOSIS_DEBUG : true;
    const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
    const ALIASES = {
        batteryDesign: [
            'battery.design_capacity',
            'battery_capacity_mah',
            'batteryCapacity',
            'battery.designCapacity',
            'battery.specs.capacity',
            'design_capacity',
            'battery.design',
            'battery.mAh',
            'battery.mah'
        ],
        batteryCurrent: [
            'battery.current_capacity',
            'batteryCapacityCurrent',
            'battery.currentCapacity',
            'battery.capacity.current',
            'battery_current_capacity',
            'battery.current',
            'battery.current_mAh',
            'currentCapacity',
            'deviceBattery.current'
        ],
        batteryPercent: [
            'battery.level',
            'batteryPercent',
            'battery.percent',
            'battery_percent',
            'battery_status.percent',
            'battery.chargePercent'
        ],
        batteryHealthPercent: [
            'battery.health',
            'battery.healthPercent',
            'batteryHealthPercent',
            'battery_health_percent',
            'health.battery',
            'battery_state.healthPercent'
        ],
        performanceScore: [
            'latestPerformanceScore',
            'performance_score',
            'performanceScore',
            'scores.performance',
            'diagnostics.performanceScore',
            'perfScore'
        ],
        responsiveness: [
            'responsivenessIndex',
            'responsiveness.index',
            'responsiveness',
            'metrics.responsiveness',
            'diagnostics.responsiveness'
        ],
        storageUsage: [
            'storageUsagePercent',
            'storage.usedPercent',
            'storage.percentUsed',
            'storageUsage',
            'storage.percent',
            'storage.storageSandboxUsagePercent'
        ],
        temperature: [
            'temperature',
            'deviceTemp',
            'battery.temperature',
            'thermal.temperature',
            'temps.device'
        ],
        ram: [
            'ram_gb',
            'ramGB',
            'deviceMemory',
            'memory.total',
            'hardware.ram'
        ],
        osVersion: [
            'merged_data.os.version',
            'deviceInfo.osVersion',
            'platform.version',
            'osVersion',
            'device.osVersion'
        ],
        drainRate: [
            'prediction.drain_per_min',
            'prediction.percentPerMinute',
            'battery.drainRate',
            'battery_drain_rate',
            'batteryDrainRate',
            'predictions.drainRate',
            'shortTermDrainPctPerMin',
            'drainRate'
        ]
    };

    function diagLog(message, data) {
        if (!DIAG_DEBUG) return;
        if (data !== undefined) {
            console.debug(`[AI_DIAG] ${message}`, data);
        } else {
            console.debug(`[AI_DIAG] ${message}`);
        }
    }

    function parseNumber(value) {
        if (value === null || value === undefined) return null;
        if (typeof value === 'number' && !Number.isNaN(value)) return value;
        const match = String(value).replace(/,/g, '').match(/-?\d+(\.\d+)?/);
        return match ? parseFloat(match[0]) : null;
    }

    function resolvePath(obj, path) {
        if (!obj || !path) return undefined;
        if (!path.includes('.')) return obj[path];
        return path.split('.').reduce((acc, key) => {
            if (acc === undefined || acc === null) return undefined;
            return acc[key];
        }, obj);
    }

    function gatherValueFromAliases(sources, aliases, { numeric = true } = {}) {
        for (const alias of aliases) {
            for (const source of sources) {
                const raw = resolvePath(source.data, alias);
                if (raw === undefined || raw === null) continue;
                const value = numeric ? parseNumber(raw) : raw;
                if (numeric && value === null) continue;
                return { value, alias, source: source.label, raw };
            }
        }
        return null;
    }

    function buildSources(data) {
        const sources = [];
        if (data) {
            sources.push({ label: 'input', data });
            if (data.snapshot) sources.push({ label: 'input.snapshot', data: data.snapshot });
            if (data.live) sources.push({ label: 'input.live', data: data.live });
            if (data.prediction) sources.push({ label: 'input.prediction', data: data.prediction });
            if (data.phoneInfo) sources.push({ label: 'input.phoneInfo', data: data.phoneInfo });
        }
        if (window.templateDataPayload) {
            sources.push({ label: 'templatePayload', data: window.templateDataPayload });
            if (window.templateDataPayload.phoneInfo) {
                sources.push({ label: 'templatePhoneInfo', data: window.templateDataPayload.phoneInfo });
            }
        }
        if (window.verifiedScoreBreakdown) {
            sources.push({ label: 'verifiedScore', data: window.verifiedScoreBreakdown });
        }
        if (window.mergedDeviceData) {
            sources.push({ label: 'mergedDeviceData', data: window.mergedDeviceData });
        }
        return sources;
    }

    function estimateFactoryCapacity(designValue, ramGb) {
        if (designValue) {
            return { value: designValue, estimated: false, note: 'Provided design capacity' };
        }
        if (ramGb !== null) {
            if (ramGb > 6) return { value: 4000, estimated: true, note: `Estimated from ${ramGb}GB RAM profile` };
            if (ramGb >= 4) return { value: 3500, estimated: true, note: `Estimated from ${ramGb}GB RAM profile` };
            return { value: 3000, estimated: true, note: `Estimated from ${ramGb}GB RAM profile` };
        }
        return { value: 4200, estimated: true, note: 'Default modern smartphone baseline' };
    }

    function deriveCurrentCapacity(original, currentValue, healthPercent, levelPercent) {
        if (currentValue) {
            return { value: currentValue, estimated: false, note: 'Provided current capacity' };
        }
        if (!original) return { value: null, estimated: true, note: 'No baseline available' };
        if (healthPercent !== null) {
            const pct = clamp(healthPercent / 100, 0.35, 1);
            return { value: original * pct, estimated: true, note: 'Estimated from battery health' };
        }
        if (levelPercent !== null) {
            const factor = clamp(0.65 + (levelPercent / 100) * 0.25, 0.4, 1);
            return { value: original * factor, estimated: true, note: 'Estimated from battery level' };
        }
        return { value: original * 0.82, estimated: true, note: 'Conservative wear assumption' };
    }

    function derivePerformanceScore(perfEntry, respEntry, storageUsage) {
        if (perfEntry && perfEntry.value !== null) {
            return {
                value: clamp(perfEntry.value, 0, 100),
                estimated: false,
                note: `Direct score (${perfEntry.alias})`
            };
        }
        const responsiveness = respEntry ? clamp(respEntry.value, 0, 100) : null;
        const storageComponent = storageUsage !== null ? clamp(100 - storageUsage, 0, 100) : null;
        if (responsiveness === null && storageComponent === null) return null;
        const respScore = responsiveness !== null ? responsiveness : 72;
        const storageScore = storageComponent !== null ? storageComponent : 78;
        return {
            value: clamp(Math.round(respScore * 0.6 + storageScore * 0.4), 30, 95),
            estimated: true,
            note: `Estimated from ${responsiveness !== null ? 'responsiveness' : ''}${responsiveness !== null && storageComponent !== null ? ' & ' : ''}${storageComponent !== null ? 'storage usage' : ''}`
        };
    }

    function runDiagnosticEngine(data) {
        const sources = buildSources(data || {});
        const aliasUsage = {};
        const fallbacks = [];
        const estimatedFields = new Set();
        const issues = [];
        const recommendations = [];
        const rulesTriggered = [];

        diagLog('Sources inspected', sources.map(src => src.label));

        const ramEntry = gatherValueFromAliases(sources, ALIASES.ram);
        if (ramEntry) aliasUsage.ram = ramEntry;

        const designEntry = gatherValueFromAliases(sources, ALIASES.batteryDesign);
        if (designEntry) aliasUsage.batteryDesign = designEntry;

        const currentEntry = gatherValueFromAliases(sources, ALIASES.batteryCurrent);
        if (currentEntry) aliasUsage.batteryCurrent = currentEntry;

        const percentEntry = gatherValueFromAliases(sources, ALIASES.batteryPercent);
        if (percentEntry) aliasUsage.batteryPercent = percentEntry;

        const healthEntry = gatherValueFromAliases(sources, ALIASES.batteryHealthPercent);
        if (healthEntry) aliasUsage.batteryHealthPercent = healthEntry;

        const performanceEntry = gatherValueFromAliases(sources, ALIASES.performanceScore);
        if (performanceEntry) aliasUsage.performanceScore = performanceEntry;

        const responsivenessEntry = gatherValueFromAliases(sources, ALIASES.responsiveness);
        if (responsivenessEntry) aliasUsage.responsiveness = responsivenessEntry;

        const storageEntry = gatherValueFromAliases(sources, ALIASES.storageUsage);
        if (storageEntry) aliasUsage.storageUsage = storageEntry;

        const temperatureEntry = gatherValueFromAliases(sources, ALIASES.temperature);
        if (temperatureEntry) aliasUsage.temperature = temperatureEntry;

        const drainEntry = gatherValueFromAliases(sources, ALIASES.drainRate);
        if (drainEntry) aliasUsage.drainRate = drainEntry;

        const osEntry = gatherValueFromAliases(sources, ALIASES.osVersion, { numeric: false });
        if (osEntry) aliasUsage.osVersion = osEntry;

        const factory = estimateFactoryCapacity(designEntry ? designEntry.value : null, ramEntry ? ramEntry.value : null);
        if (factory.estimated) {
            fallbacks.push(factory.note);
            estimatedFields.add('Factory capacity');
        }

        const currentCapacity = deriveCurrentCapacity(
            factory.value,
            currentEntry ? currentEntry.value : null,
            healthEntry ? healthEntry.value : null,
            percentEntry ? percentEntry.value : null
        );
        if (currentCapacity.estimated) {
            fallbacks.push(currentCapacity.note);
            estimatedFields.add('Current capacity');
        }

        const performance = derivePerformanceScore(performanceEntry, responsivenessEntry, storageEntry ? storageEntry.value : null);
        if (!performance) {
            fallbacks.push('Performance score defaulted to 75');
            estimatedFields.add('Performance score');
        }
        const performanceScore = performance ? performance.value : 75;
        const performanceEstimated = performance ? performance.estimated : true;
        if (performanceEstimated) {
            estimatedFields.add('Performance score');
        }

        const storageUsage = storageEntry ? clamp(storageEntry.value, 0, 100) : null;
        const temperature = temperatureEntry ? temperatureEntry.value : null;
        const drainRate = drainEntry ? Math.abs(drainEntry.value) : null;

        const degradation = factory.value && currentCapacity.value
            ? clamp((factory.value - currentCapacity.value) / factory.value, 0, 0.95)
            : null;
        const healthPercent = healthEntry ? clamp(healthEntry.value, 0, 100) : null;

        const signalsPresent = [
            degradation !== null,
            performanceScore !== null,
            storageUsage !== null,
            temperature !== null,
            drainRate !== null
        ].filter(Boolean).length;

        const estimationUsed = estimatedFields.size > 0;

        diagLog('Alias resolution', aliasUsage);
        diagLog('Fallbacks applied', fallbacks);

        if (degradation !== null && (degradation > 0.20 || (healthPercent !== null && healthPercent < 80))) {
            issues.push({
                id: 'battery-aging',
                message: 'Battery aging detected',
                detail: `Estimated wear ${(degradation * 100).toFixed(1)}%${healthPercent !== null ? `, health ${healthPercent}%` : ''}`,
                severity: 'high'
            });
            recommendations.push('Plan for a battery calibration or replacement to regain capacity.');
            rulesTriggered.push('battery-aging');
        }

        if (performanceScore < 50 || (responsivenessEntry && responsivenessEntry.value !== null && responsivenessEntry.value < 55)) {
            issues.push({
                id: 'performance-slowdown',
                message: 'Performance slowdown detected',
                detail: `Performance score ${Math.round(performanceScore)}%`,
                severity: 'medium'
            });
            recommendations.push('Close background apps and restart the device to clear system resources.');
            rulesTriggered.push('performance');
        }

        if (storageUsage !== null && storageUsage > 85) {
            issues.push({
                id: 'storage-pressure',
                message: 'High storage usage',
                detail: `${Math.round(storageUsage)}% of storage used`,
                severity: 'medium'
            });
            recommendations.push('Delete unused media or move files to the cloud to free up space.');
            rulesTriggered.push('storage');
        }

        if (temperature !== null && temperature > 42) {
            issues.push({
                id: 'thermal-stress',
                message: 'Thermal stress risk',
                detail: `${temperature.toFixed(1)}°C recorded`,
                severity: 'high'
            });
            recommendations.push('Let the device cool and avoid intense workloads in hot environments.');
            rulesTriggered.push('thermal');
        }

        if (drainRate !== null && drainRate > 0.8) {
            issues.push({
                id: 'rapid-drain',
                message: 'Rapid drain detected',
                detail: `${drainRate.toFixed(2)}% per minute`,
                severity: 'medium'
            });
            recommendations.push('Check for background apps or accessories causing irregular drain.');
            rulesTriggered.push('rapid-drain');
        }

        if (issues.length === 0 && signalsPresent > 0) {
            issues.push({
                id: 'all-clear',
                message: 'No critical issues detected',
                detail: 'Available metrics look healthy',
                severity: 'low'
            });
            recommendations.push('Keep software updated and maintain good charging practices.');
        }

        if (recommendations.length === 0 && signalsPresent > 0) {
            recommendations.push('Monitor the device periodically to ensure sustained performance.');
        }

        const unavailable = signalsPresent === 0;
        if (unavailable) {
            issues.push({
                id: 'data-missing',
                message: 'Not enough data to diagnose',
                detail: 'Waiting for device metrics',
                severity: 'high'
            });
            recommendations.push('Allow the collector to gather more samples for a full diagnosis.');
        }

        let score = unavailable ? 20 : 90;
        issues.forEach(issue => {
            if (issue.id === 'battery-aging') score -= 20;
            if (issue.id === 'performance-slowdown') score -= 25;
            if (issue.id === 'storage-pressure') score -= 15;
            if (issue.id === 'thermal-stress') score -= 30;
            if (issue.id === 'rapid-drain') score -= 15;
        });
        score = clamp(score, unavailable ? 0 : 45, 99);

        const partialMode = (signalsPresent <= 1 && !unavailable) || estimationUsed;

        let statusLabel = 'Excellent';
        let statusClass = 'excellent';
        if (score >= 80) {
            statusLabel = 'Excellent';
            statusClass = 'excellent';
        } else if (score >= 60) {
            statusLabel = 'Good';
            statusClass = 'good';
        } else if (score >= 45) {
            statusLabel = 'Moderate';
            statusClass = 'moderate';
        } else {
            statusLabel = 'Needs Attention';
            statusClass = 'critical';
        }

        if (partialMode && !unavailable) {
            statusLabel = 'Partial Diagnosis';
            statusClass = 'moderate';
        } else if (unavailable) {
            statusLabel = 'Diagnosis unavailable';
            statusClass = 'unknown';
        }

        const summary = {
            score,
            status: statusLabel,
            statusClass,
            issues,
            recommendations,
            fallbacks,
            aliasUsage,
            estimationUsed,
            estimatedFieldsList: Array.from(estimatedFields),
            partial: partialMode,
            unavailable,
            rulesTriggered,
            signals: {
                battery: {
                    design: factory.value,
                    current: currentCapacity.value,
                    degradation,
                    healthPercent
                },
                performance: performanceScore,
                storageUsage,
                temperature,
                drainRate
            },
            verification: {
                detectedIssues: issues.map(issue => issue.message),
                appliedFallbacks: fallbacks,
                aliasKeysUsed: Object.fromEntries(Object.entries(aliasUsage).map(([k, v]) => [k, { alias: v.alias, source: v.source }])),
                firstIssue: issues.length ? issues[0].message : null,
                firstRecommendation: recommendations[0] || null,
                discoveredAliases: Object.keys(aliasUsage),
                recommendations
            }
        };

        diagLog('Rules triggered', summary.rulesTriggered);
        diagLog('Verification summary', summary.verification);

        window.__latestDiagnosisSummary = summary;
        return summary;
    }

    function updateSmartDiagnosis(data) {
        const cardEl = document.getElementById('ai-health-card');
        const summary = runDiagnosticEngine(data || {});
        
        const scoreEl = document.getElementById('health-score-value');
        if (scoreEl) scoreEl.textContent = `${summary.score}%`;

        const statusEl = document.getElementById('health-status-badge');
        if (statusEl) {
            if (summary.estimationUsed) {
                statusEl.innerHTML = `${summary.status}<span style="margin-left: 8px; padding: 0.2rem 0.6rem; font-size: 0.65rem; border-radius: 999px; border: 1px solid rgba(255,255,255,0.4); text-transform: uppercase;">DATA ESTIMATED</span>`;
            } else {
                statusEl.textContent = summary.status;
            }
            statusEl.className = `health-status-badge ${summary.statusClass}`;
        }

        const recEl = document.getElementById('health-recommendation');
        if (recEl) {
            recEl.textContent = summary.recommendations.join(' ');
            let breakdownLine = document.getElementById('diagnosis-estimation-note');
            if ((summary.estimationUsed || summary.partial) && summary.estimatedFieldsList.length > 0) {
                if (!breakdownLine) {
                    breakdownLine = document.createElement('div');
                    breakdownLine.id = 'diagnosis-estimation-note';
                    breakdownLine.style.marginTop = '0.75rem';
                    breakdownLine.style.fontSize = '0.75rem';
                    breakdownLine.style.opacity = '0.8';
                    breakdownLine.style.padding = '0.4rem 0.6rem';
                    breakdownLine.style.borderRadius = '6px';
                    breakdownLine.style.background = 'rgba(255,255,255,0.08)';
                    breakdownLine.style.border = '1px dashed rgba(255,255,255,0.15)';
                    recEl.parentNode.appendChild(breakdownLine);
                }
                breakdownLine.textContent = `DATA ESTIMATED: ${summary.estimatedFieldsList.join(', ')}`;
            } else if (breakdownLine) {
                breakdownLine.remove();
            }
        }

        if (cardEl) {
            cardEl.className = `result-card animate-slide-up ai-health-card ${summary.statusClass}`;
        }

        return summary;
    }

    window.SmartDiagnosis = {
        runDiagnostics: runDiagnosticEngine,
        updateSmartDiagnosis
    };
    window.__testAIDiagnosis = runDiagnosticEngine;
})();


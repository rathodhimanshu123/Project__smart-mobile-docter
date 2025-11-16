/**
 * 3-Hour Minute-Resolution Prediction Client
 * Handles prediction data fetching, chart rendering, and SSE updates
 */

(function() {
    'use strict';

    // Check if Chart.js is available
    if (typeof Chart === 'undefined') {
        console.warn('[PREDICTION] Chart.js not loaded. Loading from CDN...');
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
        script.onload = function() {
            console.log('[PREDICTION] Chart.js loaded');
            initializePrediction();
        };
        document.head.appendChild(script);
    } else {
        initializePrediction();
    }

    function initializePrediction() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', setupPrediction);
        } else {
            setupPrediction();
        }
    }

    let predictionCharts = {};
    let currentPrediction = null;
    let demoMode = false;

    // Helper function to clamp values
    const clamp = (v, min, max) => Math.max(min, Math.min(max, v));

    function setupPrediction() {
        const sessionId = getSessionId();
        if (!sessionId) {
            console.warn('[PREDICTION] No session ID found');
            return;
        }

        // Load initial prediction
        loadPrediction(sessionId);

        // Subscribe to SSE prediction updates
        subscribeToPredictionUpdates(sessionId);

        // Setup demo mode toggle
        setupDemoModeToggle();
    }

    function getSessionId() {
        // Try multiple ways to get session ID
        const urlParams = new URLSearchParams(window.location.search);
        let sid = urlParams.get('sid') || urlParams.get('session_id');
        
        if (!sid) {
            // Try from page data
            const sessionEl = document.querySelector('[data-session-id]');
            if (sessionEl) {
                sid = sessionEl.getAttribute('data-session-id');
            }
        }

        // Try from window variable (set by result.html)
        if (!sid && window.sessionId) {
            sid = window.sessionId;
        }

        return sid;
    }

    async function loadPrediction(sessionId) {
        try {
            const response = await fetch(`/api/prediction/${sessionId}`);
            const data = await response.json();
            
            if (data.success && data.prediction) {
                currentPrediction = data.prediction;
                renderPrediction(currentPrediction);
            } else {
                showInsufficientData(data.prediction || {});
            }
        } catch (error) {
            console.error('[PREDICTION] Error loading prediction:', error);
            showError('Failed to load prediction data');
        }
    }

    function subscribeToPredictionUpdates(sessionId) {
        // Check if EventSource is available
        if (typeof EventSource === 'undefined') {
            console.warn('[PREDICTION] EventSource not supported');
            return;
        }

        // Get existing eventSource from result.html if available
        let eventSource = window.eventSource;
        
        // If no existing SSE connection, create one
        if (!eventSource || eventSource.readyState === EventSource.CLOSED) {
            const streamUrl = `/api/stream/${sessionId}`;
            eventSource = new EventSource(streamUrl);
            window.eventSource = eventSource;
        }

        // Listen for prediction events and battery updates
        eventSource.addEventListener('message', function(event) {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'prediction' && data.data) {
                    console.log('[PREDICTION] SSE prediction update received');
                    currentPrediction = data.data;
                    renderPrediction(currentPrediction);
                } else if (data.type === 'battery' && data.data) {
                    // Battery update - reload prediction to recompute
                    console.log('[PREDICTION] SSE battery update received, reloading prediction');
                    const sessionId = getSessionId();
                    if (sessionId) {
                        loadPrediction(sessionId);
                    }
                }
            } catch (error) {
                console.error('[PREDICTION] Error parsing SSE message:', error);
            }
        });
    }

    function renderPrediction(prediction) {
        if (!prediction) {
            showInsufficientData({});
            return;
        }

        // Handle charging paused state
        if (prediction.status === 'charging_paused' || prediction.chargingPaused) {
            showChargingPaused(prediction);
            return;
        }

        // Handle insufficient data
        if (prediction.status === 'insufficient_data' || prediction.status !== 'success') {
            showInsufficientData(prediction);
            return;
        }

        // Update health score (support multiple formats)
        const healthScore = prediction.health_score_3_hour || prediction.health_score_24_hour || prediction.health_score_30_day;
        updateHealthScore(healthScore);

        // Update UI states
        updateUIStates(prediction);

        // Render charts
        renderCharts(prediction, demoMode);

        // Update projected times (use drain_per_min if available)
        const drainPerMin = prediction.drain_per_min !== undefined ? prediction.drain_per_min : (prediction.percentPerMinute ? Math.abs(prediction.percentPerMinute) : undefined);
        updateProjectedTimes(prediction.predictedTimeTo, drainPerMin, prediction.minutesPerPercent);

        // Show prediction card
        const card = document.getElementById('prediction-card');
        if (card) {
            card.style.display = 'block';
        }

        // Hide other states
        const insufficientMsg = document.getElementById('prediction-insufficient');
        if (insufficientMsg) {
            insufficientMsg.style.display = 'none';
        }
        const chargingMsg = document.getElementById('prediction-charging');
        if (chargingMsg) {
            chargingMsg.style.display = 'none';
        }
    }

    function updateHealthScore(score) {
        const scoreEl = document.getElementById('prediction-health-score');
        if (scoreEl) {
            scoreEl.textContent = score !== undefined ? `${Math.round(score)}%` : '--';
            
            // Update color based on score
            scoreEl.className = 'prediction-score';
            if (score >= 70) {
                scoreEl.classList.add('score-good');
            } else if (score >= 50) {
                scoreEl.classList.add('score-fair');
            } else {
                scoreEl.classList.add('score-poor');
            }
        }
    }

    function updateRiskBadges(riskScores) {
        if (!riskScores) return;

        const thermalEl = document.getElementById('prediction-thermal-risk');
        if (thermalEl && riskScores.thermal_stress !== undefined) {
            thermalEl.textContent = `${Math.round(riskScores.thermal_stress)}%`;
            thermalEl.className = 'risk-badge';
            if (riskScores.thermal_stress > 50) {
                thermalEl.classList.add('risk-high');
            } else if (riskScores.thermal_stress > 30) {
                thermalEl.classList.add('risk-medium');
            } else {
                thermalEl.classList.add('risk-low');
            }
        }
    }

    function updateRecommendations(recommendations) {
        const recEl = document.getElementById('prediction-recommendations');
        if (recEl && recommendations) {
            recEl.innerHTML = '';
            recommendations.forEach(rec => {
                const li = document.createElement('li');
                li.textContent = rec;
                recEl.appendChild(li);
            });
        }
    }

    function updateKeyDates(keyDates) {
        const datesEl = document.getElementById('prediction-key-dates');
        if (datesEl && keyDates) {
            datesEl.innerHTML = '';
            const dateLabels = {
                'battery_20': 'Battery drops to 20%',
                'battery_50': 'Battery drops to 50%',
                'battery_80': 'Battery drops to 80%',
                'storage_80': 'Storage reaches 80%',
                'storage_95': 'Storage reaches 95%'
            };

            // Use 12-hour format helper if available
            const formatTime = (window.TimeUtils && window.TimeUtils.formatTime12h) 
                ? window.TimeUtils.formatTime12h 
                : function(ts) {
                    const d = ts instanceof Date ? ts : new Date(ts);
                    return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
                };

            Object.entries(keyDates).forEach(([key, dateStr]) => {
                try {
                    const date = new Date(dateStr);
                    if (isNaN(date.getTime())) {
                        throw new Error('Invalid date');
                    }
                    
                    const now = new Date();
                    const hoursUntil = Math.round((date - now) / (1000 * 60 * 60));
                    const timeStr = formatTime(date);
                    
                    const li = document.createElement('li');
                    if (hoursUntil > 0 && hoursUntil <= 24) {
                        li.innerHTML = `<strong>${dateLabels[key] || key}:</strong> In ~${hoursUntil} hour${hoursUntil !== 1 ? 's' : ''} (${timeStr})`;
                    } else {
                        li.innerHTML = `<strong>${dateLabels[key] || key}:</strong> ${timeStr}`;
                    }
                    datesEl.appendChild(li);
                } catch (e) {
                    console.warn('[PREDICTION] Invalid date:', dateStr);
                    // Show raw ISO with tooltip explaining time unavailable
                    const li = document.createElement('li');
                    li.innerHTML = `<strong>${dateLabels[key] || key}:</strong> <span title="Time unavailable">${dateStr}</span>`;
                    datesEl.appendChild(li);
                }
            });
        }
    }

    function renderCharts(prediction, demoMode) {
        if (!prediction || !prediction.batteryPrediction) return;

        // Generate 181 minute labels (0-180 minutes)
        const minutes = Array.from({length: 181}, (_, i) => i);
        
        // Get battery prediction data
        let batteryData = prediction.batteryPrediction || [];

        if (demoMode) {
            // Accelerate timeline for demo (60× speed: 180 minutes = 3 minutes)
            // Compress 181 points to show faster change
            const accelerationFactor = 60;
            batteryData = batteryData.map((val, i) => {
                if (i === 0) return val;
                const trend = val - batteryData[0];
                return batteryData[0] + (trend * accelerationFactor);
            });
        }

        // Ensure data array is exactly 181 points
        const ensureLength181 = (arr) => {
            if (arr.length > 181) {
                return arr.slice(0, 181);
            } else if (arr.length < 181) {
                const lastVal = arr.length > 0 ? arr[arr.length - 1] : 50;
                return [...arr, ...Array(181 - arr.length).fill(lastVal)];
            }
            return arr;
        };

        // Clamp all values to 0-100
        batteryData = ensureLength181(batteryData).map(v => clamp(v, 0, 100));

        // Ensure labels match data length
        const chartLabels = minutes.slice(0, 181);

        // Battery chart (minute resolution)
        renderChart('batteryChart', chartLabels, batteryData, 'Battery Level (%)', '#10b981', demoMode);
    }

    function renderChart(canvasId, labels, data, label, color, demoMode = false) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.warn(`[PREDICTION] Canvas not found: ${canvasId}`);
            return;
        }

        // Ensure labels and data have matching lengths (181 minutes)
        const maxPoints = 181;
        const finalLabels = labels.slice(0, maxPoints);
        const finalData = data.slice(0, maxPoints).map(v => clamp(v, 0, 100));
        
        // Pad if needed
        while (finalLabels.length < maxPoints) {
            finalLabels.push(finalLabels.length);
        }
        while (finalData.length < maxPoints) {
            const lastVal = finalData.length > 0 ? finalData[finalData.length - 1] : 50;
            finalData.push(clamp(lastVal, 0, 100));
        }

        const ctx = canvas.getContext('2d');

        // Update existing chart if it exists (with smooth animation)
        if (predictionCharts[canvasId]) {
            // Store old data for comparison
            const oldData = predictionCharts[canvasId].data.datasets[0].data;
            const hasSignificantChange = oldData.length > 0 && finalData.length > 0 && 
                Math.abs(oldData[0] - finalData[0]) > 0.1; // More than 0.1% change
            
            // Update data
            predictionCharts[canvasId].data.labels = finalLabels;
            predictionCharts[canvasId].data.datasets[0].data = finalData;
            predictionCharts[canvasId].data.datasets[0].label = label;
            
            // Use smooth animation if there's a significant change
            const animationMode = hasSignificantChange ? 'active' : 'none';
            predictionCharts[canvasId].update(animationMode);
            predictionCharts[canvasId].resize();
            return;
        }

        // Create new chart
        predictionCharts[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: finalLabels,
                datasets: [{
                    label: label,
                    data: finalData,
                    borderColor: color,
                    backgroundColor: color + '20',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 2,
                    pointHoverRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 750,  // Smooth animation duration
                    easing: 'easeOutQuart'
                },
                layout: {
                    padding: 8
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                const minute = context.dataIndex;
                                const value = clamp(context.parsed.y, 0, 100).toFixed(1);
                                return `${context.dataset.label}: ${value}%`;
                            },
                            title: function(context) {
                                const minute = context[0].dataIndex;
                                const now = new Date();
                                const projectedTime = new Date(now.getTime() + minute * 60 * 1000);
                                // Use 12-hour format helper if available, otherwise fallback
                                const timeStr = (window.TimeUtils && window.TimeUtils.formatTime12h) 
                                    ? window.TimeUtils.formatTime12h(projectedTime)
                                    : projectedTime.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
                                return `${minute} min (${timeStr})`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        min: 0,
                        max: 100,
                        ticks: {
                            stepSize: 10,
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Minutes from now'
                        },
                        ticks: {
                            stepSize: 30,
                            maxTicksLimit: 7,
                            callback: function(value) {
                                if (value % 60 === 0) {
                                    return (value / 60) + 'h';
                                }
                                return value + 'm';
                            }
                        }
                    }
                }
            }
        });
    }

    function showInsufficientData(prediction) {
        const card = document.getElementById('prediction-card');
        const insufficientMsg = document.getElementById('prediction-insufficient');
        const chargingMsg = document.getElementById('prediction-charging');
        
        if (card) {
            card.style.display = 'none';
        }
        if (chargingMsg) {
            chargingMsg.style.display = 'none';
        }
        
        if (insufficientMsg) {
            insufficientMsg.style.display = 'block';
            const msgText = insufficientMsg.querySelector('.insufficient-message');
            if (msgText) {
                const sampleCount = prediction.samplesCount || prediction.sampleCount || 0;
                msgText.textContent = prediction.message || `Insufficient data — collecting samples. Current: ${sampleCount} sample(s). Need at least 2 non-charging samples.`;
            }
        }
    }

    function showChargingPaused(prediction) {
        const card = document.getElementById('prediction-card');
        const insufficientMsg = document.getElementById('prediction-insufficient');
        const chargingMsg = document.getElementById('prediction-charging');
        
        if (card) {
            card.style.display = 'none';
        }
        if (insufficientMsg) {
            insufficientMsg.style.display = 'none';
        }
        
        if (chargingMsg) {
            chargingMsg.style.display = 'block';
            const msgText = chargingMsg.querySelector('.charging-message');
            if (msgText) {
                const battery = prediction.currentBattery || '--';
                msgText.textContent = prediction.message || `Predictions paused while device is charging. Current battery: ${battery}%`;
            }
        }
    }

    function updateUIStates(prediction) {
        // Show fallback banner if fallback is used
        const fallbackEl = document.getElementById('prediction-fallback-indicator');
        if (fallbackEl) {
            const usedFallback = prediction.usedFallback || prediction.fallback;
            if (usedFallback) {
                fallbackEl.style.display = 'block';
                fallbackEl.innerHTML = '⚠️ <strong>Not enough raw battery change detected</strong> — using short-term estimate based on device responsiveness.';
            } else {
                fallbackEl.style.display = 'none';
            }
        }

        // Show sample count with tooltip for low counts
        const sampleCountEl = document.getElementById('prediction-sample-count');
        if (sampleCountEl) {
            const count = prediction.samplesCount || prediction.sampleCount || 0;
            const validCount = prediction.validSampleCount || 0;
            sampleCountEl.textContent = `Samples: ${count} total, ${validCount} valid (non-charging)`;
            
            // Add tooltip if samplesCount < 3
            if (count < 3) {
                sampleCountEl.title = 'Collecting samples — predictions will improve after more battery updates (3+ samples).';
                sampleCountEl.style.cursor = 'help';
                sampleCountEl.style.textDecoration = 'underline';
                sampleCountEl.style.textDecorationStyle = 'dotted';
            } else {
                sampleCountEl.title = '';
                sampleCountEl.style.cursor = 'default';
                sampleCountEl.style.textDecoration = 'none';
            }
        }
    }

    function updateProjectedTimes(predictedTimeTo, drainPerMin, minutesPerPercent) {
        const timesEl = document.getElementById('prediction-projected-times');
        if (!timesEl) return;

        timesEl.innerHTML = '';
        
        // Add drain rate info (use drain_per_min if available)
        if (drainPerMin !== undefined && drainPerMin > 0) {
            const rateEl = document.createElement('li');
            rateEl.innerHTML = `<strong>Drain Rate:</strong> ${drainPerMin.toFixed(4)}% per minute`;
            timesEl.appendChild(rateEl);
        }
        
        // Add time per 1%
        if (minutesPerPercent !== undefined && minutesPerPercent !== null) {
            const timePerEl = document.createElement('li');
            timePerEl.innerHTML = `<strong>Time per 1%:</strong> ~${minutesPerPercent.toFixed(1)} minutes`;
            timesEl.appendChild(timePerEl);
        } else if (drainPerMin !== undefined && drainPerMin > 0) {
            // Calculate time per 1% if not provided
            const timePerEl = document.createElement('li');
            const timePer1Pct = 1.0 / drainPerMin;
            timePerEl.innerHTML = `<strong>Time per 1%:</strong> ~${timePer1Pct.toFixed(1)} minutes`;
            timesEl.appendChild(timePerEl);
        }

        // Add projected times (using 12-hour format)
        if (predictedTimeTo) {
            const formatTime = (window.TimeUtils && window.TimeUtils.formatTime12h) 
                ? window.TimeUtils.formatTime12h 
                : function(ts) {
                    const d = ts instanceof Date ? ts : new Date(ts);
                    return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
                };
            
            if (predictedTimeTo['50'] !== null && predictedTimeTo['50'] !== undefined) {
                const li = document.createElement('li');
                const minutes = Math.round(predictedTimeTo['50']);
                const now = new Date();
                const projectedTime = new Date(now.getTime() + minutes * 60 * 1000);
                const timeStr = formatTime(projectedTime);
                li.innerHTML = `<strong>Battery drops to 50%:</strong> In ~${minutes} min (${timeStr})`;
                timesEl.appendChild(li);
            }
            
            if (predictedTimeTo['20'] !== null && predictedTimeTo['20'] !== undefined) {
                const li = document.createElement('li');
                const minutes = Math.round(predictedTimeTo['20']);
                const now = new Date();
                const projectedTime = new Date(now.getTime() + minutes * 60 * 1000);
                const timeStr = formatTime(projectedTime);
                li.innerHTML = `<strong>Battery drops to 20%:</strong> In ~${minutes} min (${timeStr})`;
                timesEl.appendChild(li);
            }
            
            if (predictedTimeTo['10'] !== null && predictedTimeTo['10'] !== undefined) {
                const li = document.createElement('li');
                const minutes = Math.round(predictedTimeTo['10']);
                const now = new Date();
                const projectedTime = new Date(now.getTime() + minutes * 60 * 1000);
                const timeStr = formatTime(projectedTime);
                li.innerHTML = `<strong>Battery drops to 10%:</strong> In ~${minutes} min (${timeStr})`;
                timesEl.appendChild(li);
            }
        }
    }

    function showError(message) {
        const errorEl = document.getElementById('prediction-error');
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.style.display = 'block';
        }
    }

    function setupDemoModeToggle() {
        const toggle = document.getElementById('prediction-demo-toggle');
        if (toggle) {
            toggle.addEventListener('change', function() {
                demoMode = this.checked;
                if (currentPrediction && currentPrediction.status === 'success') {
                    renderCharts(currentPrediction.time_series, demoMode);
                }
            });
        }
    }

    // Export for global access
    window.PredictionModule = {
        loadPrediction: loadPrediction,
        renderPrediction: renderPrediction,
        demoMode: function() { return demoMode; }
    };

})();


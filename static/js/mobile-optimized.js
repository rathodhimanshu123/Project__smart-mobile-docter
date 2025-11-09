document.addEventListener('DOMContentLoaded', function() {
    console.log('Mobile.js loaded - starting device information collection');
    
    const status = document.getElementById('status-message');
    const phoneData = document.getElementById('phone-data');
    const dataList = document.getElementById('data-list');
    const sessionId = document.body.dataset.sessionId;
    const baseUrl = document.body.dataset.baseUrl || '';
    const loadingSpinner = document.getElementById('loading-spinner');
    const errorDisplay = document.getElementById('error-display');
    const manualRedirect = document.getElementById('manual-redirect');

    // Function to display errors
    function displayError(message) {
        console.error('Error:', message);
        if (status) status.style.display = 'none';
        if (errorDisplay) {
            errorDisplay.textContent = `Error: ${message}`;
            errorDisplay.style.display = 'block';
        }
        if (loadingSpinner) loadingSpinner.style.display = 'none';
    }

    // Function to add data item with optimized DOM updates
    function addDataItem(label, value) {
        const div = document.createElement('div');
        div.className = 'data-item';
        div.innerHTML = `<strong>${label}:</strong><span class="value">${value}</span>`;
        dataList.appendChild(div);
    }

    // Optimized function to get basic device information
    function getBasicDeviceInfo() {
        const ua = navigator.userAgent;
        const deviceInfo = {
            model: 'Unknown',
            manufacturer: 'Unknown',
            androidVersion: 'Not Android',
            userAgent: ua.substring(0, 100)
        };

        // Quick lookup maps for device identification
        const deviceMaps = {
            Samsung: { manufacturer: 'Samsung', model: 'Samsung Device' },
            iPhone: { manufacturer: 'Apple', model: 'iPhone' },
            OnePlus: { manufacturer: 'OnePlus', model: 'OnePlus Device' },
            Pixel: { manufacturer: 'Google', model: 'Google Pixel' },
            Xiaomi: { manufacturer: 'Xiaomi', model: 'Xiaomi Device' },
            Huawei: { manufacturer: 'Huawei', model: 'Huawei Device' },
            K: { manufacturer: 'Android', model: 'Android Device' }
        };

        // Find matching device
        for (const [key, value] of Object.entries(deviceMaps)) {
            if (ua.includes(key)) {
                deviceInfo.manufacturer = value.manufacturer;
                deviceInfo.model = value.model;
                break;
            }
        }

        // Extract Android version
        const androidMatch = ua.match(/Android\s([0-9]+(\.[0-9]+)?)/);
        if (androidMatch) {
            deviceInfo.androidVersion = androidMatch[1];
        }

        return deviceInfo;
    }

    // Optimized function to get all device information
    async function collectAllDeviceInfo() {
        const deviceInfo = getBasicDeviceInfo();
        const collector = new MobileDeviceCollector();
        
        try {
            const collectedInfo = await collector.initialize();
            return {
                ...deviceInfo,
                ...collectedInfo,
                sessionId,
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            console.error('Error collecting device info:', error);
            return deviceInfo;
        }
    }

    // Optimized function to send data
    function sendData(data) {
        return new Promise((resolve, reject) => {
            // Use relative path for API calls
            const apiUrl = '/api/submit_phone_data';
            
            fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                if (result.log_file) {
                    const downloadBtn = document.createElement('a');
                    downloadBtn.href = `/download_log/${result.log_file}`;
                    downloadBtn.className = 'download-btn';
                    downloadBtn.innerHTML = '📥 Download Device Analysis Log';
                    downloadBtn.setAttribute('download', ''); // Force download attribute
                    
                    // Add click handler for mobile devices
                    downloadBtn.addEventListener('click', async (e) => {
                        e.preventDefault();
                        try {
                            const response = await fetch(downloadBtn.href);
                            const blob = await response.blob();
                            const url = window.URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.style.display = 'none';
                            a.href = url;
                            a.download = `device_analysis_${new Date().toISOString().replace(/[:.]/g, '')}.log`;
                            document.body.appendChild(a);
                            a.click();
                            window.URL.revokeObjectURL(url);
                            document.body.removeChild(a);
                        } catch (error) {
                            console.error('Download failed:', error);
                            alert('Download failed. Please try again.');
                        }
                    });
                    
                    phoneData.appendChild(downloadBtn);
                }
                resolve(result);
            })
            .catch(error => {
                console.error('Error sending data:', error);
                reject(error);
            });
        });
    }

    // Main execution function
    async function main() {
        try {
            // Start collecting device info immediately
            const deviceInfo = await collectAllDeviceInfo();
            
            // Add additional system info
            deviceInfo.systemInfo = {
                platform: navigator.platform,
                language: navigator.language,
                cookiesEnabled: navigator.cookieEnabled,
                screenResolution: `${window.screen.width}x${window.screen.height}`,
                windowSize: `${window.innerWidth}x${window.innerHeight}`,
                pixelRatio: window.devicePixelRatio || 1,
                timestamp: new Date().toISOString()
            };

            // Update UI with collected info
            Object.entries(deviceInfo).forEach(([key, value]) => {
                if (typeof value === 'object') {
                    Object.entries(value).forEach(([subKey, subValue]) => {
                        addDataItem(`${key} - ${subKey}`, subValue);
                    });
                } else {
                    addDataItem(key, value);
                }
            });

            // Send data to server
            const result = await sendData(deviceInfo);
            
            // Update status
            if (status) {
                status.textContent = 'Device information collected successfully';
                status.className = 'status-message status-success';
            }
            if (loadingSpinner) {
                loadingSpinner.style.display = 'none';
            }

            return result;
        } catch (error) {
            displayError(error.message);
            throw error;
        }
    }

    // Start the process
    main().catch(error => {
        console.error('Main execution failed:', error);
        displayError('Failed to collect device information');
    });
});

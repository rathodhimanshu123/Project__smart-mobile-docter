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

    console.log('Session ID:', sessionId, 'Base URL:', baseUrl);

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

    // Function to add data item
    function addDataItem(label, value) {
        try {
            const div = document.createElement('div');
            div.className = 'data-item';
            
            const labelElement = document.createElement('strong');
            labelElement.textContent = `${label}:`;
            
            const valueElement = document.createElement('span');
            valueElement.className = 'value';
            valueElement.textContent = value;
            
            div.appendChild(labelElement);
            div.appendChild(valueElement);
            
            dataList.appendChild(div);
            console.log(`Added data item: ${label} = ${value}`);
        } catch (e) {
            console.warn('Error adding data item:', e);
        }
    }

    // Function to get basic device information
    function getBasicDeviceInfo() {
        try {
            const ua = navigator.userAgent;
            console.log('User Agent:', ua);
            
            // Extract Android version
            const androidMatch = ua.match(/Android\s([0-9]+(\.[0-9]+)?)/);
            const androidVersion = androidMatch ? androidMatch[1] : 'Not Android';
            
            // Extract device model (simplified)
            let model = 'Unknown';
            if (ua.includes('Samsung')) model = 'Samsung Device';
            else if (ua.includes('iPhone')) model = 'iPhone';
            else if (ua.includes('OnePlus')) model = 'OnePlus Device';
            else if (ua.includes('Pixel')) model = 'Google Pixel';
            else if (ua.includes('Xiaomi')) model = 'Xiaomi Device';
            else if (ua.includes('Huawei')) model = 'Huawei Device';
            else if (ua.includes('K')) model = 'Android Device';
            
            // Manufacturer
            let manufacturer = 'Unknown';
            if (ua.includes('Samsung')) manufacturer = 'Samsung';
            else if (ua.includes('iPhone') || ua.includes('iPad')) manufacturer = 'Apple';
            else if (ua.includes('OnePlus')) manufacturer = 'OnePlus';
            else if (ua.includes('Pixel')) manufacturer = 'Google';
            else if (ua.includes('Xiaomi')) manufacturer = 'Xiaomi';
            else if (ua.includes('Huawei')) manufacturer = 'Huawei';
            else if (ua.includes('K')) manufacturer = 'Android';
            
            return {
                model: model,
                manufacturer: manufacturer,
                androidVersion: androidVersion,
                userAgent: ua.substring(0, 100) + '...'
            };
        } catch (e) {
            console.warn('Error getting basic device info:', e);
            return {
                model: 'Unknown',
                manufacturer: 'Unknown',
                androidVersion: 'Unknown',
                userAgent: 'Unknown'
            };
        }
    }

    // Function to get battery information (simplified)
    function getBatteryInfo() {
        try {
            if (navigator.getBattery) {
                // Use a simple promise-based approach
                return new Promise((resolve) => {
                    navigator.getBattery().then(battery => {
                        resolve({
                            level: `${Math.round(battery.level * 100)}%`,
                            charging: battery.charging ? 'Charging' : 'Not charging'
                        });
                    }).catch(() => {
                        resolve({ level: 'Not available', charging: 'Unknown' });
                    });
                });
            }
        } catch (e) {
            console.warn('Battery API error:', e);
        }
        return Promise.resolve({ level: 'Not available', charging: 'Unknown' });
    }

    // Function to get screen information
    function getScreenInfo() {
        try {
            return {
                resolution: `${window.screen.width}x${window.screen.height}`,
                colorDepth: `${window.screen.colorDepth} bit`,
                pixelRatio: window.devicePixelRatio || 'Not available'
            };
        } catch (e) {
            console.warn('Error getting screen info:', e);
            return {
                resolution: 'Unknown',
                colorDepth: 'Unknown',
                pixelRatio: 'Not available'
            };
        }
    }

    // Function to get network information
    function getNetworkInfo() {
        try {
            const info = { type: 'Unknown', speed: 'Unknown' };
            if (navigator.connection) {
                info.type = navigator.connection.effectiveType || 'Unknown';
                info.speed = navigator.connection.downlink ? `${navigator.connection.downlink} Mbps` : 'Unknown';
            }
            return info;
        } catch (e) {
            console.warn('Error getting network info:', e);
            return { type: 'Unknown', speed: 'Unknown' };
        }
    }

    // Function to send data with optimization
    function sendData(data) {
        return new Promise((resolve, reject) => {
            const serverIp = document.body.dataset.serverIp || '127.0.0.1';
            const apiUrl = `http://${serverIp}:8080/api/submit_phone_data`;
            
            // Use fetch API instead of XMLHttpRequest for better performance
            fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(data),
                signal: AbortSignal.timeout(5000) // 5 second timeout
            
            xhr.onload = function() {
                if (xhr.status === 200) {
                    try {
                        const result = JSON.parse(xhr.responseText);
                        if (result.log_file) {
                            const downloadBtn = document.createElement('a');
                            downloadBtn.href = `/download_log/${result.log_file}`;
                            downloadBtn.className = 'download-btn';
                            downloadBtn.innerHTML = '📥 Download Device Analysis Log';
                            const phoneData = document.getElementById('phone-data');
                            if (phoneData) {
                                phoneData.appendChild(downloadBtn);
                            }
                        }
                        resolve(result);
                    } catch (e) {
                        resolve({ success: true });
                    }
                } else {
                    reject(new Error(`Server returned ${xhr.status}: ${xhr.responseText}`));
                }
            };
            
            xhr.onerror = function() {
                reject(new Error('Network error occurred'));
            };
            
            xhr.ontimeout = function() {
                reject(new Error('Request timed out'));
            };
            
            try {
                xhr.send(JSON.stringify(data));
            } catch (e) {
                reject(new Error('Failed to send data: ' + e.message));
            }
        });
    }

    // Main execution function
    async function main() {
        try {
            // Update status
            if (status) status.textContent = 'Collecting device information...';
            if (loadingSpinner) loadingSpinner.style.display = 'inline-block';

            // Collect basic information
            console.log('Collecting basic device info...');
            const deviceInfo = getBasicDeviceInfo();
            
            console.log('Collecting battery info...');
            const batteryInfo = await getBatteryInfo();
            
            console.log('Collecting screen info...');
            const screenInfo = getScreenInfo();
            
            console.log('Collecting network info...');
            const networkInfo = getNetworkInfo();
            
            // Build data object
            const comprehensiveData = {
                model: deviceInfo.model,
                manufacturer: deviceInfo.manufacturer,
                androidVersion: deviceInfo.androidVersion,
                batteryLevel: batteryInfo.level,
                batteryStatus: batteryInfo.charging,
                screenResolution: screenInfo.resolution,
                screenColorDepth: screenInfo.colorDepth,
                screenPixelRatio: screenInfo.pixelRatio,
                networkType: networkInfo.type,
                networkSpeed: networkInfo.speed,
                cpuCores: navigator.hardwareConcurrency || 'Not available',
                ram: navigator.deviceMemory ? `${navigator.deviceMemory} GB` : 'Not available',
                language: navigator.language || 'Unknown',
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                platform: navigator.platform || 'Unknown',
                onLine: navigator.onLine ? 'Yes' : 'No',
                collectedAt: new Date().toISOString()
            };

            console.log('Data collected:', comprehensiveData);

            // Display collected information
            if (status) {
                status.textContent = 'Device information collected successfully!';
                status.classList.add('status-success');
            }
            if (loadingSpinner) loadingSpinner.style.display = 'none';

            // Add information to the page
            addDataItem('📱 Device Model', comprehensiveData.model);
            addDataItem('🏭 Manufacturer', comprehensiveData.manufacturer);
            addDataItem('🤖 Android Version', comprehensiveData.androidVersion);
            addDataItem('🔋 Battery Level', comprehensiveData.batteryLevel);
            addDataItem('🔌 Charging Status', comprehensiveData.batteryStatus);
            addDataItem('📱 Screen Resolution', comprehensiveData.screenResolution);
            addDataItem('🎨 Color Depth', comprehensiveData.screenColorDepth);
            addDataItem('📐 Pixel Ratio', comprehensiveData.screenPixelRatio);
            addDataItem('⚡ CPU Cores', comprehensiveData.cpuCores);
            addDataItem('💾 RAM', comprehensiveData.ram);
            addDataItem('📶 Network Type', comprehensiveData.networkType);
            addDataItem('🚀 Network Speed', comprehensiveData.networkSpeed);
            addDataItem('🌍 Language', comprehensiveData.language);
            addDataItem('🕐 Timezone', comprehensiveData.timezone);
            addDataItem('📡 Online Status', comprehensiveData.onLine);

            // Add success note
            const noteDiv = document.createElement('div');
            noteDiv.className = 'data-item';
            noteDiv.style.backgroundColor = '#d4edda';
            noteDiv.style.borderLeft = '4px solid #28a745';
            noteDiv.style.padding = '15px';
            
            const noteLabel = document.createElement('strong');
            noteLabel.textContent = '✅ Success:';
            
            const noteValue = document.createElement('span');
            noteValue.className = 'value';
            noteValue.textContent = 'Device information collected successfully! Data will be sent to the server and you\'ll be redirected to the results page.';
            
            noteDiv.appendChild(noteLabel);
            noteDiv.appendChild(noteValue);
            dataList.appendChild(noteDiv);

            // Send data to server
            console.log('Sending data to server...');
            if (status) status.textContent = 'Sending data to server...';
            if (loadingSpinner) loadingSpinner.style.display = 'inline-block';

            await sendData({
                session_id: sessionId,
                phone_data: comprehensiveData
            });

            console.log('Data sent successfully');
            if (status) {
                status.textContent = 'Data sent successfully! Redirecting to results...';
                status.classList.add('status-success');
            }
            if (loadingSpinner) loadingSpinner.style.display = 'none';
            
            // Redirect to results page
            setTimeout(() => {
                console.log('Redirecting to results page...');
                // Get the server IP from the data attribute
                const serverIp = document.body.dataset.serverIp || '127.0.0.1';
                console.log('Using server IP for redirect:', serverIp);
                
                // Construct the redirect URL using the server IP with the correct format
                const redirectUrl = `http://${serverIp}:8080/result/${encodeURIComponent(sessionId)}`;
                console.log('Redirect URL:', redirectUrl);
                
                window.location.href = redirectUrl;
            }, 2000);

        } catch (error) {
            console.error('Error:', error);
            displayError(`Failed to collect or send device information: ${error.message}`);
            
            // Show manual redirect option
            if (manualRedirect) {
                manualRedirect.style.display = 'block';
            }
            
            // Add error note
            const errorNote = document.createElement('div');
            errorNote.className = 'data-item';
            errorNote.style.backgroundColor = '#f8d7da';
            errorNote.style.borderLeft = '4px solid #dc3545';
            errorNote.innerHTML = `
                <strong>⚠️ Note:</strong> Some data was collected but there was an issue sending it to the server. 
                You can still view the results by clicking the button below.
            `;
            dataList.appendChild(errorNote);
        }
    }

    // S
    main();
});

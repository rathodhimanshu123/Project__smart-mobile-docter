// Device Information Collector Service
class DeviceInfoCollector {
    constructor() {
        this.deviceInfo = {};
    }

    async collectAllInfo() {
        try {
            // Force collection of Android-specific information
            const androidInfo = await this.getAndroidInfo();
            
            this.deviceInfo = {
                // Android-specific Information
                ...androidInfo,
                
                // Basic Device Information
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                language: navigator.language,
                deviceMemory: await this.getDeviceMemory(),
                cpuCores: navigator.hardwareConcurrency ? `${navigator.hardwareConcurrency} cores` : 'Unknown',
                screenResolution: `${window.screen.width}x${window.screen.height}`,
                pixelRatio: window.devicePixelRatio,
                colorDepth: `${window.screen.colorDepth}-bit`,
                
                // Network Information
                networkType: this.getNetworkInfo(),
                onlineStatus: navigator.onLine ? 'Online' : 'Offline',
                
                // Battery Information
                battery: await this.getBatteryInfo(),
                
                // Storage Information
                storage: await this.getStorageInfo(),
                
                // Performance Information
                performance: this.getPerformanceInfo(),
                
                // Additional System Information
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                timestamp: new Date().toISOString(),
                
                // Mobile-Specific Information
                mobileInfo: this.getMobileSpecificInfo()
            };

            return this.deviceInfo;
        } catch (error) {
            console.error('Error collecting device information:', error);
            return {
                error: 'Failed to collect complete device information',
                partialInfo: this.deviceInfo
            };
        }
    }

    async getBatteryInfo() {
        if ('getBattery' in navigator) {
            try {
                const battery = await navigator.getBattery();
                return {
                    level: `${Math.round(battery.level * 100)}%`,
                    charging: battery.charging ? 'Yes' : 'No',
                    chargingTime: battery.charging ? `${Math.round(battery.chargingTime / 60)} minutes` : 'N/A',
                    dischargingTime: !battery.charging ? `${Math.round(battery.dischargingTime / 60)} minutes` : 'N/A'
                };
            } catch (e) {
                return 'Battery information unavailable';
            }
        }
        return 'Battery API not supported';
    }

    async getStorageInfo() {
        if ('storage' in navigator && 'estimate' in navigator.storage) {
            try {
                const estimate = await navigator.storage.estimate();
                return {
                    quotaBytes: this.formatBytes(estimate.quota),
                    usageBytes: this.formatBytes(estimate.usage),
                    percentageUsed: `${Math.round((estimate.usage / estimate.quota) * 100)}%`
                };
            } catch (e) {
                return 'Storage information unavailable';
            }
        }
        return 'Storage API not supported';
    }

    getNetworkInfo() {
        if ('connection' in navigator) {
            const conn = navigator.connection;
            return {
                type: conn.effectiveType || 'Unknown',
                downlinkSpeed: conn.downlink ? `${conn.downlink} Mbps` : 'Unknown',
                rtt: conn.rtt ? `${conn.rtt} ms` : 'Unknown',
                saveData: conn.saveData ? 'Yes' : 'No'
            };
        }
        return 'Network information unavailable';
    }

    getPerformanceInfo() {
        if ('memory' in performance) {
            return {
                jsHeapSizeLimit: this.formatBytes(performance.memory.jsHeapSizeLimit),
                totalJSHeapSize: this.formatBytes(performance.memory.totalJSHeapSize),
                usedJSHeapSize: this.formatBytes(performance.memory.usedJSHeapSize)
            };
        }
        return 'Performance information unavailable';
    }

    getMobileSpecificInfo() {
        const info = {};
        
        // Detect mobile device type
        info.type = /iPad/.test(navigator.userAgent) ? 'iPad' : 
                   /iPhone/.test(navigator.userAgent) ? 'iPhone' : 
                   /Android/.test(navigator.userAgent) ? 'Android' : 
                   'Other';
                   
        // Check for touch support
        info.touchPoints = navigator.maxTouchPoints || 0;
        
        // Check orientation capabilities
        info.orientationSupport = typeof window.orientation !== 'undefined';
        
        // Check vibration support
        info.vibrationSupport = 'vibrate' in navigator;
        
        return info;
    }

    formatBytes(bytes) {
        if (!bytes) return 'Unknown';
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        if (bytes === 0) return '0 Byte';
        const i = parseInt(Math.floor(Math.log(bytes) / Math.log(1024)));
        return Math.round(bytes / Math.pow(1024, i)) + ' ' + sizes[i];
    }

    async getDeviceMemory() {
        try {
            if ('memory' in navigator) {
                return `${navigator.deviceMemory} GB`;
            }
            
            // Alternative method for Android
            const performanceMemory = performance.memory;
            if (performanceMemory) {
                const totalMemory = this.formatBytes(performanceMemory.jsHeapSizeLimit);
                const usedMemory = this.formatBytes(performanceMemory.usedJSHeapSize);
                return `${usedMemory} / ${totalMemory}`;
            }
            
            return 'Not available';
        } catch (e) {
            return 'Not available';
        }
    }

    async getAndroidInfo() {
        const androidInfo = {
            Ram: 'Not available',
            OsVersion: 'Not Android',
            Battery: 'Not available%',
            Model: 'Android Device',
            Manufacturer: 'Android',
            AndroidVersion: 'Not Android'
        };

        try {
            // Get Battery Information
            if ('getBattery' in navigator || 'battery' in navigator) {
                const battery = await (navigator.getBattery?.() || navigator.battery);
                if (battery) {
                    androidInfo.Battery = `${Math.round(battery.level * 100)}%`;
                }
            }

            // Get Device Model and Manufacturer
            const userAgent = navigator.userAgent.toLowerCase();
            if (userAgent.includes('android')) {
                androidInfo.OsVersion = 'Android';
                androidInfo.AndroidVersion = 'Android';
                
                // Extract model information
                const modelMatch = userAgent.match(/\(linux;.*?;\s*(.*?)\s*build\//i);
                if (modelMatch && modelMatch[1]) {
                    const modelInfo = modelMatch[1].split(';').map(s => s.trim());
                    if (modelInfo.length >= 2) {
                        androidInfo.Manufacturer = modelInfo[0];
                        androidInfo.Model = modelInfo[1];
                    }
                }
            }

            // Get RAM Information
            if ('deviceMemory' in navigator) {
                androidInfo.Ram = `${navigator.deviceMemory} GB`;
            } else if ('memory' in performance) {
                const memory = performance.memory;
                androidInfo.Ram = this.formatBytes(memory.jsHeapSizeLimit);
            }

            // Additional Android Version Detection
            if (userAgent.includes('android')) {
                const versionMatch = userAgent.match(/android\s([0-9\.]*)/i);
                if (versionMatch && versionMatch[1]) {
                    androidInfo.AndroidVersion = `Android ${versionMatch[1]}`;
                }
            }

        } catch (e) {
            console.error('Error collecting Android info:', e);
        }

        return androidInfo;
    }
}

// Initialize the service
const deviceCollector = new DeviceInfoCollector();

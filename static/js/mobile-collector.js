// Mobile Device Information Collector
class MobileDeviceCollector {
    constructor() {
        this.info = {};
    }

    async initialize() {
        try {
            // Collect basic info first since it's fast and synchronous
            this.collectBasicInfo();
            
            // Collect all other information in parallel
            await Promise.all([
                this.collectBatteryInfo(),
                this.collectMemoryInfo(),
                this.collectStorageInfo(),
                this.collectNetworkInfo()
            ]);
            
            return this.info;
        } catch (error) {
            console.error('Error collecting device info:', error);
            // Return partial data instead of null
            return this.info;
        }
    }

    async collectBasicInfo() {
        const ua = navigator.userAgent.toLowerCase();
        const isAndroid = ua.includes('android');
        
        this.info.deviceInfo = {
            model: 'Unknown',
            manufacturer: 'Unknown',
            platform: navigator.platform,
            osVersion: 'Unknown'
        };

        if (isAndroid) {
            const match = ua.match(/\(linux;.*?;\s*(.*?)\s*build\//i);
            if (match && match[1]) {
                const parts = match[1].split(';').map(p => p.trim());
                if (parts.length >= 2) {
                    this.info.deviceInfo.manufacturer = parts[0];
                    this.info.deviceInfo.model = parts[1];
                }
            }

            const versionMatch = ua.match(/android\s([0-9\.]*)/i);
            if (versionMatch) {
                this.info.deviceInfo.osVersion = `Android ${versionMatch[1]}`;
            }
        }
    }

    async collectBatteryInfo() {
        try {
            const battery = await (navigator.getBattery?.() || navigator.battery);
            if (battery) {
                this.info.batteryInfo = {
                    level: `${Math.round(battery.level * 100)}%`,
                    charging: battery.charging ? 'Yes' : 'No',
                    chargingTime: battery.charging ? `${Math.round(battery.chargingTime / 60)} minutes` : 'N/A',
                    dischargingTime: !battery.charging ? `${Math.round(battery.dischargingTime / 60)} minutes` : 'N/A'
                };
            } else {
                this.info.batteryInfo = { status: 'Battery information not available' };
            }
        } catch (e) {
            this.info.batteryInfo = { status: 'Battery information not available' };
        }
    }

    async collectMemoryInfo() {
        this.info.memoryInfo = {
            deviceMemory: navigator.deviceMemory ? `${navigator.deviceMemory} GB` : 'Unknown',
            totalJSHeapSize: 'Unknown',
            usedJSHeapSize: 'Unknown'
        };

        if ('memory' in performance) {
            const memory = performance.memory;
            this.info.memoryInfo.totalJSHeapSize = this.formatBytes(memory.jsHeapSizeLimit);
            this.info.memoryInfo.usedJSHeapSize = this.formatBytes(memory.usedJSHeapSize);
        }
    }

    async collectStorageInfo() {
        try {
            if ('storage' in navigator && 'estimate' in navigator.storage) {
                const estimate = await navigator.storage.estimate();
                this.info.storageInfo = {
                    quota: this.formatBytes(estimate.quota),
                    usage: this.formatBytes(estimate.usage),
                    percentUsed: `${Math.round((estimate.usage / estimate.quota) * 100)}%`
                };
            } else {
                this.info.storageInfo = { status: 'Storage information not available' };
            }
        } catch (e) {
            this.info.storageInfo = { status: 'Storage information not available' };
        }
    }

    async collectNetworkInfo() {
        this.info.networkInfo = {
            online: navigator.onLine ? 'Yes' : 'No',
            type: 'Unknown',
            speed: 'Unknown'
        };

        if ('connection' in navigator) {
            const conn = navigator.connection;
            this.info.networkInfo.type = conn.effectiveType || 'Unknown';
            this.info.networkInfo.speed = conn.downlink ? `${conn.downlink} Mbps` : 'Unknown';
        }
    }

    formatBytes(bytes) {
        if (!bytes) return 'Unknown';
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        if (bytes === 0) return '0 Byte';
        const i = parseInt(Math.floor(Math.log(bytes) / Math.log(1024)));
        return Math.round(bytes / Math.pow(1024, i)) + ' ' + sizes[i];
    }
}

// Initialize collector when the script loads
const mobileCollector = new MobileDeviceCollector();

package com.example.smartmobiledoctor.models;

public class DeviceInfo {
    private String modelName;
    private String manufacturer;
    private float ramSizeGB;
    private float availableRamGB;
    private float storageSizeGB;
    private float availableStorageGB;
    private String androidVersion;
    private int processorCores;
    private int batteryLevel;
    private String batteryStatus; // Charging/Discharging
    private String batteryPlugged; // AC/USB/Wireless
    private String cpuModel;
    private Integer cpuMaxFreqMHz;
    private String networkType;
    private String carrierName;
    private String simState;
    private String imeiOrAndroidId;
    private String screenResolution;
    private float screenSizeInches;

    public DeviceInfo() {}

    // Getters and setters
    public String getModelName() { return modelName; }
    public void setModelName(String modelName) { this.modelName = modelName; }

    public String getManufacturer() { return manufacturer; }
    public void setManufacturer(String manufacturer) { this.manufacturer = manufacturer; }

    public float getRamSizeGB() { return ramSizeGB; }
    public void setRamSizeGB(float ramSizeGB) { this.ramSizeGB = ramSizeGB; }
    public float getAvailableRamGB() { return availableRamGB; }
    public void setAvailableRamGB(float availableRamGB) { this.availableRamGB = availableRamGB; }

    public float getStorageSizeGB() { return storageSizeGB; }
    public void setStorageSizeGB(float storageSizeGB) { this.storageSizeGB = storageSizeGB; }
    public float getAvailableStorageGB() { return availableStorageGB; }
    public void setAvailableStorageGB(float availableStorageGB) { this.availableStorageGB = availableStorageGB; }

    public String getAndroidVersion() { return androidVersion; }
    public void setAndroidVersion(String androidVersion) { this.androidVersion = androidVersion; }

    public int getProcessorCores() { return processorCores; }
    public void setProcessorCores(int processorCores) { this.processorCores = processorCores; }

    public int getBatteryLevel() { return batteryLevel; }
    public void setBatteryLevel(int batteryLevel) { this.batteryLevel = batteryLevel; }

    public String getBatteryStatus() { return batteryStatus; }
    public void setBatteryStatus(String batteryStatus) { this.batteryStatus = batteryStatus; }

    public String getBatteryPlugged() { return batteryPlugged; }
    public void setBatteryPlugged(String batteryPlugged) { this.batteryPlugged = batteryPlugged; }

    public String getCpuModel() { return cpuModel; }
    public void setCpuModel(String cpuModel) { this.cpuModel = cpuModel; }

    public Integer getCpuMaxFreqMHz() { return cpuMaxFreqMHz; }
    public void setCpuMaxFreqMHz(Integer cpuMaxFreqMHz) { this.cpuMaxFreqMHz = cpuMaxFreqMHz; }

    public String getNetworkType() { return networkType; }
    public void setNetworkType(String networkType) { this.networkType = networkType; }

    public String getCarrierName() { return carrierName; }
    public void setCarrierName(String carrierName) { this.carrierName = carrierName; }

    public String getSimState() { return simState; }
    public void setSimState(String simState) { this.simState = simState; }

    public String getImeiOrAndroidId() { return imeiOrAndroidId; }
    public void setImeiOrAndroidId(String imeiOrAndroidId) { this.imeiOrAndroidId = imeiOrAndroidId; }

    public String getScreenResolution() { return screenResolution; }
    public void setScreenResolution(String screenResolution) { this.screenResolution = screenResolution; }

    public float getScreenSizeInches() { return screenSizeInches; }
    public void setScreenSizeInches(float screenSizeInches) { this.screenSizeInches = screenSizeInches; }
}

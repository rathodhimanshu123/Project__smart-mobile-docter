package com.example.smartmobiledoctor.models;

public class DeviceInfo {
    private String modelName;
    private String manufacturer;
    private float ramSizeGB;
    private float storageSizeGB;
    private String androidVersion;
    private int processorCores;
    private int batteryLevel;

    public DeviceInfo() {}

    // Getters and setters
    public String getModelName() { return modelName; }
    public void setModelName(String modelName) { this.modelName = modelName; }

    public String getManufacturer() { return manufacturer; }
    public void setManufacturer(String manufacturer) { this.manufacturer = manufacturer; }

    public float getRamSizeGB() { return ramSizeGB; }
    public void setRamSizeGB(float ramSizeGB) { this.ramSizeGB = ramSizeGB; }

    public float getStorageSizeGB() { return storageSizeGB; }
    public void setStorageSizeGB(float storageSizeGB) { this.storageSizeGB = storageSizeGB; }

    public String getAndroidVersion() { return androidVersion; }
    public void setAndroidVersion(String androidVersion) { this.androidVersion = androidVersion; }

    public int getProcessorCores() { return processorCores; }
    public void setProcessorCores(int processorCores) { this.processorCores = processorCores; }

    public int getBatteryLevel() { return batteryLevel; }
    public void setBatteryLevel(int batteryLevel) { this.batteryLevel = batteryLevel; }
}

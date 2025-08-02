package com.example.smartmobiledoctor.services;

import android.app.ActivityManager;
import android.app.Service;
import android.content.BatteryManager;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Build;
import android.os.Environment;
import android.os.IBinder;
import android.os.StatFs;
import androidx.annotation.Nullable;

import com.example.smartmobiledoctor.models.DeviceInfo;
import com.google.gson.Gson;

public class DeviceInfoService extends Service {
    private static final long BYTES_IN_GB = 1073741824L; // 1024 * 1024 * 1024

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    public DeviceInfo collectDeviceInfo() {
        DeviceInfo deviceInfo = new DeviceInfo();

        // Get basic device info
        deviceInfo.setModelName(Build.MODEL);
        deviceInfo.setManufacturer(Build.MANUFACTURER);
        deviceInfo.setAndroidVersion(Build.VERSION.RELEASE);

        // Get RAM size
        ActivityManager actManager = (ActivityManager) getSystemService(Context.ACTIVITY_SERVICE);
        ActivityManager.MemoryInfo memInfo = new ActivityManager.MemoryInfo();
        actManager.getMemoryInfo(memInfo);
        deviceInfo.setRamSizeGB(memInfo.totalMem / (float) BYTES_IN_GB);

        // Get storage size
        StatFs statFs = new StatFs(Environment.getDataDirectory().getPath());
        long totalStorage = (long) statFs.getBlockCountLong() * (long) statFs.getBlockSizeLong();
        deviceInfo.setStorageSizeGB(totalStorage / (float) BYTES_IN_GB);

        // Get processor cores
        deviceInfo.setProcessorCores(Runtime.getRuntime().availableProcessors());

        // Get battery level
        IntentFilter iFilter = new IntentFilter(Intent.ACTION_BATTERY_CHANGED);
        Intent batteryStatus = registerReceiver(null, iFilter);
        
        int level = batteryStatus.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
        int scale = batteryStatus.getIntExtra(BatteryManager.EXTRA_SCALE, -1);
        
        float batteryPct = level * 100 / (float) scale;
        deviceInfo.setBatteryLevel(Math.round(batteryPct));

        return deviceInfo;
    }

    public String getDeviceInfoAsJson() {
        DeviceInfo deviceInfo = collectDeviceInfo();
        return new Gson().toJson(deviceInfo);
    }
}

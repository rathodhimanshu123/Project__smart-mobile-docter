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
import android.provider.Settings;
import android.telephony.SubscriptionInfo;
import android.telephony.SubscriptionManager;
import android.telephony.TelephonyManager;
import android.util.DisplayMetrics;
import android.view.WindowManager;
import androidx.annotation.Nullable;

import com.example.smartmobiledoctor.models.DeviceInfo;
import com.google.gson.Gson;

public class DeviceInfoService extends Service {
    private static final long BYTES_IN_GB = 1073741824L; // 1024 * 1024 * 1024
    private Context appContext;

    public DeviceInfoService() {
        // When constructed by system as a Service, 'this' is a valid Context
        this.appContext = this;
    }

    public DeviceInfoService(Context context) {
        // When manually created, use application context
        this.appContext = context.getApplicationContext();
    }

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
        ActivityManager actManager = (ActivityManager) appContext.getSystemService(Context.ACTIVITY_SERVICE);
        ActivityManager.MemoryInfo memInfo = new ActivityManager.MemoryInfo();
        actManager.getMemoryInfo(memInfo);
        deviceInfo.setRamSizeGB(memInfo.totalMem / (float) BYTES_IN_GB);
        deviceInfo.setAvailableRamGB(memInfo.availMem / (float) BYTES_IN_GB);

        // Get storage size
        StatFs statFs = new StatFs(Environment.getDataDirectory().getPath());
        long totalStorage = (long) statFs.getBlockCountLong() * (long) statFs.getBlockSizeLong();
        deviceInfo.setStorageSizeGB(totalStorage / (float) BYTES_IN_GB);
        long availableStorage = (long) statFs.getAvailableBlocksLong() * (long) statFs.getBlockSizeLong();
        deviceInfo.setAvailableStorageGB(availableStorage / (float) BYTES_IN_GB);

        // Get processor cores
        deviceInfo.setProcessorCores(Runtime.getRuntime().availableProcessors());
        // CPU model (best-effort from /proc/cpuinfo)
        try {
            java.io.BufferedReader br = new java.io.BufferedReader(new java.io.FileReader("/proc/cpuinfo"));
            String line;
            while ((line = br.readLine()) != null) {
                if (line.toLowerCase().contains("hardware") || line.toLowerCase().contains("model name")) {
                    String[] parts = line.split(":", 2);
                    if (parts.length == 2) {
                        deviceInfo.setCpuModel(parts[1].trim());
                        break;
                    }
                }
            }
            br.close();
        } catch (Exception ignored) {}

        // CPU max freq (per core; take max)
        try {
            int max = 0;
            for (int i = 0; i < deviceInfo.getProcessorCores(); i++) {
                java.io.File f = new java.io.File("/sys/devices/system/cpu/cpu" + i + "/cpufreq/cpuinfo_max_freq");
                if (f.exists()) {
                    String v = new java.util.Scanner(f).useDelimiter("\\Z").next().trim();
                    int mhz = Integer.parseInt(v) / 1000; // kHz to MHz
                    if (mhz > max) max = mhz;
                }
            }
            if (max > 0) deviceInfo.setCpuMaxFreqMHz(max);
        } catch (Exception ignored) {}

        // Get battery level
        IntentFilter iFilter = new IntentFilter(Intent.ACTION_BATTERY_CHANGED);
        Intent batteryStatus = appContext.registerReceiver(null, iFilter);
        
        int level = batteryStatus.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
        int scale = batteryStatus.getIntExtra(BatteryManager.EXTRA_SCALE, -1);
        
        float batteryPct = level * 100 / (float) scale;
        deviceInfo.setBatteryLevel(Math.round(batteryPct));
        int status = batteryStatus.getIntExtra(BatteryManager.EXTRA_STATUS, -1);
        String statusStr = "Unknown";
        if (status == BatteryManager.BATTERY_STATUS_CHARGING) statusStr = "Charging";
        else if (status == BatteryManager.BATTERY_STATUS_DISCHARGING) statusStr = "Discharging";
        else if (status == BatteryManager.BATTERY_STATUS_FULL) statusStr = "Full";
        else if (status == BatteryManager.BATTERY_STATUS_NOT_CHARGING) statusStr = "Not charging";
        deviceInfo.setBatteryStatus(statusStr);
        int plugged = batteryStatus.getIntExtra(BatteryManager.EXTRA_PLUGGED, -1);
        String pluggedStr = (plugged == BatteryManager.BATTERY_PLUGGED_AC) ? "AC" :
                (plugged == BatteryManager.BATTERY_PLUGGED_USB) ? "USB" :
                (plugged == BatteryManager.BATTERY_PLUGGED_WIRELESS) ? "Wireless" : "Unplugged";
        deviceInfo.setBatteryPlugged(pluggedStr);

        // Screen metrics
        WindowManager wm = (WindowManager) appContext.getSystemService(Context.WINDOW_SERVICE);
        DisplayMetrics dm = new DisplayMetrics();
        wm.getDefaultDisplay().getMetrics(dm);
        deviceInfo.setScreenResolution(dm.widthPixels + "x" + dm.heightPixels);
        float xInches = dm.widthPixels / dm.xdpi;
        float yInches = dm.heightPixels / dm.ydpi;
        deviceInfo.setScreenSizeInches((float) Math.sqrt(xInches * xInches + yInches * yInches));

        // Network info (best-effort)
        try {
            TelephonyManager tm = (TelephonyManager) appContext.getSystemService(Context.TELEPHONY_SERVICE);
            SubscriptionManager sm = (SubscriptionManager) appContext.getSystemService(Context.TELEPHONY_SUBSCRIPTION_SERVICE);
            if (sm != null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP_MR1) {
                java.util.List<SubscriptionInfo> subs = sm.getActiveSubscriptionInfoList();
                if (subs != null && !subs.isEmpty()) {
                    deviceInfo.setCarrierName(String.valueOf(subs.get(0).getCarrierName()));
                }
            }
            if (tm != null) {
                deviceInfo.setNetworkType(String.valueOf(tm.getNetworkType()));
                // IMEI: restricted on modern Android; fallback to Android ID
                String id = null;
                try {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        id = tm.getImei();
                    }
                } catch (SecurityException ignored) {}
                if (id == null) {
                    id = Settings.Secure.getString(appContext.getContentResolver(), Settings.Secure.ANDROID_ID);
                }
                deviceInfo.setImeiOrAndroidId(id);
            }
        } catch (Exception ignored) {}

        return deviceInfo;
    }

    public String getDeviceInfoAsJson() {
        DeviceInfo deviceInfo = collectDeviceInfo();
        return new Gson().toJson(deviceInfo);
    }
}

package com.example.smartmobiledoctor.webview;

import android.webkit.JavascriptInterface;
import com.example.smartmobiledoctor.services.DeviceInfoService;

public class DeviceInfoJsInterface {
    private DeviceInfoService deviceInfoService;

    public DeviceInfoJsInterface(DeviceInfoService service) {
        this.deviceInfoService = service;
    }

    @JavascriptInterface
    public String getDeviceInfo() {
        return deviceInfoService.getDeviceInfoAsJson();
    }
}

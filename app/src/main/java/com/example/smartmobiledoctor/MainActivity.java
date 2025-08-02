package com.example.smartmobiledoctor;

import android.content.Intent;
import android.os.Bundle;
import android.webkit.WebView;
import androidx.appcompat.app.AppCompatActivity;

import com.example.smartmobiledoctor.services.DeviceInfoService;
import com.example.smartmobiledoctor.webview.DeviceInfoJsInterface;

public class MainActivity extends AppCompatActivity {
    private WebView webView;
    private DeviceInfoService deviceInfoService;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        // Start the service
        Intent serviceIntent = new Intent(this, DeviceInfoService.class);
        startService(serviceIntent);
        deviceInfoService = new DeviceInfoService();

        // Setup WebView
        webView = findViewById(R.id.webview);
        webView.getSettings().setJavaScriptEnabled(true);
        
        // Add JavaScript interface
        DeviceInfoJsInterface jsInterface = new DeviceInfoJsInterface(deviceInfoService);
        webView.addJavascriptInterface(jsInterface, "Android");

        // Load your web page
        webView.loadUrl("file:///android_asset/index.html");
    }
}

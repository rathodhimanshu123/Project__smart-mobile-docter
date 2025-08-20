package com.example.smartmobiledoctor;

import android.content.Intent;
import android.os.Bundle;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.net.Uri;
import android.Manifest;
import android.content.pm.PackageManager;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.appcompat.app.AppCompatActivity;

import com.example.smartmobiledoctor.services.DeviceInfoService;
import com.example.smartmobiledoctor.webview.DeviceInfoJsInterface;

public class MainActivity extends AppCompatActivity {
    private WebView webView;
    private DeviceInfoService deviceInfoService;
    private static final int REQ_PERMS = 1001;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        // Start the service and create a context-aware instance for JS bridge
        Intent serviceIntent = new Intent(this, DeviceInfoService.class);
        startService(serviceIntent);
        deviceInfoService = new DeviceInfoService(this);

        // Setup WebView
        webView = findViewById(R.id.webview);
        webView.getSettings().setJavaScriptEnabled(true);
        
        // Add JavaScript interface
        DeviceInfoJsInterface jsInterface = new DeviceInfoJsInterface(deviceInfoService);
        webView.addJavascriptInterface(jsInterface, "Android");

        webView.setWebViewClient(new WebViewClient());

        // Request runtime permissions for phone state if needed
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_PHONE_STATE) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, new String[]{
                    Manifest.permission.READ_PHONE_STATE,
                    Manifest.permission.READ_PHONE_NUMBERS
            }, REQ_PERMS);
        }

        // Handle deep link: smd://collect?session_id=...&base_url=...
        Intent intent = getIntent();
        String url = "file:///android_asset/index.html";
        if (intent != null && Intent.ACTION_VIEW.equals(intent.getAction())) {
            Uri data = intent.getData();
            if (data != null) {
                String sessionId = data.getQueryParameter("session_id");
                String baseUrl = data.getQueryParameter("base_url");
                if (sessionId != null && baseUrl != null) {
                    url = "file:///android_asset/index.html?session_id=" + sessionId + "&base_url=" + Uri.encode(baseUrl);
                }
            }
        }
        webView.loadUrl(url);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        // No-op; we gracefully fallback if denied
    }
}

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
    private static final int REQ_PERMS = 1001;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        // Start Device Info Service
        startService(new Intent(this, DeviceInfoService.class));

        // Setup WebView
        setupWebView();

        // Request necessary permissions
        requestPhonePermissions();

        // Load the appropriate URL (handle deep link if exists)
        loadInitialUrl(getIntent());
    }

    /**
     * Initialize WebView and add JS interface.
     */
    private void setupWebView() {
        webView = findViewById(R.id.webview);
        webView.getSettings().setJavaScriptEnabled(true);
        webView.setWebViewClient(new WebViewClient());

        // Attach JS interface
        webView.addJavascriptInterface(new DeviceInfoJsInterface(this), "Android");
    }

    /**
     * Request phone state and number permissions at runtime.
     */
    private void requestPhonePermissions() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_PHONE_STATE) 
                != PackageManager.PERMISSION_GRANTED ||
            ContextCompat.checkSelfPermission(this, Manifest.permission.READ_PHONE_NUMBERS) 
                != PackageManager.PERMISSION_GRANTED) {

            ActivityCompat.requestPermissions(
                    this,
                    new String[]{
                            Manifest.permission.READ_PHONE_STATE,
                            Manifest.permission.READ_PHONE_NUMBERS
                    },
                    REQ_PERMS
            );
        }
    }

    /**
     * Load local HTML file or deep-linked URL.
     */
    private void loadInitialUrl(Intent intent) {
        String url = "file:///android_asset/index.html";

        if (intent != null && Intent.ACTION_VIEW.equals(intent.getAction())) {
            Uri data = intent.getData();
            if (data != null) {
                String sessionId = data.getQueryParameter("session_id");
                String baseUrl = data.getQueryParameter("base_url");

                if (sessionId != null && baseUrl != null) {
                    url = "file:///android_asset/index.html?session_id=" 
                            + Uri.encode(sessionId) 
                            + "&base_url=" 
                            + Uri.encode(baseUrl);
                }
            }
        }

        webView.loadUrl(url);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        // No specific action needed, fallback handled gracefully
    }
}

package com.freevoice.assistant;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.KeyEvent;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {
    private static final String PREFS = "freevoice_prefs";
    private static final String KEY_URL = "server_url";
    private static final String DEFAULT_URL = "http://127.0.0.1:8766";
    private static final int REQ_AUDIO = 1001;

    private LinearLayout setupLayout;
    private EditText urlInput;
    private WebView webView;
    private PermissionRequest pendingPermissionRequest;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        setupLayout = findViewById(R.id.setupLayout);
        urlInput = findViewById(R.id.urlInput);
        Button connectBtn = findViewById(R.id.connectBtn);
        Button settingsBtn = findViewById(R.id.settingsBtn);
        webView = findViewById(R.id.webView);

        String saved = getPrefs().getString(KEY_URL, DEFAULT_URL);
        urlInput.setText(saved);

        setupWebView();

        connectBtn.setOnClickListener(v -> openUrl(urlInput.getText().toString().trim()));
        settingsBtn.setOnClickListener(v -> showSetup());
        urlInput.setOnEditorActionListener((v, actionId, event) -> {
            if (actionId == EditorInfo.IME_ACTION_GO ||
                (event != null && event.getKeyCode() == KeyEvent.KEYCODE_ENTER)) {
                openUrl(urlInput.getText().toString().trim());
                return true;
            }
            return false;
        });

        // Auto-connect if we have a saved non-empty URL different handling? show setup first
        if (saved != null && !saved.isEmpty() && !DEFAULT_URL.equals(saved)) {
            openUrl(saved);
        } else {
            showSetup();
        }
    }

    private SharedPreferences getPrefs() {
        return getSharedPreferences(PREFS, MODE_PRIVATE);
    }

    private void setupWebView() {
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(true);
        s.setLoadsImagesAutomatically(true);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        s.setUseWideViewPort(true);
        s.setLoadWithOverviewMode(true);
        s.setBuiltInZoomControls(false);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String scheme = uri.getScheme();
                if ("http".equals(scheme) || "https".equals(scheme)) {
                    String host = uri.getHost() != null ? uri.getHost() : "";
                    String current = webView.getUrl();
                    if (current != null && current.startsWith("http")) {
                        Uri cur = Uri.parse(current);
                        if (host.equals(cur.getHost())) return false;
                    }
                    return false; // allow navigation within same host; external opens in view for simplicity
                }
                return true;
            }

            @Override
            public void onReceivedError(WebView view, int errorCode, String description, String failingUrl) {
                Toast.makeText(MainActivity.this, "Ошибка загрузки: " + description, Toast.LENGTH_LONG).show();
                showSetup();
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                runOnUiThread(() -> {
                    boolean wantsAudio = false;
                    for (String r : request.getResources()) {
                        if (PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(r)) wantsAudio = true;
                    }
                    if (wantsAudio) {
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M &&
                            checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                            pendingPermissionRequest = request;
                            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, REQ_AUDIO);
                            return;
                        }
                        request.grant(request.getResources());
                    } else {
                        request.grant(request.getResources());
                    }
                });
            }
        });
    }

    private void showSetup() {
        setupLayout.setVisibility(View.VISIBLE);
        webView.setVisibility(View.GONE);
    }

    private void openUrl(String url) {
        if (url == null || url.isEmpty()) {
            Toast.makeText(this, "Введите адрес сервера", Toast.LENGTH_SHORT).show();
            return;
        }
        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            url = "http://" + url;
        }
        getPrefs().edit().putString(KEY_URL, url).apply();
        setupLayout.setVisibility(View.GONE);
        webView.setVisibility(View.VISIBLE);
        webView.loadUrl(url);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQ_AUDIO) {
            if (pendingPermissionRequest != null) {
                boolean granted = grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED;
                if (granted) pendingPermissionRequest.grant(pendingPermissionRequest.getResources());
                else pendingPermissionRequest.deny();
                pendingPermissionRequest = null;
            }
        }
    }

    @Override
    public void onBackPressed() {
        if (webView.getVisibility() == View.VISIBLE && webView.canGoBack()) {
            webView.goBack();
        } else if (webView.getVisibility() == View.VISIBLE) {
            new AlertDialog.Builder(this)
                .setTitle("Выход")
                .setMessage("Закрыть приложение или изменить адрес сервера?")
                .setPositiveButton("Изменить адрес", (d, w) -> showSetup())
                .setNegativeButton("Закрыть", (d, w) -> finish())
                .setNeutralButton("Отмена", null)
                .show();
        } else {
            super.onBackPressed();
        }
    }
}

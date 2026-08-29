package com.chillbot.panel;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.view.KeyEvent;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.webkit.CookieManager;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.ProgressBar;

/**
 * The panel itself, wrapped in a WebView.
 *
 * The bot token never comes near this app - it stays on the machine running the
 * bot. All this holds is the panel address, and a session cookie the panel hands
 * out after you type the password.
 */
public class MainActivity extends Activity {

    private WebView web;
    private ProgressBar progress;
    private View offline;
    private String panelUrl;
    private boolean failed;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        panelUrl = Prefs.url(this);
        if (panelUrl == null) {
            startActivity(new Intent(this, SetupActivity.class));
            finish();
            return;
        }

        setContentView(R.layout.activity_main);
        web = findViewById(R.id.web);
        progress = findViewById(R.id.progress);
        offline = findViewById(R.id.offline);

        Button retry = findViewById(R.id.retry);
        retry.setOnClickListener(view -> load());

        CookieManager cookies = CookieManager.getInstance();
        cookies.setAcceptCookie(true);
        cookies.setAcceptThirdPartyCookies(web, false);

        web.getSettings().setJavaScriptEnabled(true);
        web.getSettings().setDomStorageEnabled(true);
        web.getSettings().setSupportZoom(false);
        web.getSettings().setMediaPlaybackRequiresUserGesture(true);
        web.setBackgroundColor(0xFF1A1B1E);

        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                progress.setProgress(newProgress);
                progress.setVisibility(newProgress >= 100 ? View.GONE : View.VISIBLE);
            }
        });

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri target = request.getUrl();
                Uri panel = Uri.parse(panelUrl);
                // Anything that is not the panel opens in a real browser instead.
                if (target.getHost() != null && target.getHost().equals(panel.getHost())) {
                    return false;
                }
                startActivity(new Intent(Intent.ACTION_VIEW, target));
                return true;
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    showOffline();
                }
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                if (!failed) {
                    offline.setVisibility(View.GONE);
                    web.setVisibility(View.VISIBLE);
                }
            }
        });

        load();
    }

    private void load() {
        failed = false;
        offline.setVisibility(View.GONE);
        web.setVisibility(View.VISIBLE);
        web.loadUrl(panelUrl);
    }

    private void showOffline() {
        failed = true;
        progress.setVisibility(View.GONE);
        web.setVisibility(View.GONE);
        offline.setVisibility(View.VISIBLE);
    }

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        menu.add(0, 1, 0, R.string.menu_reload);
        menu.add(0, 2, 1, R.string.menu_change);
        menu.add(0, 3, 2, R.string.menu_logout);
        menu.add(0, 4, 3, R.string.menu_browser);
        return true;
    }

    @Override
    public boolean onOptionsItemSelected(MenuItem item) {
        switch (item.getItemId()) {
            case 1:
                load();
                return true;
            case 2: {
                Intent intent = new Intent(this, SetupActivity.class);
                intent.putExtra(SetupActivity.EXTRA_EDIT, true);
                startActivity(intent);
                finish();
                return true;
            }
            case 3:
                CookieManager.getInstance().removeAllCookies(value -> load());
                return true;
            case 4:
                startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(panelUrl)));
                return true;
            default:
                return super.onOptionsItemSelected(item);
        }
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK && web != null && web.canGoBack()) {
            web.goBack();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    @Override
    protected void onPause() {
        super.onPause();
        CookieManager.getInstance().flush();
    }
}

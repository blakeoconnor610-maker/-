package com.chillbot.panel;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.EditorInfo;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * First screen.
 *
 * Normally nobody reads it: if an address is already saved it hands straight
 * over to the panel, and on a fresh install it listens for the bot announcing
 * itself on the wifi and connects on its own. Typing an address by hand is the
 * fallback, not the plan.
 */
public class SetupActivity extends Activity implements Discovery.Callback {

    /** Set on the intent to force the address prompt even when one is saved. */
    static final String EXTRA_EDIT = "edit";

    /** How long to wait for more panels before auto-connecting to a lone one. */
    private static final long SETTLE_MS = 1500;

    /** Where the panel sits when the bot is running on this same phone. */
    private static final String LOOPBACK = "http://127.0.0.1:8080";

    private final Map<String, String> discovered = new LinkedHashMap<>();
    private final Handler main = new Handler(Looper.getMainLooper());

    private Discovery discovery;
    private LinearLayout found;
    private TextView searching;
    private EditText url;
    private boolean handedOver;
    private boolean userIsTyping;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        boolean editing = getIntent().getBooleanExtra(EXTRA_EDIT, false);
        String saved = Prefs.url(this);
        if (!editing && saved != null) {
            open(saved);
            return;
        }

        setContentView(R.layout.activity_setup);

        url = findViewById(R.id.url);
        found = findViewById(R.id.found);
        searching = findViewById(R.id.searching);
        TextView error = findViewById(R.id.error);
        Button connect = findViewById(R.id.connect);

        if (saved != null) {
            url.setText(saved);
            url.setSelection(saved.length());
            userIsTyping = true;
        }

        url.setOnFocusChangeListener((view, focused) -> {
            if (focused) {
                userIsTyping = true;
            }
        });

        Runnable submit = () -> {
            String cleaned = Prefs.normalise(url.getText().toString());
            if (cleaned == null) {
                error.setText(R.string.bad_url);
                error.setVisibility(View.VISIBLE);
                return;
            }
            open(cleaned);
        };

        connect.setOnClickListener(view -> submit.run());

        // Running the bot in Termux on this same phone: mdns will not find it,
        // because loopback is not a network anything announces on.
        findViewById(R.id.thisphone).setOnClickListener(view -> open(LOOPBACK));
        url.setOnEditorActionListener((view, actionId, event) -> {
            if (actionId == EditorInfo.IME_ACTION_GO) {
                submit.run();
                return true;
            }
            return false;
        });

        discovery = new Discovery(this, this);

        // If nothing has announced itself by now, say so rather than spinning.
        main.postDelayed(() -> {
            if (!handedOver && discovered.isEmpty()) {
                searching.setText(R.string.found_none);
            }
        }, 6000);
    }

    @Override
    protected void onStart() {
        super.onStart();
        if (discovery != null) {
            discovery.start();
        }
    }

    @Override
    protected void onStop() {
        super.onStop();
        if (discovery != null) {
            discovery.stop();
        }
    }

    @Override
    public void onFound(String label, String address) {
        main.post(() -> {
            if (handedOver || discovered.containsKey(address)) {
                return;
            }
            discovered.put(address, label);
            redraw();

            // One panel, nobody typing: just go. That is the whole point.
            if (discovered.size() == 1 && !userIsTyping) {
                main.postDelayed(() -> {
                    if (!handedOver && discovered.size() == 1 && !userIsTyping) {
                        searching.setText(R.string.found_one);
                        open(address);
                    }
                }, SETTLE_MS);
            }
        });
    }

    private void redraw() {
        searching.setText(discovered.size() == 1 ? R.string.found_one : R.string.found_many);
        found.removeAllViews();
        for (Map.Entry<String, String> entry : discovered.entrySet()) {
            found.addView(button(entry.getValue(), entry.getKey()));
        }
    }

    private Button button(String label, String address) {
        Button item = new Button(this);
        item.setText(label + "\n" + address);
        item.setAllCaps(false);
        item.setGravity(Gravity.START | Gravity.CENTER_VERTICAL);
        item.setTextColor(Color.parseColor("#16181C"));
        item.setBackgroundTintList(getColorStateList(R.color.accent));
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        params.bottomMargin = (int) (8 * getResources().getDisplayMetrics().density);
        item.setLayoutParams(params);
        item.setOnClickListener(view -> open(address));
        return item;
    }

    private void open(String address) {
        if (handedOver) {
            return;
        }
        handedOver = true;
        Prefs.setUrl(this, address);
        startActivity(new Intent(this, MainActivity.class));
        finish();
    }
}

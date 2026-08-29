package com.chillbot.panel;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.view.inputmethod.EditorInfo;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;

/**
 * First screen. If an address is already saved it hands straight over to the
 * panel, so after the first run this is invisible.
 */
public class SetupActivity extends Activity {

    /** Set on the intent to force the address prompt even when one is saved. */
    static final String EXTRA_EDIT = "edit";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        boolean editing = getIntent().getBooleanExtra(EXTRA_EDIT, false);
        String saved = Prefs.url(this);
        if (!editing && saved != null) {
            startActivity(new Intent(this, MainActivity.class));
            finish();
            return;
        }

        setContentView(R.layout.activity_setup);

        EditText url = findViewById(R.id.url);
        TextView error = findViewById(R.id.error);
        Button connect = findViewById(R.id.connect);

        if (saved != null) {
            url.setText(saved);
            url.setSelection(saved.length());
        }

        Runnable submit = () -> {
            String cleaned = Prefs.normalise(url.getText().toString());
            if (cleaned == null) {
                error.setText(R.string.bad_url);
                error.setVisibility(TextView.VISIBLE);
                return;
            }
            Prefs.setUrl(this, cleaned);
            startActivity(new Intent(this, MainActivity.class));
            finish();
        };

        connect.setOnClickListener(view -> submit.run());
        url.setOnEditorActionListener((view, actionId, event) -> {
            if (actionId == EditorInfo.IME_ACTION_GO) {
                submit.run();
                return true;
            }
            return false;
        });
    }
}

package com.chillbot.panel;

import android.content.Context;
import android.content.SharedPreferences;
import android.net.Uri;

/** Remembers which panel this phone points at. Nothing secret is stored here. */
final class Prefs {

    private static final String FILE = "panel";
    private static final String KEY_URL = "url";

    private Prefs() {
    }

    static SharedPreferences of(Context context) {
        return context.getSharedPreferences(FILE, Context.MODE_PRIVATE);
    }

    static String url(Context context) {
        return of(context).getString(KEY_URL, null);
    }

    static void setUrl(Context context, String url) {
        of(context).edit().putString(KEY_URL, url).apply();
    }

    static void clear(Context context) {
        of(context).edit().remove(KEY_URL).apply();
    }

    /**
     * Tidies up whatever the user typed. Bare hosts get http:// put on the front,
     * trailing slashes go, and anything without a host comes back null.
     */
    static String normalise(String raw) {
        if (raw == null) {
            return null;
        }
        String text = raw.trim();
        if (text.isEmpty()) {
            return null;
        }
        if (!text.contains("://")) {
            text = "http://" + text;
        }
        while (text.endsWith("/")) {
            text = text.substring(0, text.length() - 1);
        }
        Uri uri = Uri.parse(text);
        String scheme = uri.getScheme();
        if (scheme == null || uri.getHost() == null || uri.getHost().isEmpty()) {
            return null;
        }
        if (!scheme.equals("http") && !scheme.equals("https")) {
            return null;
        }
        return text;
    }
}

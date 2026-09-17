package org.codebooker.t630switcher;

import android.app.Activity;
import android.app.AlertDialog;
import android.graphics.Color;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private static final String SWITCH_HELPER = "/data/adb/t630/switch-to-ubuntu";
    private static final String SWITCH_COMMAND = SWITCH_HELPER + " --switch-and-reboot";
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private Button button;
    private TextView status;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(Color.rgb(18, 18, 18));
        getWindow().setNavigationBarColor(Color.rgb(18, 18, 18));

        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setGravity(Gravity.CENTER_VERTICAL);
        page.setPadding(64, 48, 64, 48);
        page.setBackgroundColor(Color.rgb(18, 18, 18));

        TextView title = text("Native Android", 34, Color.WHITE);
        page.addView(title, matchWrap());
        TextView explanation = text(
            "Restart into Ubuntu without erasing Android apps or files.",
            20,
            Color.rgb(210, 210, 210)
        );
        LinearLayout.LayoutParams explanationParams = matchWrap();
        explanationParams.setMargins(0, 20, 0, 36);
        page.addView(explanation, explanationParams);

        button = new Button(this);
        button.setText("Restart into Ubuntu");
        button.setTextSize(22);
        button.setMinHeight(88);
        button.setOnClickListener(view -> confirmSwitch());
        page.addView(button, matchWrap());

        status = text(
            "The tablet verifies BOOT and every protected neighbor before restarting.",
            17,
            Color.rgb(180, 180, 180)
        );
        LinearLayout.LayoutParams statusParams = matchWrap();
        statusParams.setMargins(0, 30, 0, 0);
        page.addView(status, statusParams);
        setContentView(page);
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        );
    }

    private TextView text(String value, int size, int color) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(size);
        view.setTextColor(color);
        return view;
    }

    private void confirmSwitch() {
        new AlertDialog.Builder(this)
            .setTitle("Restart into Ubuntu?")
            .setMessage("Android apps will close. Android data stays encrypted on its own partition.")
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Restart into Ubuntu", (dialog, which) -> runSwitch())
            .show();
    }

    private void runSwitch() {
        button.setEnabled(false);
        status.setText("Verifying the tablet and preparing Ubuntu…");
        executor.execute(() -> {
            int result = -1;
            String lastLine = "The guarded switch did not start.";
            try {
                // Samsung's stock DEFEX path drops credentials when MagiskSU
                // launches /system/bin/sh through `su -c`.  An interactive
                // Magisk root shell retains its verified root context.  Feed
                // only this compile-time constant, never user-controlled text.
                Process process = new ProcessBuilder("su")
                    .redirectErrorStream(true)
                    .start();
                try (BufferedWriter writer = new BufferedWriter(
                        new OutputStreamWriter(process.getOutputStream()))) {
                    writer.write("set -e\n");
                    writer.write("exec " + SWITCH_COMMAND + "\n");
                }
                try (BufferedReader reader = new BufferedReader(
                        new InputStreamReader(process.getInputStream()))) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        if (!line.trim().isEmpty()) {
                            lastLine = line.trim();
                        }
                    }
                }
                result = process.waitFor();
            } catch (Exception error) {
                lastLine = error.getClass().getSimpleName() + ": " + error.getMessage();
            }
            final int finalResult = result;
            final String finalLine = lastLine;
            runOnUiThread(() -> {
                if (finalResult == 0) {
                    status.setText("Ubuntu verified. Restarting now…");
                } else {
                    status.setText("Could not switch safely: " + finalLine);
                    button.setEnabled(true);
                }
            });
        });
    }

    @Override
    protected void onDestroy() {
        executor.shutdownNow();
        super.onDestroy();
    }
}

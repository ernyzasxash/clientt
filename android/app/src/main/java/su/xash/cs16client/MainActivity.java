package su.xash.cs16client;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ComponentName;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.widget.EditText;
import android.widget.Toast;
import org.json.JSONObject;
import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import java.io.IOException;

public class MainActivity extends Activity {
	private SharedPreferences prefs;
	private static final String PREFS_NAME = "cs16_license";
	private static final String KEY_LICENSE = "license_key";
	private String licenseKey = null;
	private OkHttpClient httpClient = new OkHttpClient();
	private static final String LICENSE_SERVER = "http://72.60.130.39/check";

    private volatile boolean serverConnected = false;
    private Thread heartbeatThread;

    static {
        System.loadLibrary("your_native_lib"); // Load your native library here
    }

    private static native void nativeSetLicenseVerified(boolean verified);
    private static native String nativeGetCodeHash();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        
        // Check if we have a stored license key
        licenseKey = prefs.getString(KEY_LICENSE, null);
        
        if (licenseKey != null && !licenseKey.isEmpty()) {
            // Key already exists, launch directly
            launchEngine();
        } else {
            // Ask for license key
            showLicenseDialog();
        }
    }
    
    private void showLicenseDialog() {
        final EditText input = new EditText(this);
        input.setHint("Enter license key");
        input.setTextColor(android.graphics.Color.BLACK);
        
        new AlertDialog.Builder(this)
            .setTitle("License Required")
            .setMessage("Enter your license key")
            .setView(input)
            .setCancelable(false)
            .setPositiveButton("Verify", (dialog, which) -> {
                String key = input.getText().toString().trim();
                if (key.isEmpty()) {
                    Toast.makeText(MainActivity.this, "Key cannot be empty", Toast.LENGTH_SHORT).show();
                    showLicenseDialog();
                } else {
                    // Verify key with server
                    verifyKeyWithServer(key);
                }
            })
            .show();
    }
    
    private void verifyKeyWithServer(String key) {
        try {
            JSONObject jsonBody = new JSONObject();
            jsonBody.put("key", key);
            jsonBody.put("device_name", Build.MODEL);
            jsonBody.put("device_info", getDeviceInfo());
            jsonBody.put("code_hash", getCodeHash());
            jsonBody.put("timestamp", System.currentTimeMillis());
            
            RequestBody body = RequestBody.create(
                jsonBody.toString(),
                MediaType.parse("application/json")
            );
            
            Request request = new Request.Builder()
                .url(LICENSE_SERVER)
                .post(body)
                .build();
            
            httpClient.newCall(request).enqueue(new Callback() {
                @Override
                public void onFailure(Call call, IOException e) {
                    runOnUiThread(() -> {
                        Toast.makeText(MainActivity.this, "Server connection failed", Toast.LENGTH_SHORT).show();
                        showLicenseDialog();
                    });
                }
                
                @Override
                public void onResponse(Call call, okhttp3.Response response) throws IOException {
                    String respBody = response.body().string();
                    try {
                        JSONObject json = new JSONObject(respBody);
                        String result = json.getString("result");
                        
                        if ("success".equals(result)) {
                            licenseKey = key;
                            prefs.edit().putString(KEY_LICENSE, key).apply();
                            runOnUiThread(() -> {
                                Toast.makeText(MainActivity.this, "License verified", Toast.LENGTH_SHORT).show();
                                nativeSetLicenseVerified(true);
                                startHeartbeat(key);
                                launchEngine();
                            });
                        } else {
                            runOnUiThread(() -> {
                                nativeSetLicenseVerified(false);
                                Toast.makeText(MainActivity.this, "Wrong key", Toast.LENGTH_SHORT).show();
                                showLicenseDialog();
                            });
                        }
                    } catch (Exception e) {
                        runOnUiThread(() -> {
                            Toast.makeText(MainActivity.this, "Server error", Toast.LENGTH_SHORT).show();
                            showLicenseDialog();
                        });
                    }
                }
            });
        } catch (Exception e) {
            Toast.makeText(this, "Error: " + e.getMessage(), Toast.LENGTH_SHORT).show();
            showLicenseDialog();
        }
    }
    
    private String getDeviceInfo() {
        try {
            return new JSONObject()
                .put("model", Build.MODEL)
                .put("device", Build.DEVICE)
                .put("manufacturer", Build.MANUFACTURER)
                .put("version", Build.VERSION.RELEASE)
                .put("sdk", Build.VERSION.SDK_INT)
                .toString();
        } catch (Exception e) {
            return "{}";
        }
    }
    
    private void launchEngine() {
        String pkg = "su.xash.engine.test";

        try {
            getPackageManager().getPackageInfo(pkg, 0);
        } catch (PackageManager.NameNotFoundException e) {
            try {
                pkg = "su.xash.engine";
                getPackageManager().getPackageInfo(pkg, 0);
            } catch (PackageManager.NameNotFoundException ex) {
                startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse("https://github.com/FWGS/xash3d-fwgs/releases/tag/continuous")).setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK));
                finish();
                return;
            }
        }

        startActivity(new Intent().setComponent(new ComponentName(pkg, "su.xash.engine.XashActivity"))
                .setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK)
                .putExtra("gamedir", "cstrike")
                .putExtra("gamelibdir", getApplicationInfo().nativeLibraryDir)
                .putExtra("argv", "-dev 2 -log -dll @yapb")
                .putExtra("package", getPackageName())
                .putExtra("license_key", licenseKey)
                .putExtra("license_verified", true));
        finish();
    }

    private void startHeartbeat(final String key) {
        stopHeartbeat();
        serverConnected = true;
        heartbeatThread = new Thread(() -> {
            OkHttpClient client = new OkHttpClient();
            while (serverConnected) {
                try {
                    JSONObject jsonBody = new JSONObject();
                    jsonBody.put("key", key);
                    jsonBody.put("device_name", Build.MODEL);
                    jsonBody.put("device_info", getDeviceInfo());
                    RequestBody body = RequestBody.create(
                            jsonBody.toString(),
                            MediaType.parse("application/json")
                    );
                    Request request = new Request.Builder()
                            .url("http://72.60.130.39/heartbeat")
                            .post(body)
                            .build();
                    okhttp3.Response response = client.newCall(request).execute();
                    if (!response.isSuccessful()) {
                        throw new IOException("Unexpected code " + response);
                    }
                    response.close();
                } catch (Exception e) {
                    serverConnected = false;
                    runOnUiThread(() -> {
                        Toast.makeText(MainActivity.this, "No server connection", Toast.LENGTH_SHORT).show();
                        // Optionally show dialog or block gameplay
                    });
                    break;
                }
                try {
                    Thread.sleep(1000);
                } catch (InterruptedException ignored) {
                    break;
                }
            }
        });
        heartbeatThread.start();
    }

    private void stopHeartbeat() {
        serverConnected = false;
        nativeSetLicenseVerified(false);
        if (heartbeatThread != null) {
            heartbeatThread.interrupt();
            heartbeatThread = null;
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        stopHeartbeat();
    }

    public String getCodeHash() {
        return nativeGetCodeHash();
    }
}

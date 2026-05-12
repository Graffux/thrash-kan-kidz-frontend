const { withAndroidManifest } = require("expo/config-plugins");

module.exports = function removePermissionsPlugin(config) {
  return withAndroidManifest(config, async (config) => {
    const manifest = config.modResults.manifest;
    
    // Ensure tools namespace is declared
    if (!manifest.$) {
      manifest.$ = {};
    }
    manifest.$["xmlns:tools"] = "http://schemas.android.com/tools";
    
    const removePermissions = [
      "android.permission.READ_MEDIA_IMAGES",
      "android.permission.READ_MEDIA_VIDEO",
      "android.permission.READ_EXTERNAL_STORAGE",
      "android.permission.WRITE_EXTERNAL_STORAGE",
      "android.permission.RECORD_AUDIO",
      // Strip foreground service permissions injected by expo-audio.
      // We only play short SFX while the user is actively in the app —
      // never background audio — so these permissions are not needed
      // and trigger a Google Play declaration requirement.
      "android.permission.FOREGROUND_SERVICE",
      "android.permission.FOREGROUND_SERVICE_MEDIA_PLAYBACK",
    ];
    
    if (!manifest["uses-permission"]) {
      manifest["uses-permission"] = [];
    }
    
    // Remove existing entries for these permissions
    manifest["uses-permission"] = manifest["uses-permission"].filter(
      (perm) => !removePermissions.includes(perm.$?.["android:name"])
    );
    
    // Add them back with tools:node="remove" so they get stripped from merged manifest
    for (const perm of removePermissions) {
      manifest["uses-permission"].push({
        $: {
          "android:name": perm,
          "tools:node": "remove",
        },
      });
    }
    
    return config;
  });
};

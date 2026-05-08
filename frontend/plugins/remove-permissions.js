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

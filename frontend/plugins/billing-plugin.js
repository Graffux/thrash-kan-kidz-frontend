const { withAppBuildGradle, withAndroidManifest } = require('expo/config-plugins');

// Add BILLING permission to AndroidManifest
const withBillingPermission = (config) => {
  return withAndroidManifest(config, (config) => {
    const manifest = config.modResults.manifest;
    if (!manifest['uses-permission']) {
      manifest['uses-permission'] = [];
    }
    const hasPermission = manifest['uses-permission'].some(
      (p) => p.$?.['android:name'] === 'com.android.vending.BILLING'
    );
    if (!hasPermission) {
      manifest['uses-permission'].push({
        $: { 'android:name': 'com.android.vending.BILLING' },
      });
    }
    return config;
  });
};

// Force Play Billing Library 7.0.0 in build.gradle
const withBillingLibrary = (config) => {
  return withAppBuildGradle(config, (config) => {
    const contents = config.modResults.contents;
    if (!contents.includes('com.android.billingclient:billing')) {
      config.modResults.contents = contents.replace(
        /dependencies\s*{/,
        `dependencies {\n    implementation "com.android.billingclient:billing:7.0.0"`
      );
    }
    return config;
  });
};

module.exports = (config) => {
  config = withBillingPermission(config);
  config = withBillingLibrary(config);
  return config;
};

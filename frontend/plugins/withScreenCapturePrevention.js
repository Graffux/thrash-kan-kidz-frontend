const { withAndroidStyles, AndroidConfig } = require('@expo/config-plugins');

const withScreenCapturePrevention = (config) => {
  return withAndroidStyles(config, async (config) => {
    // Add FLAG_SECURE to the main activity style
    // This is done by modifying the theme in styles.xml
    const styles = config.modResults;
    
    // Find or create the AppTheme style
    if (!styles.resources) {
      styles.resources = {};
    }
    if (!styles.resources.style) {
      styles.resources.style = [];
    }
    
    // Check if we already have an AppTheme
    let appTheme = styles.resources.style.find(
      (style) => style.$.name === 'AppTheme' || style.$.name === 'Theme.App.SplashScreen'
    );
    
    if (appTheme) {
      // Add windowSecure item to prevent screenshots
      if (!appTheme.item) {
        appTheme.item = [];
      }
      
      // Check if windowSecure is already set
      const hasWindowSecure = appTheme.item.some(
        (item) => item.$.name === 'android:windowSecure'
      );
      
      if (!hasWindowSecure) {
        appTheme.item.push({
          $: { name: 'android:windowSecure' },
          _: 'true',
        });
      }
    }
    
    return config;
  });
};

module.exports = withScreenCapturePrevention;

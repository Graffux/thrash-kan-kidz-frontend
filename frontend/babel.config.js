module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    // Reanimated 4 split its worklets out into a separate package; the
    // plugin must be listed last so it runs after all other transforms.
    // Without this, any component using <MotiView> (which depends on
    // reanimated) silently fails or throws at runtime.
    plugins: ['react-native-worklets/plugin'],
  };
};

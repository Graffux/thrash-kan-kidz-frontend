/**
 * DrippingLogo — the "Thrash Kan Kidz" wordmark header.
 *
 * Renders the raster brand logo (slime-dripping metal letters on red plate).
 * Kept as a named component so home/auth screens import path is unchanged.
 *
 * The asset is local (bundled) so it loads instantly with no network call —
 * critical for the home screen first paint.
 */
import React from 'react';
import { View, Image, StyleSheet, StyleProp, ViewStyle } from 'react-native';

interface Props {
  width?: number;
  height?: number;
  style?: StyleProp<ViewStyle>;
}

// Source aspect is 1024x1024 in the optimized JPG, but the visible
// wordmark inside the artwork is roughly 4:3 — width/height defaults
// favor a wide banner look.
export const DrippingLogo: React.FC<Props> = ({ width = 280, height = 146, style }) => {
  return (
    <View style={[styles.wrap, { width, height }, style]} testID="dripping-logo">
      <Image
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        source={require('../assets/headers/tkk_home.png')}
        style={styles.img}
        resizeMode="contain"
      />
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  img: {
    width: '100%',
    height: '100%',
  },
});

export default DrippingLogo;

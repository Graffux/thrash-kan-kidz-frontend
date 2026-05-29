/**
 * GrungeBackground — shared full-screen wrapper that lays down the
 * Thrash Kan Kidz visual identity (dark base + slime-green vignette
 * + rust corners + noise overlay) behind any screen content.
 *
 * Built with absolutely-positioned <View>s + LinearGradient so it works
 * everywhere (web preview, Android, iOS) without bundling raster images
 * for every layer. Children render on top via flex.
 *
 * Usage:
 *   <GrungeBackground>
 *     <ScrollView>...</ScrollView>
 *   </GrungeBackground>
 */
import React from 'react';
import { View, StyleSheet, StyleProp, ViewStyle, Image } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { SlimeBubbles } from './SlimeBubbles';

const RUST_TEXTURE = require('../../assets/decor/rust_texture.png');
// v2 image generated with Gemini Nano Banana — the previous `ronch_peek.png`
// was cropped above the eyes (only forehead + dreadlocks visible). v2 places
// the FULL face (eyes, nose, grinning mouth, slime) in the lower 60% of the
// canvas with hands gripping the bottom edge, so when positioned at the
// bottom of the screen the character clearly reads as "peeking up" rather
// than as a faceless forehead.
const RONCH_PEEK = require('../../assets/decor/ronch_peek_v2.png');

interface Props {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  /** Slightly lighter base for screens that need more contrast (e.g. forms). */
  lighten?: boolean;
  /** Hide animated bubbles on screens with heavy scroll/CPU work (e.g. modals). */
  noBubbles?: boolean;
  /** Hide the Ronch peek silhouette (e.g. for the login splash). */
  noRonchPeek?: boolean;
}

export const GrungeBackground: React.FC<Props> = ({ children, style, lighten, noBubbles, noRonchPeek }) => {
  return (
    <View style={[styles.root, lighten && styles.rootLight, style]} testID="grunge-bg">
      {/* Dark base layer — solid color reads cleaner than a gradient on dark UI. */}
      <View style={styles.base} pointerEvents="none" />

      {/* Slime-green radial-ish vignette via a soft top-center gradient. We
          fake a radial by stacking two linear gradients (top & bottom) since
          react-native-linear-gradient doesn't ship a true radial. */}
      <LinearGradient
        colors={['rgba(57, 255, 20, 0.10)', 'rgba(57, 255, 20, 0.00)', 'rgba(0, 0, 0, 0.0)']}
        locations={[0, 0.5, 1]}
        start={{ x: 0.5, y: 0 }}
        end={{ x: 0.5, y: 1 }}
        style={StyleSheet.absoluteFill}
        pointerEvents="none"
      />

      {/* Rust corner glows — top-left + bottom-right warm tint */}
      <LinearGradient
        colors={['rgba(140, 60, 18, 0.35)', 'rgba(140, 60, 18, 0.0)']}
        start={{ x: 0, y: 0 }}
        end={{ x: 0.55, y: 0.55 }}
        style={StyleSheet.absoluteFill}
        pointerEvents="none"
      />
      <LinearGradient
        colors={['rgba(0,0,0,0)', 'rgba(120, 30, 10, 0.30)']}
        start={{ x: 0.45, y: 0.45 }}
        end={{ x: 1, y: 1 }}
        style={StyleSheet.absoluteFill}
        pointerEvents="none"
      />

      {/* Edge vignette — darken corners so content pops in the middle */}
      <LinearGradient
        colors={['rgba(0,0,0,0.55)', 'rgba(0,0,0,0)', 'rgba(0,0,0,0.65)']}
        locations={[0, 0.5, 1]}
        start={{ x: 0.5, y: 0 }}
        end={{ x: 0.5, y: 1 }}
        style={StyleSheet.absoluteFill}
        pointerEvents="none"
      />

      {/* Rust texture overlay — extremely faint, tiles behind everything */}
      <Image
        source={RUST_TEXTURE}
        style={styles.rustTexture}
        resizeMode="cover"
      />

      {/* Noise overlay — tiled dots simulate grain without a raster asset.
          The grid is intentionally sparse so it never overwhelms the UI;
          on smaller phones the dots get clipped at edges which is fine. */}
      <View style={styles.noise} pointerEvents="none">
        {Array.from({ length: 80 }).map((_, i) => (
          <View
            key={i}
            style={[
              styles.noiseDot,
              {
                top: `${(i * 37) % 100}%`,
                left: `${(i * 71) % 100}%`,
                opacity: 0.04 + ((i * 13) % 9) / 100,
              },
            ]}
          />
        ))}
      </View>

      {/* Animated slime bubbles floating upward (cosmetic ambient) */}
      {!noBubbles && <SlimeBubbles />}

      {/* Ronch peeking up from the bottom-right corner */}
      {!noRonchPeek && (
        <Image
          source={RONCH_PEEK}
          style={styles.ronchPeek}
          resizeMode="contain"
        />
      )}

      <View style={styles.content}>{children}</View>
    </View>
  );
};

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: '#070a07',
  },
  rootLight: {
    backgroundColor: '#0d1410',
  },
  base: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#0a0d0a',
  },
  noise: {
    ...StyleSheet.absoluteFillObject,
  },
  rustTexture: {
    ...StyleSheet.absoluteFillObject,
    opacity: 0.12,
  },
  ronchPeek: {
    position: 'absolute',
    bottom: 56, // hugs the top of the bottom-nav so face starts above it
    right: -20, // slight bleed off-screen, more body visible
    width: 280,
    height: 280, // square aspect ratio for the asset shows the full character
    opacity: 0.65,
  },
  noiseDot: {
    position: 'absolute',
    width: 2,
    height: 2,
    borderRadius: 1,
    backgroundColor: '#a8ffae',
  },
  content: {
    flex: 1,
  },
});

export default GrungeBackground;

/**
 * MascotSplash — JS-side branded splash that overlays the app for the
 * first ~1.5s after the native splash hides.
 *
 * Why we need this:
 *   - Native splash (configured in app.json) is a static PNG.
 *   - We want Ronch to do a quick animated entrance: scale-in, slight
 *     head-tilt, then fade away with the logo tagline.
 *   - Adding it as a JS overlay means we can iterate on it freely
 *     without re-building / re-uploading native splash assets.
 *
 * Mount this near the top of the root layout (`app/_layout.tsx`) so it
 * sits above every screen during the boot sequence. After `holdMs` it
 * fades and unmounts itself; no parent cleanup required.
 */
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Image as ExpoImage } from 'expo-image';
import { MotiView } from 'moti';
import { MASCOT_SIGNATURE, MASCOT_TAGLINE } from '../assets/mascot';

interface Props {
  holdMs?: number;  // total visible duration before fade out (default 1500)
}

export const MascotSplash: React.FC<Props> = ({ holdMs = 1500 }) => {
  const [visible, setVisible] = useState(true);
  const [fading, setFading] = useState(false);

  useEffect(() => {
    // Stage 1: trigger fade just before hold expires
    const fadeAt = setTimeout(() => setFading(true), Math.max(0, holdMs - 400));
    // Stage 2: unmount after fade finishes
    const unmountAt = setTimeout(() => setVisible(false), holdMs);
    return () => {
      clearTimeout(fadeAt);
      clearTimeout(unmountAt);
    };
  }, [holdMs]);

  if (!visible) return null;

  return (
    <MotiView
      pointerEvents="none"
      from={{ opacity: 1 }}
      animate={{ opacity: fading ? 0 : 1 }}
      transition={{ type: 'timing', duration: 400 }}
      style={styles.overlay}
    >
      <View style={styles.center}>
        <MotiView
          from={{ scale: 0.4, rotate: '-12deg', opacity: 0 }}
          animate={{ scale: 1, rotate: '0deg', opacity: 1 }}
          transition={{ type: 'spring', damping: 12, stiffness: 180, mass: 0.7 }}
        >
          <ExpoImage
            source={{ uri: MASCOT_SIGNATURE }}
            style={styles.image}
            contentFit="contain"
            cachePolicy="memory-disk"
          />
        </MotiView>
        <MotiView
          from={{ translateY: 12, opacity: 0 }}
          animate={{ translateY: 0, opacity: 1 }}
          transition={{ type: 'timing', duration: 600, delay: 300 }}
        >
          <Text style={styles.tagline}>{MASCOT_TAGLINE}</Text>
        </MotiView>
      </View>
    </MotiView>
  );
};

const styles = StyleSheet.create({
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#050505',
    zIndex: 9999,
    elevation: 9999,
    alignItems: 'center',
    justifyContent: 'center',
  },
  center: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  image: {
    width: 280,
    height: 280,
  },
  tagline: {
    marginTop: 18,
    color: '#39FF14',
    fontSize: 14,
    fontWeight: '900',
    letterSpacing: 3,
    textAlign: 'center',
    textShadowColor: '#39FF14',
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 8,
  },
});

export default MascotSplash;

/**
 * MascotStamp — small corner-anchored mascot badge for reveal moments.
 *
 * Drops a 60-80px Ronch headshot into a corner of any modal/screen with
 * a subtle pop-in entrance and a slow head-tilt sway. Used on pack
 * reveals, series-completion modals, etc., to keep him present without
 * blocking the main content.
 *
 * Mood swap support: pass `mood` to show happy/angry/wide-eyed/idle.
 * Position support: 'tl' | 'tr' | 'bl' | 'br' for the four corners.
 */
import React from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import { Image as ExpoImage } from 'expo-image';
import { MotiView } from 'moti';
import { MASCOT_FOR_EVENT } from '../assets/mascot';

interface Props {
  mood?: 'idle' | 'variant_pull' | 'series_complete' | 'duplicate' | 'rare_reveal';
  position?: 'tl' | 'tr' | 'bl' | 'br';
  size?: number;
  style?: ViewStyle;
}

const POSITION_STYLE: Record<NonNullable<Props['position']>, ViewStyle> = {
  tl: { top: 12, left: 12 },
  tr: { top: 12, right: 12 },
  bl: { bottom: 12, left: 12 },
  br: { bottom: 12, right: 12 },
};

export const MascotStamp: React.FC<Props> = ({
  mood = 'idle',
  position = 'br',
  size = 70,
  style,
}) => {
  return (
    <MotiView
      pointerEvents="none"
      from={{ scale: 0, rotate: '-30deg', opacity: 0 }}
      animate={{ scale: 1, rotate: '0deg', opacity: 1 }}
      transition={{ type: 'spring', damping: 9, stiffness: 200, mass: 0.6 }}
      style={[
        styles.wrap,
        POSITION_STYLE[position],
        { width: size, height: size },
        style,
      ]}
    >
      <MotiView
        from={{ rotate: '-4deg' }}
        animate={{ rotate: '4deg' }}
        transition={{ type: 'timing', duration: 1500, loop: true }}
        style={styles.inner}
      >
        <View
          style={[
            styles.glow,
            { width: size, height: size, borderRadius: size / 2 },
          ]}
        >
          <ExpoImage
            source={{ uri: MASCOT_FOR_EVENT(mood) }}
            style={[styles.image, { borderRadius: size / 2 }]}
            contentFit="cover"
            cachePolicy="memory-disk"
          />
        </View>
      </MotiView>
    </MotiView>
  );
};

const styles = StyleSheet.create({
  wrap: {
    position: 'absolute',
    zIndex: 99,
    elevation: 99,
  },
  inner: {
    width: '100%',
    height: '100%',
  },
  glow: {
    borderWidth: 2,
    borderColor: '#39FF14',
    backgroundColor: '#050505',
    overflow: 'hidden',
    shadowColor: '#39FF14',
    shadowOpacity: 0.9,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 0 },
    elevation: 10,
  },
  image: {
    width: '100%',
    height: '100%',
  },
});

export default MascotStamp;

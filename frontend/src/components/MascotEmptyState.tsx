/**
 * MascotEmptyState — themed empty placeholder featuring Ronch.
 *
 * Use anywhere a list / grid / section would otherwise be a blank space
 * with text. Ronch gives it personality + reinforces brand on first run.
 *
 * Configurable headline + subtext. Optional bottom CTA via children prop.
 */
import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';
import { Image as ExpoImage } from 'expo-image';
import { MotiView } from 'moti';
import { MASCOT_FOR_EVENT } from '../assets/mascot';

interface Props {
  headline: string;
  subtext?: string;
  mood?: 'idle' | 'variant_pull' | 'series_complete' | 'duplicate' | 'rare_reveal';
  style?: ViewStyle;
  children?: React.ReactNode;
}

export const MascotEmptyState: React.FC<Props> = ({
  headline,
  subtext,
  mood = 'idle',
  style,
  children,
}) => {
  return (
    <View style={[styles.wrap, style]}>
      <MotiView
        from={{ rotate: '-3deg', translateY: 0 }}
        animate={{ rotate: '3deg', translateY: -4 }}
        transition={{ type: 'timing', duration: 1800, loop: true }}
        style={styles.imageWrap}
      >
        <ExpoImage
          source={{ uri: MASCOT_FOR_EVENT(mood) }}
          style={styles.image}
          contentFit="contain"
          cachePolicy="memory-disk"
        />
      </MotiView>
      <Text style={styles.headline}>{headline}</Text>
      {subtext ? <Text style={styles.subtext}>{subtext}</Text> : null}
      {children}
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: {
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
  },
  imageWrap: {
    width: 220,
    height: 220,
    alignItems: 'center',
    justifyContent: 'center',
  },
  image: {
    width: '100%',
    height: '100%',
  },
  headline: {
    fontSize: 22,
    fontWeight: '900',
    letterSpacing: 2,
    textTransform: 'uppercase',
    color: '#39FF14',
    textAlign: 'center',
    marginTop: 12,
    textShadowColor: '#39FF14',
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 8,
  },
  subtext: {
    fontSize: 14,
    color: '#bdbdbd',
    textAlign: 'center',
    marginTop: 8,
    paddingHorizontal: 24,
    lineHeight: 20,
  },
});

export default MascotEmptyState;

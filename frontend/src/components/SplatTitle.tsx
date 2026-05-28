/**
 * SplatTitle — paint-splat / drip section header used across the app.
 *
 * Visual: text in slime-green / bone-white with a drip-mask background
 * (a wavy SVG splat behind the text). No raster assets needed; the splat
 * is drawn at runtime with two stacked SVG paths to suggest a paint stain.
 *
 * Usage:
 *   <SplatTitle>THRASH MISSIONS</SplatTitle>
 */
import React from 'react';
import { View, Text, StyleSheet, StyleProp, ViewStyle, TextStyle } from 'react-native';
import Svg, { Path, Defs, LinearGradient as SvgGrad, Stop } from 'react-native-svg';
import { FONTS } from '../theme';

interface Props {
  children: React.ReactNode;
  /** Bone-white text vs slime-green text. */
  variant?: 'slime' | 'bone';
  style?: StyleProp<ViewStyle>;
  textStyle?: StyleProp<TextStyle>;
}

export const SplatTitle: React.FC<Props> = ({
  children,
  variant = 'slime',
  style,
  textStyle,
}) => {
  const fillId = variant === 'slime' ? 'splatSlime' : 'splatBone';
  const fillStart = variant === 'slime' ? '#1a2a1a' : '#2a1a14';
  const fillEnd = variant === 'slime' ? '#0a1a0a' : '#1a0e08';
  const textColor = variant === 'slime' ? '#9aff5a' : '#f4e8c8';

  return (
    <View style={[styles.wrap, style]}>
      <Svg width="100%" height="50" viewBox="0 0 320 50" preserveAspectRatio="none" style={styles.splat}>
        <Defs>
          <SvgGrad id={fillId} x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor={fillStart} stopOpacity="1" />
            <Stop offset="1" stopColor={fillEnd} stopOpacity="1" />
          </SvgGrad>
        </Defs>
        {/* Main splat blob — wavy uneven edges */}
        <Path
          d="M 8 8 Q 16 2 28 6 Q 50 4 80 8 Q 130 5 180 9 Q 240 6 290 10 Q 310 8 314 18 Q 318 28 308 32 Q 250 36 200 33 Q 130 35 70 32 Q 24 35 10 30 Q 2 22 8 8 Z"
          fill={`url(#${fillId})`}
        />
        {/* Drip details — longer drips hanging off the bottom edge */}
        <Path d="M 30 32 Q 31 44 32 48 L 28 48 Q 29 44 29 32 Z" fill="#39ff14" opacity="0.65" />
        <Path d="M 90 33 Q 91 42 92 46 L 88 46 Q 89 42 89 33 Z" fill="#39ff14" opacity="0.5" />
        <Path d="M 160 32 Q 161 48 162 50 L 158 50 Q 159 48 159 32 Z" fill="#39ff14" opacity="0.7" />
        <Path d="M 220 33 Q 221 40 222 44 L 218 44 Q 219 40 219 33 Z" fill="#39ff14" opacity="0.55" />
        <Path d="M 280 32 Q 281 46 282 49 L 278 49 Q 279 46 279 32 Z" fill="#39ff14" opacity="0.6" />
      </Svg>
      <Text style={[styles.text, { color: textColor }, textStyle]}>{children}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: {
    height: 50,
    justifyContent: 'center',
    alignItems: 'flex-start',
    marginBottom: 16,
    marginTop: 4,
  },
  splat: {
    ...StyleSheet.absoluteFillObject,
  },
  text: {
    fontSize: 22,
    fontFamily: FONTS.death,
    fontWeight: '900',
    letterSpacing: 2,
    paddingHorizontal: 14,
    paddingVertical: 4,
    paddingTop: 6,
    textShadowColor: 'rgba(0,0,0,0.8)',
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 2,
  },
});

export default SplatTitle;

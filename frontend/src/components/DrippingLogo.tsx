/**
 * DrippingLogo — the "THRASH KAN KIDZ" wordmark with slime-green drips.
 *
 * Pure SVG (no raster) so it scales sharply at any DPI and zero asset
 * bytes. Uses a single dripping-text effect: render text twice — once as
 * a glow halo, once crisp on top — and decorate with vertical drips
 * hanging off the baseline.
 */
import React from 'react';
import { View, StyleSheet, StyleProp, ViewStyle } from 'react-native';
import Svg, { Text as SvgText, Path, Defs, LinearGradient as SvgGrad, Stop } from 'react-native-svg';

interface Props {
  width?: number;
  height?: number;
  style?: StyleProp<ViewStyle>;
}

export const DrippingLogo: React.FC<Props> = ({ width = 280, height = 70, style }) => {
  return (
    <View style={[styles.wrap, style]}>
      <Svg width={width} height={height} viewBox="0 0 280 70">
        <Defs>
          <SvgGrad id="slimeGrad" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#c4ff5a" stopOpacity="1" />
            <Stop offset="0.5" stopColor="#5aff14" stopOpacity="1" />
            <Stop offset="1" stopColor="#1a8a02" stopOpacity="1" />
          </SvgGrad>
        </Defs>

        {/* Glow halo behind the text */}
        <SvgText
          x="140"
          y="32"
          textAnchor="middle"
          fontSize="22"
          fontWeight="900"
          fill="rgba(57, 255, 20, 0.35)"
          stroke="rgba(57, 255, 20, 0.55)"
          strokeWidth="4"
          letterSpacing="2"
        >
          THRASH KAN KIDZ
        </SvgText>

        {/* Crisp foreground text */}
        <SvgText
          x="140"
          y="32"
          textAnchor="middle"
          fontSize="22"
          fontWeight="900"
          fill="url(#slimeGrad)"
          stroke="#0a1a02"
          strokeWidth="0.5"
          letterSpacing="2"
        >
          THRASH KAN KIDZ
        </SvgText>

        {/* Slime drips dripping off the baseline — varied lengths */}
        <Path d="M 40 38 Q 41 50 42 56 L 39 56 Q 40 50 40 38 Z" fill="url(#slimeGrad)" />
        <Path d="M 78 39 Q 79 48 80 52 L 77 52 Q 78 48 78 39 Z" fill="url(#slimeGrad)" />
        <Path d="M 120 39 Q 121 56 122 64 L 119 64 Q 120 56 120 39 Z" fill="url(#slimeGrad)" />
        <Path d="M 160 38 Q 161 46 162 49 L 159 49 Q 160 46 160 38 Z" fill="url(#slimeGrad)" />
        <Path d="M 198 39 Q 199 55 200 60 L 197 60 Q 198 55 198 39 Z" fill="url(#slimeGrad)" />
        <Path d="M 236 38 Q 237 48 238 52 L 235 52 Q 236 48 236 38 Z" fill="url(#slimeGrad)" />
      </Svg>
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: {
    alignItems: 'center',
    justifyContent: 'center',
  },
});

export default DrippingLogo;

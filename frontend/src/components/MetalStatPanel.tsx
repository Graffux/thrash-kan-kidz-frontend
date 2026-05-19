/**
 * MetalStatPanel — rusted-metal framed stat tile for the Home grid.
 *
 * Visual: dark plate with green/rust trim, drip border bottom, icon at top
 * (Ionicons placeholder — Nano Banana custom art comes in Batch 2b),
 * big yellow value, slime-green uppercase label.
 *
 * Used in a 4-up flex row on Home (matches the mockup's MY CARDS /
 * COLLECTIONS / TRADES / DAILY STREAK grid).
 */
import React from 'react';
import { View, Text, StyleSheet, ViewStyle, StyleProp, Image, ImageSourcePropType } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface Props {
  /** Custom artwork (preferred). */
  iconSource?: ImageSourcePropType;
  /** Fallback Ionicons glyph if no custom source provided. */
  iconName?: keyof typeof Ionicons.glyphMap;
  iconColor?: string;
  value: string | number;
  label: string;
  style?: StyleProp<ViewStyle>;
}

export const MetalStatPanel: React.FC<Props> = ({
  iconSource,
  iconName,
  iconColor = '#c4ff5a',
  value,
  label,
  style,
}) => {
  return (
    <View style={[styles.panel, style]}>
      <View style={styles.iconWrap}>
        {iconSource ? (
          <Image source={iconSource} style={styles.iconImage} resizeMode="contain" />
        ) : iconName ? (
          <Ionicons name={iconName} size={28} color={iconColor} />
        ) : null}
      </View>
      <Text style={styles.value}>{value}</Text>
      <Text style={styles.label}>{label}</Text>
      {/* Drip strip across the bottom — green ooze trim */}
      <View style={styles.dripStrip} pointerEvents="none">
        <View style={[styles.drip, { left: '20%' }]} />
        <View style={[styles.drip, { left: '50%', height: 8 }]} />
        <View style={[styles.drip, { left: '78%', height: 4 }]} />
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  panel: {
    flex: 1,
    aspectRatio: 0.82,
    backgroundColor: '#1a1a14',
    borderRadius: 10,
    borderWidth: 2,
    borderColor: '#39ff14',
    paddingTop: 12,
    paddingHorizontal: 6,
    paddingBottom: 14,
    alignItems: 'center',
    justifyContent: 'flex-start',
    // Rivet trim — alternating top/bottom border colors fake an inset bevel
    borderTopColor: '#5aff5a',
    borderBottomColor: '#1a8a02',
    shadowColor: '#39ff14',
    shadowOpacity: 0.25,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 0 },
  },
  iconWrap: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(57, 255, 20, 0.12)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 6,
    borderWidth: 1,
    borderColor: 'rgba(57, 255, 20, 0.4)',
    overflow: 'hidden',
  },
  iconImage: {
    width: 40,
    height: 40,
  },
  value: {
    fontSize: 20,
    fontWeight: '900',
    color: '#ffd24a',
    textShadowColor: 'rgba(0,0,0,0.7)',
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 2,
  },
  label: {
    fontSize: 10,
    fontWeight: '800',
    color: '#9aff5a',
    letterSpacing: 1,
    textAlign: 'center',
    marginTop: 4,
  },
  dripStrip: {
    position: 'absolute',
    bottom: -1,
    left: 0,
    right: 0,
    height: 0,
  },
  drip: {
    position: 'absolute',
    top: -1,
    width: 3,
    height: 6,
    backgroundColor: '#39ff14',
    borderBottomLeftRadius: 2,
    borderBottomRightRadius: 2,
    shadowColor: '#39ff14',
    shadowOpacity: 0.8,
    shadowRadius: 3,
    shadowOffset: { width: 0, height: 0 },
  },
});

export default MetalStatPanel;

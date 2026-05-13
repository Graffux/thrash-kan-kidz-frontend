/**
 * MetalButton — reusable death-metal-themed CTA button.
 *
 * Wraps any tappable action with:
 *   - A neon glow border (color is rarity-driven via the `tone` prop)
 *   - A linear gradient surface (subtle darkness + sheen)
 *   - A spring-snap press animation (Moti)
 *   - Uppercase letter-spaced label inspired by metal album typography
 *
 * Used as a drop-in replacement for raw `<TouchableOpacity>` callouts
 * across Shop, Home, Trade, etc. Designed to be cost-effective: one
 * import, one component, applied 20+ places.
 */
import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, ViewStyle, TextStyle, View } from 'react-native';
import { MotiView } from 'moti';
import { LinearGradient } from 'expo-linear-gradient';

export type MetalButtonTone = 'hellfire' | 'toxic' | 'blacklight' | 'magma' | 'gold';

interface Props {
  label: string;
  onPress: () => void;
  tone?: MetalButtonTone;
  disabled?: boolean;
  fullWidth?: boolean;
  size?: 'sm' | 'md' | 'lg';
  testID?: string;
  style?: ViewStyle;
  labelStyle?: TextStyle;
  icon?: React.ReactNode;
}

const TONE_COLORS: Record<MetalButtonTone, { glow: string; gradient: [string, string]; text: string }> = {
  hellfire: { glow: '#FF003C', gradient: ['#3A0010', '#FF003C'], text: '#FFFFFF' },
  toxic: { glow: '#39FF14', gradient: ['#0A2A0A', '#39FF14'], text: '#050505' },
  blacklight: { glow: '#B026FF', gradient: ['#1F0033', '#B026FF'], text: '#FFFFFF' },
  magma: { glow: '#FF5F00', gradient: ['#2A1000', '#FF5F00'], text: '#050505' },
  gold: { glow: '#C5A059', gradient: ['#2A1F0A', '#C5A059'], text: '#050505' },
};

const SIZE_PADDING = {
  sm: { paddingVertical: 8, paddingHorizontal: 14, fontSize: 13 },
  md: { paddingVertical: 12, paddingHorizontal: 22, fontSize: 16 },
  lg: { paddingVertical: 16, paddingHorizontal: 28, fontSize: 20 },
};

export const MetalButton: React.FC<Props> = ({
  label,
  onPress,
  tone = 'hellfire',
  disabled = false,
  fullWidth = false,
  size = 'md',
  testID,
  style,
  labelStyle,
  icon,
}) => {
  const [pressed, setPressed] = useState(false);
  const toneCfg = TONE_COLORS[tone];
  const sizing = SIZE_PADDING[size];

  return (
    <Pressable
      onPress={disabled ? undefined : onPress}
      onPressIn={() => !disabled && setPressed(true)}
      onPressOut={() => setPressed(false)}
      disabled={disabled}
      style={[
        fullWidth && { alignSelf: 'stretch' },
        disabled && { opacity: 0.45 },
        style,
      ]}
      data-testid={testID || 'metal-button'}
    >
      <MotiView
        animate={{
          scale: pressed ? 0.96 : 1,
          shadowOpacity: pressed ? 1 : 0.75,
        }}
        transition={{ type: 'spring', damping: 14, stiffness: 220, mass: 0.6 }}
        style={[
          styles.outer,
          {
            borderColor: toneCfg.glow,
            shadowColor: toneCfg.glow,
          },
        ]}
      >
        <LinearGradient
          colors={toneCfg.gradient}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={[
            styles.inner,
            {
              paddingVertical: sizing.paddingVertical,
              paddingHorizontal: sizing.paddingHorizontal,
            },
          ]}
        >
          <View style={styles.row}>
            {icon ? <View style={styles.iconWrap}>{icon}</View> : null}
            <Text
              style={[
                styles.label,
                { color: toneCfg.text, fontSize: sizing.fontSize },
                labelStyle,
              ]}
              numberOfLines={1}
            >
              {label}
            </Text>
          </View>
        </LinearGradient>
      </MotiView>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  outer: {
    borderRadius: 6,
    borderWidth: 2,
    backgroundColor: '#050505',
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 14,
    elevation: 8,
    overflow: 'hidden',
  },
  inner: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconWrap: {
    marginRight: 8,
  },
  label: {
    fontWeight: '900',
    letterSpacing: 2,
    textTransform: 'uppercase',
  },
});

export default MetalButton;

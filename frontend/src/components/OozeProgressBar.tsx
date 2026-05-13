/**
 * OozeProgressBar — death-metal progress bar with neon ooze fill.
 *
 * Replaces flat `<View>` progress bars across the app (Series completion,
 * Goal progress, Variant collection 4/4). The fill animates in via Moti
 * timing transition so unlocking progress feels like toxic slime crawling
 * up a glass tube.
 *
 * Configurable `tone` matches the death-metal palette:
 *   - toxic  → green slime (default, for series progress)
 *   - hellfire → blood red (for rare/dangerous progress)
 *   - blacklight → neon purple (for variants)
 *   - gold → tarnished gold (for coin / achievement milestones)
 */
import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';
import { MotiView } from 'moti';

export type OozeTone = 'toxic' | 'hellfire' | 'blacklight' | 'gold';

interface Props {
  value: number;          // numerator (e.g. 12)
  max: number;            // denominator (e.g. 16)
  tone?: OozeTone;
  label?: string;         // optional override (defaults to "12 / 16")
  height?: number;
  showLabel?: boolean;
  style?: ViewStyle;
  testID?: string;
}

const TONE_MAP: Record<OozeTone, { glow: string; fill: string; track: string }> = {
  toxic: { glow: '#39FF14', fill: '#39FF14', track: '#0A1A0A' },
  hellfire: { glow: '#FF003C', fill: '#FF003C', track: '#1A0008' },
  blacklight: { glow: '#B026FF', fill: '#B026FF', track: '#15001F' },
  gold: { glow: '#C5A059', fill: '#FFD700', track: '#1A1408' },
};

export const OozeProgressBar: React.FC<Props> = ({
  value,
  max,
  tone = 'toxic',
  label,
  height = 18,
  showLabel = true,
  style,
  testID,
}) => {
  const safeMax = Math.max(1, max);
  const pct = Math.min(100, Math.max(0, (value / safeMax) * 100));
  const cfg = TONE_MAP[tone];
  const displayLabel = label ?? `${value} / ${max}`;

  return (
    <View style={[styles.wrap, style]} data-testid={testID || 'ooze-progress-bar'}>
      <View
        style={[
          styles.track,
          {
            height,
            backgroundColor: cfg.track,
            borderColor: cfg.glow,
            shadowColor: cfg.glow,
          },
        ]}
      >
        <MotiView
          from={{ width: '0%' }}
          animate={{ width: `${pct}%` }}
          transition={{ type: 'timing', duration: 900 }}
          style={[
            styles.fill,
            {
              backgroundColor: cfg.fill,
              shadowColor: cfg.glow,
            },
          ]}
        />
        {/* Subtle sheen highlight to read as wet/glossy ooze */}
        <View pointerEvents="none" style={styles.sheen} />
      </View>
      {showLabel && (
        <Text style={[styles.label, { color: cfg.glow, textShadowColor: cfg.glow }]}>
          {displayLabel}
        </Text>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: {
    width: '100%',
  },
  track: {
    width: '100%',
    borderRadius: 4,
    borderWidth: 1.5,
    overflow: 'hidden',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.6,
    shadowRadius: 6,
    elevation: 4,
    position: 'relative',
  },
  fill: {
    height: '100%',
    opacity: 0.92,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 1,
    shadowRadius: 8,
  },
  sheen: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: '40%',
    backgroundColor: 'rgba(255,255,255,0.08)',
  },
  label: {
    marginTop: 4,
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1,
    textAlign: 'right',
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 4,
  },
});

export default OozeProgressBar;

/**
 * CoinGainPop — floating "+50" pop on the Home screen header.
 *
 * Renders an absolutely positioned floating text element above the coin
 * balance whenever it increases. Uses Moti for a one-shot animation:
 *   - Slide up 60px
 *   - Scale 1 → 1.4 → 0.95 (overshoot then settle)
 *   - Fade out at the end
 *   - Auto-unmount itself after 1100ms to keep React tree clean
 *
 * Trigger by mounting <CoinGainPop amount={...} key={uniqueId} /> — change
 * the `key` (use `Date.now()`) every time you want a new pop, so React
 * remounts and the animation re-fires.
 */
import React, { useEffect, useState } from 'react';
import { Text, StyleSheet, ViewStyle } from 'react-native';
import { MotiText } from 'moti';

interface Props {
  amount: number;
  tone?: 'gold' | 'medal';     // 'gold' for coins, 'medal' for goals
  durationMs?: number;
  style?: ViewStyle;
}

const TONE_COLOR: Record<NonNullable<Props['tone']>, string> = {
  gold: '#FFD700',
  medal: '#39FF14',
};

export const CoinGainPop: React.FC<Props> = ({ amount, tone = 'gold', durationMs = 1100, style }) => {
  // Self-unmount after the animation finishes. Parent doesn't need to
  // track lifecycle — just bump the key to fire another.
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => setVisible(false), durationMs);
    return () => clearTimeout(t);
  }, [durationMs]);

  if (!visible) return null;

  const color = TONE_COLOR[tone];
  const sign = amount >= 0 ? '+' : '';

  return (
    <MotiText
      from={{ translateY: 0, opacity: 0, scale: 0.6 }}
      animate={{ translateY: -60, opacity: 1, scale: 1.4 }}
      // Two-stage feel: snappy entrance, slow fade. Moti picks the second
      // animate via a sequence, so we use transition with overshoot.
      transition={{
        type: 'spring',
        damping: 9,
        stiffness: 180,
        mass: 0.6,
        opacity: { type: 'timing', duration: durationMs * 0.85 },
        translateY: { type: 'timing', duration: durationMs },
      }}
      style={[
        styles.pop,
        {
          color,
          textShadowColor: color,
        },
        style,
      ]}
    >
      {sign}{Math.abs(amount)}{tone === 'gold' ? ' COINS' : ' MEDALS'}
    </MotiText>
  );
};

const styles = StyleSheet.create({
  pop: {
    position: 'absolute',
    top: 0,
    alignSelf: 'center',
    fontSize: 22,
    fontWeight: '900',
    letterSpacing: 1.5,
    textTransform: 'uppercase',
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 12,
    pointerEvents: 'none' as any,
    zIndex: 999,
  },
});

export default CoinGainPop;

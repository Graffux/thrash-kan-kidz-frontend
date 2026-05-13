/**
 * PackRevealWrapper — wraps a card reveal in a juicy choreographed
 * entrance animation.
 *
 * Animation timeline (~900ms total):
 *   0–120ms   : Tremble (subtle X/Y wobble, builds anticipation)
 *   120–240ms : Flash overlay (white, 0.7 → 0 alpha)
 *   240–600ms : Scale spring (0.5 → 1.15 → 1.0)
 *   600ms+    : Rests at scale 1.0 with pulsing glow IF rarity != common
 *
 * Reused for: pack reveal in Shop, trade-in win in Collection,
 * Daily Wheel card prizes, Card Picker wins. One choreography to rule
 * all reveal moments.
 *
 * @prop rarity — drives the rest-state glow color. 'common' = no glow.
 * @prop animationKey — change this (e.g. card.id) to retrigger the
 *       full animation when the wrapped content changes.
 */
import React, { useEffect, useState } from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import { MotiView } from 'moti';

type Rarity = 'common' | 'rare' | 'epic';

interface Props {
  rarity?: Rarity;
  animationKey?: string | number;  // bump to retrigger
  children: React.ReactNode;
  width: number;
  height: number;
  style?: ViewStyle;
}

const RARITY_GLOW: Record<Rarity, string | null> = {
  common: null,
  rare: '#FFD700',     // gold halo for series-completion rewards (rare)
  epic: '#FF003C',     // hellfire halo for epic rewards (Sean Kill-Again, Alien Dubin)
};

export const PackRevealWrapper: React.FC<Props> = ({
  rarity = 'common',
  animationKey,
  children,
  width,
  height,
  style,
}) => {
  const [stage, setStage] = useState<'tremble' | 'flash' | 'scale' | 'rest'>('tremble');
  const glow = RARITY_GLOW[rarity];

  // Drive the staged choreography by stepping through stages with
  // setTimeout. Each stage maps to a different `animate` config below.
  // Resets every time `animationKey` changes (e.g. next pack card).
  useEffect(() => {
    setStage('tremble');
    const t1 = setTimeout(() => setStage('flash'), 120);
    const t2 = setTimeout(() => setStage('scale'), 240);
    const t3 = setTimeout(() => setStage('rest'), 600);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, [animationKey]);

  // Choreography per stage. We split scale + translate into the inner
  // wrapper so a static parent can host shadow without re-rendering.
  const motiAnimate = (() => {
    switch (stage) {
      case 'tremble':
        return { scale: 0.5, translateX: -3, translateY: -2, rotate: '-2deg' };
      case 'flash':
        return { scale: 0.6, translateX: 3, translateY: 2, rotate: '2deg' };
      case 'scale':
        return { scale: 1.15, translateX: 0, translateY: 0, rotate: '0deg' };
      case 'rest':
      default:
        return { scale: 1, translateX: 0, translateY: 0, rotate: '0deg' };
    }
  })();

  return (
    <View
      style={[
        styles.wrap,
        { width, height },
        glow && {
          shadowColor: glow,
          shadowOpacity: stage === 'rest' ? 0.95 : 0,
          shadowRadius: 22,
          shadowOffset: { width: 0, height: 0 },
          elevation: 14,
        },
        style,
      ]}
    >
      <MotiView
        animate={motiAnimate}
        transition={{
          type: 'spring',
          damping: stage === 'scale' ? 8 : 14,
          stiffness: stage === 'scale' ? 180 : 320,
          mass: 0.7,
        }}
        style={styles.fill}
      >
        {children}
      </MotiView>

      {/* White flash overlay — sits on top during flash stage only. */}
      <MotiView
        pointerEvents="none"
        animate={{ opacity: stage === 'flash' ? 0.75 : 0 }}
        transition={{ type: 'timing', duration: 220 }}
        style={[styles.flashOverlay, { backgroundColor: '#FFFFFF' }]}
      />

      {/* Resting glow halo — visible only after the entrance settles. */}
      {glow && stage === 'rest' && (
        <MotiView
          pointerEvents="none"
          from={{ opacity: 0.4, scale: 1 }}
          animate={{ opacity: 0.95, scale: 1.05 }}
          transition={{ type: 'timing', duration: 1100, loop: true }}
          style={[
            styles.glowHalo,
            { borderColor: glow, shadowColor: glow },
          ]}
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: {
    position: 'relative',
    alignItems: 'center',
    justifyContent: 'center',
  },
  fill: {
    width: '100%',
    height: '100%',
  },
  flashOverlay: {
    ...StyleSheet.absoluteFillObject,
  },
  glowHalo: {
    ...StyleSheet.absoluteFillObject,
    borderRadius: 8,
    borderWidth: 2,
    shadowOpacity: 0.8,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 0 },
  },
});

export default PackRevealWrapper;

import React from 'react';
import { Animated, Image, StyleSheet, View } from 'react-native';

type PackBurstProps = {
  visible: boolean;
  packImage: string;
  burstAnim: Animated.Value;
};

const FRAGMENTS = [
  { x: -120, y: -90, r: '-35deg', w: 28, h: 18 },
  { x: 110, y: -100, r: '42deg', w: 24, h: 20 },
  { x: -95, y: 65, r: '25deg', w: 22, h: 16 },
  { x: 125, y: 70, r: '-28deg', w: 26, h: 18 },
  { x: -45, y: -135, r: '60deg', w: 18, h: 14 },
  { x: 50, y: -130, r: '-55deg', w: 20, h: 14 },
];

export default function PackBurst({ visible, packImage, burstAnim }: PackBurstProps) {
  if (!visible) return null;

  const leftX = burstAnim.interpolate({ inputRange: [0, 1], outputRange: [0, -95] });
  const rightX = burstAnim.interpolate({ inputRange: [0, 1], outputRange: [0, 95] });
  const halfOpacity = burstAnim.interpolate({ inputRange: [0, 0.8, 1], outputRange: [1, 1, 0] });
  const glowScale = burstAnim.interpolate({ inputRange: [0, 1], outputRange: [0.4, 2.4] });
  const glowOpacity = burstAnim.interpolate({ inputRange: [0, 0.35, 1], outputRange: [0, 0.9, 0] });

  return (
    <View pointerEvents="none" style={styles.overlay}>
      <Animated.View style={[styles.energyGlow, { opacity: glowOpacity, transform: [{ scale: glowScale }] }]} />

      <Animated.View style={[styles.leftHalf, { opacity: halfOpacity, transform: [{ translateX: leftX }, { rotate: '-14deg' }] }]}>
        <Image source={{ uri: packImage }} style={styles.leftImage} resizeMode="cover" />
      </Animated.View>

      <Animated.View style={[styles.rightHalf, { opacity: halfOpacity, transform: [{ translateX: rightX }, { rotate: '14deg' }] }]}>
        <Image source={{ uri: packImage }} style={styles.rightImage} resizeMode="cover" />
      </Animated.View>

      {FRAGMENTS.map((f, idx) => {
        const tx = burstAnim.interpolate({ inputRange: [0, 1], outputRange: [0, f.x] });
        const ty = burstAnim.interpolate({ inputRange: [0, 1], outputRange: [0, f.y] });
        const op = burstAnim.interpolate({ inputRange: [0, 0.75, 1], outputRange: [1, 1, 0] });

        return (
          <Animated.View
            key={`fragment-${idx}`}
            style={[
              styles.fragment,
              {
                width: f.w,
                height: f.h,
                opacity: op,
                transform: [{ translateX: tx }, { translateY: ty }, { rotate: f.r }],
              },
            ]}
          />
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    position: 'absolute',
    width: 220,
    height: 280,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 20,
  },
  energyGlow: {
    position: 'absolute',
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: 'rgba(170, 0, 255, 0.85)',
    shadowColor: '#b700ff',
    shadowOpacity: 1,
    shadowRadius: 28,
  },
  leftHalf: {
    position: 'absolute',
    width: 90,
    height: 240,
    overflow: 'hidden',
    left: 20,
    borderTopLeftRadius: 12,
    borderBottomLeftRadius: 12,
  },
  rightHalf: {
    position: 'absolute',
    width: 90,
    height: 240,
    overflow: 'hidden',
    right: 20,
    borderTopRightRadius: 12,
    borderBottomRightRadius: 12,
  },
  leftImage: {
    width: 180,
    height: 240,
  },
  rightImage: {
    width: 180,
    height: 240,
    transform: [{ translateX: -90 }],
  },
  fragment: {
    position: 'absolute',
    backgroundColor: '#FFD700',
    borderWidth: 1,
    borderColor: '#111',
  },
});

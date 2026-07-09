import React, { useEffect, useRef } from 'react';
import { Animated, Easing, Image, Text, View } from 'react-native';

const PACK_W = 330;
const PACK_H = 470;
const HALF_W = PACK_W / 2;

type PackEruptionProps = {
  visible: boolean;
  packImage: string;
  cards?: { card: any; is_duplicate: boolean }[];
  onAnimationComplete?: () => void;
};

export default function PackEruption({
  visible,
  packImage,
  cards = [],
  onAnimationComplete,
}: PackEruptionProps) {
  const slam = useRef(new Animated.Value(0)).current;
  const shakeX = useRef(new Animated.Value(0)).current;
  const rip = useRef(new Animated.Value(0)).current;
  const burst = useRef(new Animated.Value(0)).current;
  const fade = useRef(new Animated.Value(1)).current;
  const impact = useRef(new Animated.Value(0)).current;
  const cardsOut = useRef(new Animated.Value(0)).current;

  const slamScale = slam.interpolate({
    inputRange: [0, 0.7, 1],
    outputRange: [0.45, 1.12, 1],
  });

  const impactOpacity = impact.interpolate({
    inputRange: [0, 0.25, 1],
    outputRange: [0, 0.9, 0],
  });

  const impactScale = impact.interpolate({
    inputRange: [0, 1],
    outputRange: [0.25, 2.1],
  });

  const heroCardY = cardsOut.interpolate({
  inputRange: [0, 0.12, 0.35, 0.65, 1],
  outputRange: [260, 170, 20, -140, -235],
});

const heroCardScale = cardsOut.interpolate({
  inputRange: [0, 0.08, 0.3, 0.65, 1],
  outputRange: [0.02, 0.18, 0.95, 1.45, 1.12],
});

const heroCardRotate = cardsOut.interpolate({
  inputRange: [0, 0.4, 1],
  outputRange: ['-18deg', '3deg', '0deg'],
});
const heroCardOpacity = cardsOut.interpolate({
  inputRange: [0, 0.15, 1],
  outputRange: [0, 1, 1],
});

  const leftX = rip.interpolate({
    inputRange: [0, 1],
    outputRange: [0, -260],
  });

  const rightX = rip.interpolate({
    inputRange: [0, 1],
    outputRange: [0, 260],
  });

  const leftRot = rip.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '-40deg'],
  });

  const rightRot = rip.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '40deg'],
  });

  const burstScale = burst.interpolate({
    inputRange: [0, 1],
    outputRange: [0.2, 3.2],
  });

  const burstOpacity = burst.interpolate({
    inputRange: [0, 0.25, 1],
    outputRange: [0, 1, 0],
  });

  useEffect(() => {
    if (!visible) return;

    slam.setValue(0);
    shakeX.setValue(0);
    rip.setValue(0);
    burst.setValue(0);
    fade.setValue(1);
    impact.setValue(0);
    cardsOut.setValue(0);

    Animated.sequence([
      Animated.parallel([
        Animated.timing(slam, {
          toValue: 1,
          duration: 260,
          easing: Easing.out(Easing.back(1.8)),
          useNativeDriver: true,
        }),
        Animated.timing(impact, {
          toValue: 1,
          duration: 260,
          easing: Easing.out(Easing.quad),
          useNativeDriver: true,
        }),
      ]),

      Animated.loop(
  Animated.sequence([
    Animated.timing(shakeX, {
      toValue: -24,
      duration: 28,
      useNativeDriver: true,
    }),
    Animated.timing(shakeX, {
      toValue: 24,
      duration: 28,
      useNativeDriver: true,
    }),
    Animated.timing(shakeX, {
      toValue: -18,
      duration: 28,
      useNativeDriver: true,
    }),
    Animated.timing(shakeX, {
      toValue: 18,
      duration: 28,
      useNativeDriver: true,
    }),
    Animated.timing(shakeX, {
      toValue: -12,
      duration: 24,
      useNativeDriver: true,
    }),
    Animated.timing(shakeX, {
      toValue: 12,
      duration: 24,
      useNativeDriver: true,
    }),
    Animated.timing(shakeX, {
      toValue: 0,
      duration: 20,
      useNativeDriver: true,
    }),
  ]),
  { iterations: 6 }
),

      Animated.parallel([
        Animated.timing(rip, {
          toValue: 1,
          duration: 520,
          easing: Easing.out(Easing.cubic),
          useNativeDriver: true,
        }),
        Animated.timing(burst, {
          toValue: 1,
          duration: 520,
          easing: Easing.out(Easing.cubic),
          useNativeDriver: true,
        }),
        Animated.timing(cardsOut, {
          toValue: 1,
          duration: 620,
          easing: Easing.out(Easing.back(1.3)),
          useNativeDriver: true,
}),
      ]),

      Animated.delay(700),

Animated.timing(fade, {
  toValue: 0,
  duration: 180,
  easing: Easing.out(Easing.quad),
  useNativeDriver: true,
}),
    ]).start(({ finished }) => {
      if (finished) {
        onAnimationComplete?.();
      }
    });
  }, [visible]);
  if (!visible) return null;

  return (
    <View
      pointerEvents="none"
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: 'rgba(0,0,0,0.82)',
        zIndex: 999,
      }}
    >
      <Animated.Text
  style={{
    color: '#39ff14',
    fontSize: 34,
    fontWeight: '900',
    letterSpacing: 2,
    textShadowColor: '#39ff14',
    textShadowRadius: 18,
    opacity: fade,
    transform: [{ scale: slamScale }],
  }}
>
  RIP IT OPEN
</Animated.Text>

      <Animated.View
        pointerEvents="none"
        style={{
          position: 'absolute',
          width: 180,
          height: 180,
          borderRadius: 999,
          backgroundColor: '#39ff14',
          opacity: impactOpacity,
          transform: [{ scale: impactScale }],
        }}
      />

      <Animated.View
        style={{
          width: PACK_W,
          height: PACK_H,
          marginTop: 12,
          position: 'relative',
          opacity: fade,
          transform: [{ translateX: shakeX }, { scale: slamScale }],
        }}
      >
        <Animated.View
          pointerEvents="none"
          style={{
            position: 'absolute',
            top: PACK_H * 0.22,
            left: PACK_W * 0.15,
            width: PACK_W * 0.7,
            height: PACK_H * 0.5,
            borderRadius: 999,
            backgroundColor: '#39ff14',
            opacity: burstOpacity,
            transform: [{ scale: burstScale }],
          }}
        />

        {cards.slice(0, 3).map((pull, index) => {
  const startX = 0;
 const endX = index === 0 ? -170 : index === 1 ? 0 : 170;

  const cardX = cardsOut.interpolate({
    inputRange: [0, 1],
    outputRange: [startX, endX],
  });

  return (
    <Animated.Image
      key={index}
      source={{ uri: pull.card.front_image_url }}
      resizeMode="contain"
      style={{
        position: 'absolute',
        top: PACK_H * 0.30,
        left: PACK_W * 0.14,
        width: PACK_W * 0.58,
        height: PACK_H * 0.64,
        opacity: heroCardOpacity,
        transform: [
          { translateX: cardX },
          { translateY: heroCardY },
          { scale: heroCardScale },
        ],
      }}
    />
  );
})}
        <Animated.View
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: HALF_W,
            height: PACK_H,
            overflow: 'hidden',
            transform: [{ translateX: leftX }, { rotate: leftRot }],
          }}
        >
          <Image
            source={{ uri: packImage }}
            resizeMode="stretch"
            style={{
              width: PACK_W,
              height: PACK_H,
            }}
          />
        </Animated.View>

        <Animated.View
          style={{
            position: 'absolute',
            top: 0,
            left: HALF_W,
            width: HALF_W,
            height: PACK_H,
            overflow: 'hidden',
            transform: [{ translateX: rightX }, { rotate: rightRot }],
          }}
        >
          <Image
            source={{ uri: packImage }}
            resizeMode="stretch"
            style={{
              width: PACK_W,
              height: PACK_H,
              marginLeft: -HALF_W,
            }}
          />
        </Animated.View>
      </Animated.View>
    </View>
  );
}
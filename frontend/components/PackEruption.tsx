import React, { useEffect, useRef } from 'react';
import {
  Animated,
  Dimensions,
  Easing,
  Image,
} from 'react-native';

const PACK_W = 330;
const PACK_H = 470;
const TOP_H = 82;
const { width: SCREEN_W, height: SCREEN_H } = Dimensions.get('window');

type PackPull = {
  card: {
    id?: string;
    front_image_url?: string;
  };
  is_duplicate: boolean;
};

type PackOrigin = {
  x: number;
  y: number;
  width: number;
  height: number;
};

type PackEruptionProps = {
  visible: boolean;
  packImage: string;
  origin?: PackOrigin | null;
  cards?: PackPull[];
  onAnimationComplete?: () => void;
};

export default function PackEruption({
  visible,
  packImage,
  origin,
  cards = [],
  onAnimationComplete,
}: PackEruptionProps) {
  const intro = useRef(new Animated.Value(0)).current;
  const shakeX = useRef(new Animated.Value(0)).current;
  const shakeRotate = useRef(new Animated.Value(0)).current;
  const tear = useRef(new Animated.Value(0)).current;
  const burst = useRef(new Animated.Value(0)).current;
  const stackOut = useRef(new Animated.Value(0)).current;
  const fanOut = useRef(new Animated.Value(0)).current;
  const flash = useRef(new Animated.Value(0)).current;
  const fade = useRef(new Animated.Value(1)).current;

  const targetCenterX = SCREEN_W / 2;
  const targetCenterY = SCREEN_H / 2;

  const originCenterX = origin
    ? origin.x + origin.width / 2
    : targetCenterX;

  const originCenterY = origin
    ? origin.y + origin.height / 2
    : targetCenterY;

  const startTranslateX = originCenterX - targetCenterX;
  const startTranslateY = originCenterY - targetCenterY;
  const startScaleX = origin ? origin.width / PACK_W : 0.55;
  const startScaleY = origin ? origin.height / PACK_H : 0.55;

  const originX = intro.interpolate({
    inputRange: [0, 1],
    outputRange: [startTranslateX, 0],
  });

  const originY = intro.interpolate({
    inputRange: [0, 1],
    outputRange: [startTranslateY, -10],
  });

  const originScaleX = intro.interpolate({
    inputRange: [0, 0.8, 1],
    outputRange: [startScaleX, 1.06, 1.02],
  });

  const originScaleY = intro.interpolate({
    inputRange: [0, 0.8, 1],
    outputRange: [startScaleY, 1.06, 1.02],
  });

  const overlayOpacity = intro.interpolate({
    inputRange: [0, 0.35, 1],
    outputRange: [0, 0.7, 1],
  });

  const packRotate = shakeRotate.interpolate({
    inputRange: [-1, 0, 1],
    outputRange: ['-3deg', '0deg', '3deg'],
  });

  const topY = tear.interpolate({
    inputRange: [0, 0.15, 1],
    outputRange: [0, -12, -310],
  });

  const topX = tear.interpolate({
    inputRange: [0, 0.4, 1],
    outputRange: [0, 40, 165],
  });

  const topRotate = tear.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '58deg'],
  });

  const topOpacity = tear.interpolate({
    inputRange: [0, 0.62, 1],
    outputRange: [1, 0.9, 0],
  });

  const bodyY = tear.interpolate({
    inputRange: [0, 0.45, 1],
    outputRange: [0, 18, 135],
  });

  const bodyRotate = tear.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '-10deg'],
  });

  const burstScale = burst.interpolate({
    inputRange: [0, 0.25, 1],
    outputRange: [0.12, 1.4, 4],
  });

  const burstOpacity = burst.interpolate({
    inputRange: [0, 0.15, 0.72, 1],
    outputRange: [0, 1, 0.65, 0],
  });

  const flashOpacity = flash.interpolate({
    inputRange: [0, 0.2, 1],
    outputRange: [0, 0.9, 0],
  });

  const stackY = stackOut.interpolate({
    inputRange: [0, 0.2, 0.65, 1],
    outputRange: [185, 120, -145, -205],
  });

  const stackScale = stackOut.interpolate({
    inputRange: [0, 0.18, 0.7, 1],
    outputRange: [0.08, 0.28, 1.15, 1],
  });

  const stackOpacity = stackOut.interpolate({
    inputRange: [0, 0.12, 0.28, 1],
    outputRange: [0, 0, 1, 1],
  });

  useEffect(() => {
    if (!visible) return;

    intro.setValue(0);
    shakeX.setValue(0);
    shakeRotate.setValue(0);
    tear.setValue(0);
    burst.setValue(0);
    stackOut.setValue(0);
    fanOut.setValue(0);
    flash.setValue(0);
    fade.setValue(1);

    const shakeSequence = Animated.sequence([
      Animated.parallel([
        Animated.timing(shakeX, {
          toValue: -22,
          duration: 45,
          useNativeDriver: true,
        }),
        Animated.timing(shakeRotate, {
          toValue: -1,
          duration: 45,
          useNativeDriver: true,
        }),
      ]),
      Animated.parallel([
        Animated.timing(shakeX, {
          toValue: 22,
          duration: 45,
          useNativeDriver: true,
        }),
        Animated.timing(shakeRotate, {
          toValue: 1,
          duration: 45,
          useNativeDriver: true,
        }),
      ]),
      Animated.parallel([
        Animated.timing(shakeX, {
          toValue: 0,
          duration: 38,
          useNativeDriver: true,
        }),
        Animated.timing(shakeRotate, {
          toValue: 0,
          duration: 38,
          useNativeDriver: true,
        }),
      ]),
    ]);

    Animated.sequence([
      Animated.timing(intro, {
        toValue: 1,
        duration: 420,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),

      Animated.loop(shakeSequence, { iterations: 4 }),

      Animated.parallel([
        Animated.timing(tear, {
          toValue: 1,
          duration: 550,
          easing: Easing.out(Easing.exp),
          useNativeDriver: true,
        }),
        Animated.timing(burst, {
          toValue: 1,
          duration: 650,
          easing: Easing.out(Easing.cubic),
          useNativeDriver: true,
        }),
        Animated.sequence([
          Animated.timing(flash, {
            toValue: 1,
            duration: 90,
            useNativeDriver: true,
          }),
          Animated.timing(flash, {
            toValue: 0,
            duration: 280,
            useNativeDriver: true,
          }),
        ]),
      ]),

      Animated.delay(250),

      Animated.timing(stackOut, {
        toValue: 1,
        duration: 700,
        easing: Easing.out(Easing.back(1.6)),
        useNativeDriver: true,
      }),

      Animated.delay(180),

      Animated.timing(fanOut, {
        toValue: 1,
        duration: 450,
        easing: Easing.out(Easing.back(1.25)),
        useNativeDriver: true,
      }),

      Animated.delay(450),

      Animated.timing(fade, {
        toValue: 0,
        duration: 260,
        easing: Easing.in(Easing.quad),
        useNativeDriver: true,
      }),
    ]).start(({ finished }) => {
      if (finished) {
        onAnimationComplete?.();
      }
    });
  }, [
    visible,
    intro,
    shakeX,
    shakeRotate,
    tear,
    burst,
    stackOut,
    fanOut,
    flash,
    fade,
    onAnimationComplete,
  ]);

  if (!visible) return null;

  return (
    <Animated.View
      pointerEvents="none"
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: 'rgba(0,0,0,0.9)',
        opacity: Animated.multiply(fade, overlayOpacity),
        zIndex: 999,
      }}
    >
      <Animated.View
        style={{
          position: 'absolute',
          width: 230,
          height: 230,
          borderRadius: 999,
          backgroundColor: '#39ff14',
          opacity: burstOpacity,
          transform: [{ scale: burstScale }],
        }}
      />

      <Animated.View
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: '#ffffff',
          opacity: flashOpacity,
        }}
      />

      <Animated.View
        style={{
          width: PACK_W,
          height: PACK_H,
          position: 'relative',
          transform: [
            { translateX: originX },
            { translateY: originY },
            { scaleX: originScaleX },
            { scaleY: originScaleY },
            { translateX: shakeX },
            { rotate: packRotate },
          ],
        }}
      >
        {cards.slice(0, 3).map((pull, index) => {
          const finalX = index === 0 ? -145 : index === 2 ? 145 : 0;
          const finalRotate =
            index === 0 ? '-9deg' : index === 2 ? '9deg' : '0deg';

          const cardX = fanOut.interpolate({
            inputRange: [0, 1],
            outputRange: [0, finalX],
          });

          const cardRotate = fanOut.interpolate({
            inputRange: [0, 1],
            outputRange: ['0deg', finalRotate],
          });

          return (
            <Animated.Image
              key={pull.card.id || index}
              source={{ uri: pull.card.front_image_url }}
              resizeMode="contain"
              style={{
                position: 'absolute',
                top: TOP_H - 5,
                left: PACK_W * 0.14,
                width: PACK_W * 0.72,
                height: PACK_H * 0.7,
                opacity: stackOpacity,
                zIndex: 30 - index,
                transform: [
                  { translateX: cardX },
                  { translateY: stackY },
                  { rotate: cardRotate },
                  { scale: stackScale },
                ],
              }}
            />
          );
        })}

        <Animated.View
          style={{
            position: 'absolute',
            top: TOP_H - 8,
            left: 22,
            width: PACK_W - 44,
            height: 90,
            borderRadius: 999,
            backgroundColor: '#39ff14',
            opacity: burstOpacity,
            transform: [{ scale: burstScale }],
            zIndex: 6,
          }}
        />

        <Animated.View
          style={{
            position: 'absolute',
            top: TOP_H,
            left: 0,
            width: PACK_W,
            height: PACK_H - TOP_H,
            overflow: 'hidden',
            zIndex: 3,
            transform: [
              { translateY: bodyY },
              { rotate: bodyRotate },
            ],
          }}
        >
          <Image
            source={{ uri: packImage }}
            resizeMode="stretch"
            style={{
              width: PACK_W,
              height: PACK_H,
              marginTop: -TOP_H,
            }}
          />
        </Animated.View>

        <Animated.View
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: PACK_W,
            height: TOP_H,
            overflow: 'hidden',
            opacity: topOpacity,
            zIndex: 12,
            transform: [
              { translateX: topX },
              { translateY: topY },
              { rotate: topRotate },
            ],
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
      </Animated.View>
    </Animated.View>
  );
}

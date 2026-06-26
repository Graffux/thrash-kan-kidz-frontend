import React, { useEffect, useRef } from 'react';
import {
  Animated,
  Dimensions,
  Image,
  Modal,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';

type RewardTheme = 'daily' | 'series' | 'hidden' | 'epic' | 'generic';

type RewardCard = {
  id?: string;
  name?: string;
  rarity?: string;
  front_image_url?: string;
  back_image_url?: string;
  is_daily_reward?: boolean;
};

type RewardRevealProps = {
  visible: boolean;
  theme?: RewardTheme;
  card?: RewardCard | null;
  title?: string;
  subtitle?: string;
  footer?: string;
  buttonText?: string;
  onClose: () => void;
};

const { width } = Dimensions.get('window');
const CARD_W = Math.min(292, width * 0.78);
const CARD_H = CARD_W * 1.42;

const THEME = {
  daily: {
    eyebrow: '? DAILY CHALLENGE COMPLETE ?',
    title: 'SPECIAL REWARD UNLOCKED',
    accent: '#ffd24a',
    glow: 'rgba(255, 210, 74, 0.35)',
    bg: 'rgba(0,0,0,0.92)',
  },
  series: {
    eyebrow: '?? SERIES MASTERED ??',
    title: 'SERIES REWARD UNLOCKED',
    accent: '#ff3b30',
    glow: 'rgba(255, 59, 48, 0.35)',
    bg: 'rgba(0,0,0,0.94)',
  },
  hidden: {
    eyebrow: '??? UNKNOWN SIGNAL ???',
    title: 'HIDDEN CARD DISCOVERED',
    accent: '#a855f7',
    glow: 'rgba(168, 85, 247, 0.35)',
    bg: 'rgba(0,0,0,0.96)',
  },
  epic: {
    eyebrow: '? EPIC UNLOCK ?',
    title: 'EPIC REWARD UNLOCKED',
    accent: '#ff2a2a',
    glow: 'rgba(255, 42, 42, 0.35)',
    bg: 'rgba(0,0,0,0.94)',
  },
  generic: {
    eyebrow: '?? REWARD EARNED ??',
    title: 'REWARD UNLOCKED',
    accent: '#ffd24a',
    glow: 'rgba(255, 210, 74, 0.35)',
    bg: 'rgba(0,0,0,0.92)',
  },
};

export default function RewardReveal({
  visible,
  theme = 'generic',
  card,
  title,
  subtitle,
  footer,
  buttonText = 'HELL YEAH!',
  onClose,
}: RewardRevealProps) {
  const cfg = THEME[theme] || THEME.generic;

  const fade = useRef(new Animated.Value(0)).current;
  const cardY = useRef(new Animated.Value(140)).current;
  const cardScale = useRef(new Animated.Value(0.55)).current;
  const textY = useRef(new Animated.Value(28)).current;
  const glow = useRef(new Animated.Value(0)).current;
  const flash = useRef(new Animated.Value(0)).current;
  const stageLights = useRef(new Animated.Value(0)).current;
  const shake = useRef(new Animated.Value(0)).current;
  const smoke = useRef(new Animated.Value(0)).current;
  const logoSlam = useRef(new Animated.Value(0)).current;
  const sparks = useRef(new Animated.Value(0)).current;
  const idleFloat = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!visible) return;

    fade.setValue(0);
    cardY.setValue(140);
    cardScale.setValue(0.55);
    textY.setValue(28);
    glow.setValue(0);
    flash.setValue(0);
    stageLights.setValue(0);
    shake.setValue(0);
    smoke.setValue(0);
    logoSlam.setValue(0);
    sparks.setValue(0);
    idleFloat.setValue(0);

    Animated.sequence([
      Animated.timing(fade, {
        toValue: 1,
        duration: 180,
        useNativeDriver: true,
      }),
      Animated.parallel([
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
        Animated.sequence([
          Animated.timing(shake, {
            toValue: 1,
            duration: 45,
            useNativeDriver: true,
          }),
          Animated.timing(shake, {
            toValue: -1,
            duration: 45,
            useNativeDriver: true,
          }),
          Animated.timing(shake, {
            toValue: 0,
            duration: 60,
            useNativeDriver: true,
          }),
        ]),
      ]),
      Animated.parallel([
        Animated.spring(cardY, {
          toValue: 0,
          friction: 3,
          tension: 145,
          useNativeDriver: true,
        }),
        Animated.spring(cardScale, {
          toValue: 1,
          friction: 4,
          tension: 145,
          useNativeDriver: true,
        }),
        Animated.timing(textY, {
          toValue: 0,
          duration: 300,
          useNativeDriver: true,
        }),

        Animated.timing(sparks, {
          toValue: 1,
          duration: 720,
          useNativeDriver: true,
        }),
      ]),
    ]).start();

    const glowLoop = Animated.loop(
      Animated.sequence([
        Animated.timing(glow, {
          toValue: 1,
          duration: 760,
          useNativeDriver: true,
        }),
        Animated.timing(glow, {
          toValue: 0,
          duration: 760,
          useNativeDriver: true,
        }),
      ])
    );

    const lightLoop = Animated.loop(
      Animated.sequence([
        Animated.timing(stageLights, {
          toValue: 1,
          duration: 520,
          useNativeDriver: true,
        }),
        Animated.timing(stageLights, {
          toValue: 0,
          duration: 520,
          useNativeDriver: true,
        }),
      ])
    );

    const smokeLoop = Animated.loop(
      Animated.timing(smoke, {
        toValue: 1,
        duration: 2600,
        useNativeDriver: true,
      })
    );

    glowLoop.start();
    lightLoop.start();
    smokeLoop.start();

    const floatLoop = Animated.loop(
      Animated.sequence([
        Animated.timing(idleFloat, {
          toValue: 1,
          duration: 1450,
          useNativeDriver: true,
        }),
        Animated.timing(idleFloat, {
          toValue: 0,
          duration: 1450,
          useNativeDriver: true,
        }),
      ])
    );
    floatLoop.start();

    return () => {
      glowLoop.stop();
      lightLoop.stop();
      smokeLoop.stop();
      floatLoop.stop();
    };
  }, [visible, fade, cardY, cardScale, textY, glow, flash, stageLights, shake, smoke, sparks, idleFloat]);

  const glowOpacity = glow.interpolate({
    inputRange: [0, 1],
    outputRange: [0.35, 0.95],
  });

  const lightOpacity = stageLights.interpolate({
    inputRange: [0, 1],
    outputRange: [0.12, 0.55],
  });

  const shakeX = shake.interpolate({
    inputRange: [-1, 0, 1],
    outputRange: [-16, 0, 16],
  });

  const smokeLeftX = smoke.interpolate({
    inputRange: [0, 1],
    outputRange: [-55, 35],
  });

  const smokeRightX = smoke.interpolate({
    inputRange: [0, 1],
    outputRange: [55, -35],
  });

  const smokeOpacity = smoke.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: [0.08, 0.22, 0.08],
  });

  const logoSlamY = logoSlam.interpolate({
    inputRange: [0, 1],
    outputRange: [-70, 0],
  });

  const logoSlamScale = logoSlam.interpolate({
    inputRange: [0, 0.72, 1],
    outputRange: [1.8, 0.86, 1],
  });

  const logoSlamOpacity = logoSlam.interpolate({
    inputRange: [0, 0.2, 1],
    outputRange: [0, 1, 1],
  });

  const sparkOpacity = sparks.interpolate({
    inputRange: [0, 0.18, 1],
    outputRange: [0, 1, 0],
  });

  const sparkScale = sparks.interpolate({
    inputRange: [0, 1],
    outputRange: [0.35, 1.2],
  });

  const sparkFlyLeft = sparks.interpolate({
    inputRange: [0, 1],
    outputRange: [0, -95],
  });

  const sparkFlyRight = sparks.interpolate({
    inputRange: [0, 1],
    outputRange: [0, 95],
  });

  const idleFloatY = idleFloat.interpolate({
    inputRange: [0, 1],
    outputRange: [0, -14],
  });

  const idleTilt = idleFloat.interpolate({
    inputRange: [0, 1],
    outputRange: ['-3deg', '3deg'],
  });

  return (
    <Modal visible={visible} transparent animationType="none" onRequestClose={onClose}>
      <Animated.View
        style={[
          styles.overlay,
          {
            backgroundColor: cfg.bg,
            opacity: fade,
            transform: [{ translateX: shakeX }],
          },
        ]}
      >
        <Animated.View
          pointerEvents="none"
          style={[
            StyleSheet.absoluteFillObject,
            {
              backgroundColor: '#ffffff',
              opacity: flash,
            },
          ]}
        />

        <View style={styles.stageRig} pointerEvents="none">
          <Animated.View
            style={[
              styles.smokeLeft,
              {
                opacity: smokeOpacity,
                transform: [{ translateX: smokeLeftX }],
              },
            ]}
          />
          <Animated.View
            style={[
              styles.smokeRight,
              {
                opacity: smokeOpacity,
                transform: [{ translateX: smokeRightX }],
              },
            ]}
          />
          <Animated.View
            style={[
              styles.stageLightLeft,
              { backgroundColor: cfg.accent, opacity: lightOpacity },
            ]}
          />
          <Animated.View
            style={[
              styles.stageLightRight,
              { backgroundColor: cfg.accent, opacity: lightOpacity },
            ]}
          />
          <View style={styles.floorGlow} />
        </View>


        <View style={styles.sparkLayer} pointerEvents="none">
          <Animated.Text
            style={[
              styles.spark,
              {
                color: cfg.accent,
                opacity: sparkOpacity,
                transform: [{ translateX: sparkFlyLeft }, { scale: sparkScale }],
              },
            ]}
          >
            ?
          </Animated.Text>
          <Animated.Text
            style={[
              styles.sparkAlt,
              {
                color: cfg.accent,
                opacity: sparkOpacity,
                transform: [{ translateX: sparkFlyRight }, { scale: sparkScale }],
              },
            ]}
          >
            ?
          </Animated.Text>
        </View>


        <Animated.View style={[styles.headerBlock, { transform: [{ translateY: textY }] }]}>
          <Text style={[styles.eyebrow, { color: cfg.accent }]}>{subtitle || cfg.eyebrow}</Text>
          <Text style={styles.title}>{title || cfg.title}</Text>
        </Animated.View>

        <Animated.View
          style={[
            styles.cardStage,
            {
              transform: [{ translateY: Animated.add(cardY, idleFloatY) }, { scale: cardScale }, { rotate: idleTilt }],
            },
          ]}
        >
          <Animated.View
            style={[
              styles.glow,
              {
                backgroundColor: cfg.glow,
                opacity: glowOpacity,
              },
            ]}
          />
          {card?.front_image_url ? (
            <Image
              source={{ uri: card.front_image_url }}
              style={[styles.cardImage, { borderColor: cfg.accent }]}
              resizeMode="contain"
            />
          ) : (
            <View style={[styles.cardPlaceholder, { borderColor: cfg.accent }]}>
              <Text style={styles.placeholderText}>?</Text>
            </View>
          )}
        </Animated.View>

        <View style={styles.infoBlock}>
          <Text style={styles.cardName}>{card?.name || 'Reward Card'}</Text>
          <Text style={[styles.rarity, { color: cfg.accent }]}>
            {(card?.rarity || 'reward').toUpperCase()}
          </Text>
          <Text style={styles.footer}>
            {footer || 'Added to Special / Reward Cards'}
          </Text>
        </View>

        <Pressable style={[styles.button, { backgroundColor: cfg.accent }]} onPress={onClose}>
          <Text style={styles.buttonText}>{buttonText}</Text>
        </Pressable>
      </Animated.View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 18,
  },
  stageRig: {
    ...StyleSheet.absoluteFillObject,
    overflow: 'hidden',
  },
  smokeLeft: {
    position: 'absolute',
    left: -45,
    bottom: 120,
    width: CARD_W + 80,
    height: 145,
    borderRadius: 999,
    backgroundColor: 'rgba(255,255,255,0.38)',
    transform: [{ rotate: '-8deg' }],
  },
  smokeRight: {
    position: 'absolute',
    right: -45,
    bottom: 160,
    width: CARD_W + 70,
    height: 125,
    borderRadius: 999,
    backgroundColor: 'rgba(255,255,255,0.32)',
    transform: [{ rotate: '8deg' }],
  },
  stageLightLeft: {
    position: 'absolute',
    top: -80,
    left: -80,
    width: 190,
    height: 520,
    borderRadius: 95,
    transform: [{ rotate: '-22deg' }],
  },
  stageLightRight: {
    position: 'absolute',
    top: -80,
    right: -80,
    width: 190,
    height: 520,
    borderRadius: 95,
    transform: [{ rotate: '22deg' }],
  },
  floorGlow: {
    position: 'absolute',
    bottom: 72,
    width: CARD_W + 95,
    height: 42,
    borderRadius: 999,
    alignSelf: 'center',
    backgroundColor: 'rgba(255,255,255,0.08)',
  },
  logoSlam: {
    position: 'absolute',
    top: 42,
    alignItems: 'center',
    zIndex: 3,
  },
  logoSlamText: {
    fontSize: 42,
    fontWeight: '900',
    letterSpacing: 3,
    textShadowColor: '#000',
    textShadowOffset: { width: 0, height: 3 },
    textShadowRadius: 10,
  },
  logoSlamSub: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 2,
    marginTop: -4,
    textShadowColor: '#000',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 8,
  },
  sparkLayer: {
    position: 'absolute',
    top: CARD_H * 0.34,
    width: CARD_W + 160,
    height: 90,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 4,
  },
  spark: {
    position: 'absolute',
    left: 70,
    fontSize: 34,
    fontWeight: '900',
    textShadowColor: '#fff',
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 8,
  },
  sparkAlt: {
    position: 'absolute',
    right: 70,
    fontSize: 34,
    fontWeight: '900',
    textShadowColor: '#fff',
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 8,
  },
  burstLayer: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    justifyContent: 'center',
  },
  burst: {
    position: 'absolute',
    top: 92,
    fontSize: 34,
    fontWeight: '900',
    opacity: 0.6,
  },
  burstSmall: {
    position: 'absolute',
    bottom: 110,
    fontSize: 30,
    fontWeight: '900',
    opacity: 0.55,
  },
  headerBlock: {
    alignItems: 'center',
    marginBottom: 8,
  },
  eyebrow: {
    fontSize: 16,
    fontWeight: '900',
    textAlign: 'center',
    letterSpacing: 1,
  },
  title: {
    color: '#fff',
    fontSize: 27,
    fontWeight: '900',
    textAlign: 'center',
    marginTop: 6,
    textShadowColor: '#000',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 8,
  },
  cardStage: {
    width: CARD_W + 28,
    height: CARD_H + 28,
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 2,
  },
  glow: {
    position: 'absolute',
    width: CARD_W + 58,
    height: CARD_H + 58,
    borderRadius: 22,
  },
  cardImage: {
    width: CARD_W,
    height: CARD_H,
    borderRadius: 12,
    borderWidth: 3,
    backgroundColor: '#050505',
  },
  cardPlaceholder: {
    width: CARD_W,
    height: CARD_H,
    borderRadius: 12,
    borderWidth: 3,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#111',
  },
  placeholderText: {
    color: '#fff',
    fontSize: 72,
    fontWeight: '900',
  },
  infoBlock: {
    alignItems: 'center',
    marginTop: 4,
    marginBottom: 10,
  },
  cardName: {
    color: '#fff',
    fontSize: 23,
    fontWeight: '900',
    textAlign: 'center',
  },
  rarity: {
    marginTop: 2,
    fontSize: 14,
    fontWeight: '900',
    letterSpacing: 1,
  },
  footer: {
    color: '#d8d8d8',
    fontSize: 13,
    fontWeight: '700',
    textAlign: 'center',
    marginTop: 4,
  },
  button: {
    paddingHorizontal: 28,
    paddingVertical: 13,
    borderRadius: 999,
    borderWidth: 2,
    borderColor: '#fff',
  },
  buttonText: {
    color: '#080808',
    fontSize: 16,
    fontWeight: '900',
    letterSpacing: 0.6,
  },
});





























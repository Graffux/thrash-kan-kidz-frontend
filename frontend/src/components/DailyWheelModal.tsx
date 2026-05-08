import React, { useState, useRef } from 'react';
import { View, Text, StyleSheet, Modal, TouchableOpacity, Animated, Easing, Dimensions } from 'react-native';
import { Image as ExpoImage } from 'expo-image';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// 4 separate layer images
const IMG_WHEEL = 'https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/b2nnkk3b_Screenshot_20260423_090311_ChatGPT.png';
const IMG_FRAME = 'https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/lhhe4odr_file_00000000d9d071f7b937862f015b167c.png';
const IMG_SPIN_BTN = 'https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/dyjye6ko_file_000000000c4471f7a591a52c59897d60.png';
const IMG_POINTER = 'https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/o6zn0oij_file_00000000bb7c71f7acd437634d27784c.png';

// Segments clockwise from top: 200coins, freepack, 25coins, 1medal, 50coins, 3medals, 100coins, 5medals
// Segments clockwise from top pointer: 200coins, freepack, 25coins, 1medal, 50coins, 3medals, 100coins, 5medals
const SEGMENTS = [
  { type: 'coins', amount: 200, label: '200 Coins' },
  { type: 'free_pack', amount: 1, label: 'Free Pack!' },
  { type: 'coins', amount: 25, label: '25 Coins' },
  { type: 'medals', amount: 1, label: '1 Medal' },
  { type: 'coins', amount: 50, label: '50 Coins' },
  { type: 'medals', amount: 3, label: '3 Medals' },
  { type: 'coins', amount: 100, label: '100 Coins' },
  { type: 'medals', amount: 5, label: '5 Medals' },
];

const SEGMENT_ANGLE = 360 / SEGMENTS.length; // 45 degrees

function getTargetRotation(segmentIndex: number, currentRotation: number): number {
  const fullSpins = 5 + Math.floor(Math.random() * 3); // 5-7 full spins
  const jitter = (Math.random() - 0.5) * (SEGMENT_ANGLE * 0.35);
  const segmentCenter = segmentIndex * SEGMENT_ANGLE + SEGMENT_ANGLE / 2;
  const normalizedStop = 360 - segmentCenter + jitter;
  const currentNormalized = ((currentRotation % 360) + 360) % 360;
  let delta = normalizedStop - currentNormalized;
  if (delta < 0) delta += 360;
  return currentRotation + fullSpins * 360 + delta;
}

interface DailyWheelModalProps {
  visible: boolean;
  onClose: () => void;
  onSpin: () => Promise<any>;
  streak: number;
  onSpinStart?: () => void;
  onPrizeWon?: () => void;
}

export const DailyWheelModal: React.FC<DailyWheelModalProps> = ({ visible, onClose, onSpin, streak, onSpinStart, onPrizeWon }) => {
  const [spinning, setSpinning] = useState(false);
  const [result, setResult] = useState<any>(null);
  const spinAnim = useRef(new Animated.Value(0)).current;
  const currentRotation = useRef(0);

  const handleSpin = async () => {
    if (spinning) return;
    setSpinning(true);
    setResult(null);
    onSpinStart?.();

    try {
      const data = await onSpin();
      const prize = data.prize;

      // Find matching segment
      const segIndex = SEGMENTS.findIndex(
        s => s.type === prize.type && s.amount === prize.amount
      );
      const targetIndex = segIndex >= 0 ? segIndex : 0;

      const targetRotation = getTargetRotation(targetIndex, currentRotation.current);
      currentRotation.current = targetRotation;

      // Animate from 0 to targetRotation using the accumulated value
      spinAnim.setValue(0);

      Animated.timing(spinAnim, {
        toValue: targetRotation,
        duration: 5200,
        easing: Easing.bezier(0.12, 0.8, 0.18, 1),
        useNativeDriver: true,
      }).start(() => {
        setResult(data);
        setSpinning(false);
        onPrizeWon?.();
      });
    } catch (err: any) {
      setSpinning(false);
      setResult({ error: err.message || 'Failed to spin' });
    }
  };

  const handleClose = () => {
    // Don't reset rotation - it accumulates
    setResult(null);
    setSpinning(false);
    onClose();
  };

  const wheelRotation = spinAnim.interpolate({
    inputRange: [0, 360],
    outputRange: ['0deg', '360deg'],
  });

  const STAGE = Math.min(SCREEN_WIDTH - 32, 360);
  const WHEEL_SIZE = STAGE * 0.78;
  const SPIN_BTN_SIZE = STAGE * 0.22;
  const POINTER_W = STAGE * 0.14;
  const POINTER_H = STAGE * 0.18;

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={handleClose}>
      <View style={styles.overlay}>
        <View style={styles.container}>
          {/* Close X */}
          <TouchableOpacity style={styles.closeBtn} onPress={handleClose} data-testid="close-wheel-btn">
            <Text style={styles.closeBtnText}>X</Text>
          </TouchableOpacity>

          <Text style={styles.title}>Daily Spin</Text>
          {streak > 0 && (
            <Text style={styles.streak}>
              {streak} day streak! {streak >= 7 ? 'BIG PRIZE guaranteed!' : `${7 - streak} more for bonus!`}
            </Text>
          )}

          {/* Wheel Stage */}
          <View style={[styles.stage, { width: STAGE, height: STAGE }]}>
            {/* Layer 1: Spinning wheel (bottom) */}
            <View style={[styles.wheelClip, { 
              width: WHEEL_SIZE, height: WHEEL_SIZE, borderRadius: WHEEL_SIZE / 2,
              top: (STAGE - WHEEL_SIZE) / 2, left: (STAGE - WHEEL_SIZE) / 2,
            }]}>
              <Animated.View style={{ width: WHEEL_SIZE, height: WHEEL_SIZE, transform: [{ rotate: wheelRotation }] }}>
                <ExpoImage source={{ uri: IMG_WHEEL }} style={{ width: WHEEL_SIZE, height: WHEEL_SIZE }} contentFit="contain" />
              </Animated.View>
            </View>

            {/* Layer 2: Static frame (on top of wheel) */}
            <ExpoImage source={{ uri: IMG_FRAME }} style={[styles.frameImg, { width: STAGE, height: STAGE }]} contentFit="contain" />

            {/* Layer 3: Pointer at top */}
            <ExpoImage 
              source={{ uri: IMG_POINTER }} 
              style={[styles.pointerImg, { width: POINTER_W, height: POINTER_H, left: (STAGE - POINTER_W) / 2, top: -POINTER_H * 0.15 }]} 
              contentFit="contain" 
            />

            {/* Layer 4: Spin button center (tappable) */}
            <TouchableOpacity
              style={[styles.spinBtnWrap, { 
                width: SPIN_BTN_SIZE, height: SPIN_BTN_SIZE,
                top: (STAGE - SPIN_BTN_SIZE) / 2, left: (STAGE - SPIN_BTN_SIZE) / 2,
              }]}
              onPress={handleSpin}
              disabled={spinning || !!result}
              data-testid="spin-wheel-btn"
            >
              <ExpoImage source={{ uri: IMG_SPIN_BTN }} style={{ width: SPIN_BTN_SIZE, height: SPIN_BTN_SIZE }} contentFit="contain" />
            </TouchableOpacity>
          </View>

          {/* Result */}
          {result && !result.error && (
            <View style={styles.resultSection}>
              <Text style={styles.resultTitle}>You won!</Text>
              <Text style={styles.resultPrize}>{result.prize.label}</Text>
              {result.streak_bonus && <Text style={styles.streakBonus}>7-Day Streak Bonus!</Text>}
            </View>
          )}

          {result?.error && (
            <Text style={styles.errorText}>{result.error}</Text>
          )}

          {/* Bottom button */}
          {!result ? (
            spinning ? (
              <Text style={styles.spinningText}>Spinning...</Text>
            ) : null
          ) : (
            <TouchableOpacity style={styles.collectButton} onPress={handleClose} data-testid="collect-prize-btn">
              <Text style={styles.collectButtonText}>REAP YOUR REWARDS!</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.95)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  container: {
    width: '95%',
    maxWidth: 400,
    backgroundColor: '#0a0a14',
    borderRadius: 24,
    padding: 16,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#8B0000',
  },
  closeBtn: {
    position: 'absolute',
    top: 10,
    right: 14,
    zIndex: 20,
  },
  closeBtnText: {
    color: '#888',
    fontSize: 22,
    fontWeight: 'bold',
  },
  title: {
    fontSize: 26,
    fontWeight: 'bold',
    color: '#8B0000',
    fontStyle: 'italic',
    marginBottom: 2,
  },
  streak: {
    fontSize: 12,
    color: '#CE93D8',
    marginBottom: 6,
    textAlign: 'center',
  },
  // Stage holds all layers
  stage: {
    position: 'relative',
    marginVertical: 8,
  },
  wheelClip: {
    position: 'absolute',
    overflow: 'hidden',
    zIndex: 1,
  },
  frameImg: {
    position: 'absolute',
    top: 0,
    left: 0,
    zIndex: 2,
  },
  pointerImg: {
    position: 'absolute',
    zIndex: 4,
  },
  spinBtnWrap: {
    position: 'absolute',
    zIndex: 5,
  },
  resultSection: {
    alignItems: 'center',
    marginVertical: 10,
  },
  resultTitle: {
    fontSize: 16,
    color: '#aaa',
  },
  resultPrize: {
    fontSize: 30,
    fontWeight: 'bold',
    color: '#FFD700',
  },
  streakBonus: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#E91E63',
    marginTop: 6,
  },
  errorText: {
    color: '#F44336',
    fontSize: 14,
    marginVertical: 8,
  },
  spinningText: {
    color: '#888',
    fontSize: 16,
    fontStyle: 'italic',
    marginTop: 8,
  },
  collectButton: {
    backgroundColor: '#4CAF50',
    paddingHorizontal: 36,
    paddingVertical: 14,
    borderRadius: 24,
    marginTop: 8,
  },
  collectButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
    fontStyle: 'italic',
  },
});

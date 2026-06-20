/**
 * ScratchCard — finger-drag scratch-off overlay for variant card reveals.
 *
 * Behavior:
 *   - Renders the card image (revealed art) on the bottom layer.
 *   - Renders an SVG mask + cover image on top. Mask starts fully opaque;
 *     drag finger to paint white circles into the mask, "scratching" the
 *     cover away to reveal the art underneath.
 *   - When ~55% of the cover is scratched, the cover fades out automatically
 *     and onComplete() fires once.
 *
 * Why SVG (not Skia):
 *   - react-native-svg ships in ~600KB vs Skia ~5MB
 *   - Web-compatible (works in the Expo web preview without polyfills)
 *   - No prebuild required beyond a normal EAS build
 *
 * Coverage estimate:
 *   - Each scratch dot has fixed radius; we track unique grid cells touched
 *     instead of true pixel coverage. Grid is finer than the dot radius so
 *     the estimate is conservative-but-cheap. Sweep enough and you cross
 *     the threshold; the user feels the reveal happen at the right moment.
 */
import React, { useCallback, useMemo, useRef, useState, useEffect } from 'react';
import { View, StyleSheet, PanResponder, GestureResponderEvent, PanResponderGestureState, Animated, Platform } from 'react-native';
import { Image as ExpoImage } from 'expo-image';
import Svg, { Defs, Mask, Rect, Circle, G, Image as SvgImage } from 'react-native-svg';
import * as Haptics from 'expo-haptics';

interface Props {
  width: number;
  height: number;
  imageUri: string;       // The card front (revealed beneath the scratch cover)
  coverUri: string;       // The themed scratch cover (gets scratched away)
  onComplete?: () => void; // Fires once when scratch threshold is crossed
  brushRadius?: number;   // Brush size in px, default 22
  threshold?: number;     // Coverage fraction 0–1 to auto-complete, default 0.55
}

export const ScratchCard: React.FC<Props> = ({
  width,
  height,
  imageUri,
  coverUri,
  onComplete,
  brushRadius = 22,
  threshold = 0.55,
}) => {
  // Each entry is one circle painted into the mask. We keep them in state
  // because the SVG re-renders only on state change.
  const [dots, setDots] = useState<{ x: number; y: number }[]>([]);
  const [revealed, setRevealed] = useState(false);
  // Slightly transparent so players can tease the art beneath as they scratch.
  // 0.82 = visible cover with a faint ghost of the card underneath.
  const coverOpacity = useRef(new Animated.Value(0.82)).current;

  // Grid-based coverage tracking. We snap each dot to a cell and count
  // unique touched cells. Cell size ~= half the brush radius keeps overlap
  // counting honest without being expensive.
  const cellSize = Math.max(8, Math.floor(brushRadius / 1.5));
  const cols = Math.max(1, Math.ceil(width / cellSize));
  const rows = Math.max(1, Math.ceil(height / cellSize));
  const totalCells = cols * rows;
  const touchedCells = useRef<Set<number>>(new Set());
  // Throttle haptic feedback. PanResponder fires onMove ~60Hz which would
  // queue a vibration on every frame — that feels like a constant buzz
  // and on Android can trip the OS rate limiter. We gate haptics to fire
  // at most once every ~80ms, which feels like the textured chatter of
  // dragging a coin across foil.
  const lastHapticAt = useRef(0);

  const fireHaptic = useCallback(() => {
    // Haptics aren't supported on web — guard so the dev preview doesn't
    // throw. On native, expo-haptics is a no-op if the device lacks a
    // vibration motor.
    if (Platform.OS === 'web') return;
    const now = Date.now();
    if (now - lastHapticAt.current < 80) return;
    lastHapticAt.current = now;
    // Light impact = a single short "tick", perfect for scratch chatter.
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {
      /* ignore haptic errors silently — never crash a scratch */
    });
  }, []);

  // Trigger the reveal animation + onComplete callback exactly once.
  const triggerReveal = useCallback(() => {
    if (revealed) return;
    setRevealed(true);
    // Stronger haptic to mark the reveal moment — feels like ripping off
    // the last sliver of foil.
    if (Platform.OS !== 'web') {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {
        /* swallow — never crash the reveal */
      });
    }
    Animated.timing(coverOpacity, {
      toValue: 0,
      duration: 350,
      useNativeDriver: true,
    }).start(() => {
      onComplete?.();
    });
  }, [revealed, coverOpacity, onComplete]);

  const recordTouch = useCallback(
    (x: number, y: number) => {
      // Clamp inside bounds (RN sometimes gives negative on edge gestures)
      const cx = Math.max(0, Math.min(width, x));
      const cy = Math.max(0, Math.min(height, y));
      const col = Math.floor(cx / cellSize);
      const row = Math.floor(cy / cellSize);
      const key = row * cols + col;
      const isNewCell = !touchedCells.current.has(key);
      if (isNewCell) {
        touchedCells.current.add(key);
        // Only buzz when the finger crosses into fresh territory. Avoids
        // a constant rumble when the user holds still mid-drag.
        fireHaptic();
      }
      setDots((prev) => [...prev, { x: cx, y: cy }]);
      const coverage = touchedCells.current.size / totalCells;
      if (coverage >= threshold) {
        triggerReveal();
      }
    },
    [width, height, cellSize, cols, totalCells, threshold, triggerReveal, fireHaptic]
  );

  // PanResponder captures both initial touch and drag deltas. We feed every
  // sampled point into recordTouch — RN typically delivers events at 60Hz
  // during a drag, plenty dense for a smooth scratch.
  const panResponder = useMemo(
    () =>
      PanResponder.create({
        onStartShouldSetPanResponder: () => !revealed,
        onMoveShouldSetPanResponder: () => !revealed,
        onPanResponderGrant: (e: GestureResponderEvent) => {
          recordTouch(e.nativeEvent.locationX, e.nativeEvent.locationY);
        },
        onPanResponderMove: (e: GestureResponderEvent, _g: PanResponderGestureState) => {
          recordTouch(e.nativeEvent.locationX, e.nativeEvent.locationY);
        },
      }),
    [revealed, recordTouch]
  );

  // Reset dots/coverage if the imageUri changes (e.g. cycling through pack cards).
  useEffect(() => {
    setDots([]);
    setRevealed(false);
    touchedCells.current = new Set();
    coverOpacity.setValue(0.82);
  }, [imageUri, coverOpacity]);

  return (
    <View style={[styles.wrap, { width, height }]} {...panResponder.panHandlers}>
      {/* Bottom layer: revealed card art */}
      <ExpoImage
        source={{ uri: imageUri }}
        style={StyleSheet.absoluteFill}
        contentFit="contain"
        cachePolicy="memory-disk"
        transition={150}
      />
      {/* Top layer: scratch cover.
          - SOLID FALLBACK behind the SVG <Image>: if the cover image fails
            to render (large remote JPEG + react-native-svg's flaky
            href loading), the user still sees something obvious to scratch
            off, not a "blank screen, nothing happens" state. The SVG
            image renders on top of this fallback when it does load — same
            visual either way. */}
      <Animated.View
        pointerEvents={revealed ? 'none' : 'auto'}
        style={[StyleSheet.absoluteFill, { opacity: coverOpacity }]}
      >
        <Svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
          <Defs>
            <Mask id="scratchMask" x="0" y="0" width={width} height={height}>
              {/* White = visible cover. We start fully white. */}
              <Rect x="0" y="0" width={width} height={height} fill="white" />
              {/* Each dot punches a black hole in the mask, revealing card below. */}
              <G>
                {dots.map((d, i) => (
                  <Circle key={i} cx={d.x} cy={d.y} r={brushRadius} fill="black" />
                ))}
              </G>
            </Mask>
          </Defs>
          {/* Fallback foil color — also masked so scratch holes show the card
              art underneath, not a solid gold layer. If the SvgImage href
              below fails to load (slow network / flaky devices), this Rect
              still gives the user something to scratch. */}
          <Rect
            x="0"
            y="0"
            width={width}
            height={height}
            fill="#d4a017"
            mask="url(#scratchMask)"
          />
          {/* The fancy cover image, painted on top of the fallback Rect. */}
          <SvgImage
            href={coverUri}
            x="0"
            y="0"
            width={width}
            height={height}
            preserveAspectRatio="xMidYMid slice"
            mask="url(#scratchMask)"
          />
        </Svg>
      </Animated.View>
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: {
    position: 'relative',
    overflow: 'hidden',
    backgroundColor: '#0a0a0a',
    borderRadius: 8,
  },
});

export default ScratchCard;

/**
 * RonchTrashTalk — surprise mascot popup with rotating one-liners.
 *
 * Drops a Ronch headshot + speech-bubble into the corner of any screen
 * for ~3 seconds, then fades out. Triggered every Nth pack-open via the
 * `maybeShowRonchTrashTalk()` helper exported alongside this component.
 *
 * The trash-talk pool is intentionally short + punchy + on-brand for the
 * death-metal aesthetic. Add lines freely — randomized pull is biased
 * away from immediate repeats.
 *
 * Why a self-contained controlled component:
 *   - Lets callers (Shop, Home, Goals, etc.) reuse the same Ronch
 *     personality without re-implementing the popup choreography.
 *   - Counter logic lives in `maybeShowRonchTrashTalk()` — pure function
 *     with AsyncStorage persistence so it survives app restarts.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { View, Text, StyleSheet, Dimensions } from 'react-native';
import { Image as ExpoImage } from 'expo-image';
import { MotiView } from 'moti';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { MASCOT_FOR_EVENT } from '../assets/mascot';

const TRASH_TALK_LINES: string[] = [
  "Bones rattling yet?",
  "Open more or perish.",
  "These packs ain't pulling themselves.",
  "More variants. Less mercy.",
  "Get back to grinding, weakling.",
  "I smell duplicates. Disgusting.",
  "Variants taste better than respect.",
  "Crack another pack, you coward.",
  "The metal demands sacrifice. PULL.",
  "If this pack is bad, I'm blaming you.",
  "Don't make me show up again.",
  "Real Thrashers complete sets. ARE you a real Thrasher?",
];

// Storage keys for the pack-counter + last-seen line index.
const KEY_PACK_COUNTER = 'ronch_pack_counter_v1';
const KEY_LAST_LINE = 'ronch_last_line_v1';

// Frequency: show Ronch every N pack opens. Bump higher for less spam.
const RONCH_EVERY_N = 10;

/**
 * Increment the pack-open counter and decide whether Ronch shows up.
 * Returns the line to show OR null if Ronch isn't appearing this time.
 * Side-effects: writes new counter + last-line index to AsyncStorage.
 */
export async function maybeShowRonchTrashTalk(): Promise<string | null> {
  try {
    const rawCount = await AsyncStorage.getItem(KEY_PACK_COUNTER);
    const count = (parseInt(rawCount || '0', 10) || 0) + 1;
    await AsyncStorage.setItem(KEY_PACK_COUNTER, String(count));

    if (count % RONCH_EVERY_N !== 0) return null;

    // Pick a random line, biased away from the last one we showed.
    const rawLast = await AsyncStorage.getItem(KEY_LAST_LINE);
    const lastIdx = parseInt(rawLast || '-1', 10);
    let pick = Math.floor(Math.random() * TRASH_TALK_LINES.length);
    if (pick === lastIdx && TRASH_TALK_LINES.length > 1) {
      pick = (pick + 1) % TRASH_TALK_LINES.length;
    }
    await AsyncStorage.setItem(KEY_LAST_LINE, String(pick));
    return TRASH_TALK_LINES[pick];
  } catch {
    // AsyncStorage hiccup → silently skip, never crash a pack reveal.
    return null;
  }
}

interface Props {
  line: string | null;            // null hides the popover
  onDismiss: () => void;
  durationMs?: number;            // total visible time before auto-fade
}

export const RonchTrashTalk: React.FC<Props> = ({ line, onDismiss, durationMs = 3200 }) => {
  const [fading, setFading] = useState(false);

  useEffect(() => {
    if (!line) return;
    setFading(false);
    const fadeT = setTimeout(() => setFading(true), durationMs - 400);
    const doneT = setTimeout(() => onDismiss(), durationMs);
    return () => {
      clearTimeout(fadeT);
      clearTimeout(doneT);
    };
  }, [line, durationMs, onDismiss]);

  // Position bottom-center, above the tab bar but out of the way of
  // pack-reveal content. Width capped so long lines wrap nicely.
  const { width } = useMemo(() => Dimensions.get('window'), []);
  const maxWidth = Math.min(320, width - 32);

  if (!line) return null;

  return (
    <MotiView
      pointerEvents="none"
      from={{ translateY: 80, opacity: 0 }}
      animate={{ translateY: 0, opacity: fading ? 0 : 1 }}
      transition={{ type: 'spring', damping: 12, stiffness: 200, mass: 0.6 }}
      style={[styles.wrap, { maxWidth }]}
    >
      <View style={styles.bubble}>
        <Text style={styles.line}>{line}</Text>
      </View>
      <View style={styles.headshotGlow}>
        <ExpoImage
          source={{ uri: MASCOT_FOR_EVENT('duplicate') }}
          style={styles.headshot}
          contentFit="cover"
          cachePolicy="memory-disk"
        />
      </View>
    </MotiView>
  );
};

const styles = StyleSheet.create({
  wrap: {
    position: 'absolute',
    bottom: 100,
    alignSelf: 'center',
    flexDirection: 'row',
    alignItems: 'flex-end',
    zIndex: 9998,
    elevation: 9998,
  },
  bubble: {
    flex: 1,
    backgroundColor: '#0d0d0d',
    borderColor: '#39FF14',
    borderWidth: 2,
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 14,
    marginRight: 8,
    shadowColor: '#39FF14',
    shadowOpacity: 0.85,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 0 },
    elevation: 10,
  },
  line: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '800',
    lineHeight: 18,
    letterSpacing: 0.5,
  },
  headshotGlow: {
    width: 56,
    height: 56,
    borderRadius: 28,
    borderWidth: 2,
    borderColor: '#39FF14',
    overflow: 'hidden',
    backgroundColor: '#050505',
    shadowColor: '#39FF14',
    shadowOpacity: 0.85,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 0 },
    elevation: 10,
  },
  headshot: {
    width: '100%',
    height: '100%',
  },
});

export default RonchTrashTalk;

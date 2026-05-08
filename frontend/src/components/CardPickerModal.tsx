import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Modal,
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  Animated,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useSoundPlayer } from '../utils/sounds';

interface Prize {
  type: string;
  amount: number;
  label: string;
}

interface CardPickerModalProps {
  visible: boolean;
  onClose: () => void;
  apiUrl: string;
  userId: string;
  onPrizeWon: () => void;
}

const { width } = Dimensions.get('window');
const CARD_SIZE = Math.min((width - 80) / 4, 76);

// Build a layout of 8 cards = 4 prizes shown twice, shuffled
function buildLayout(prizes: Prize[]): Prize[] {
  const pairs = [...prizes, ...prizes];
  for (let i = pairs.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [pairs[i], pairs[j]] = [pairs[j], pairs[i]];
  }
  return pairs;
}

const PRIZE_ICONS: Record<string, string> = {
  '1 Free Pack': 'gift',
  '1 Medal': 'medal',
  '2 Medals': 'medal',
  '3 Medals': 'medal',
};
const PRIZE_COLORS: Record<string, string> = {
  '1 Free Pack': '#E91E63',
  '1 Medal': '#FFC107',
  '2 Medals': '#FF9800',
  '3 Medals': '#FFD700',
};

export const CardPickerModal: React.FC<CardPickerModalProps> = ({
  visible,
  onClose,
  apiUrl,
  userId,
  onPrizeWon,
}) => {
  const [loading, setLoading] = useState(true);
  const [canPlay, setCanPlay] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [prizes, setPrizes] = useState<Prize[]>([]);
  const [layout, setLayout] = useState<Prize[]>([]);
  const [flipped, setFlipped] = useState<boolean[]>(Array(8).fill(false));
  const [matched, setMatched] = useState<boolean[]>(Array(8).fill(false));
  const [first, setFirst] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [wonPrize, setWonPrize] = useState<Prize | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Ref-based mirror of `first` to eliminate any chance of stale-state during
  // rapid taps: React setState is async, so the closure in handleTap could
  // see `first=null` on the 2nd tap if the user taps before re-render.
  const firstRef = useRef<number | null>(null);

  const tapSound = useSoundPlayer('button_tap');
  const matchSound = useSoundPlayer('prize_won');
  const dupeSound = useSoundPlayer('duplicate');

  const fetchState = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiUrl}/api/users/${userId}/card-picker`);
      if (!res.ok) {
        // Backend probably hasn't deployed the new endpoints yet
        setError(
          res.status === 404
            ? 'Card Picker not available yet. The server is still updating, try again in a few minutes.'
            : `Server error (${res.status}). Try again later.`
        );
        setCanPlay(false);
        setCooldown(-1); // marker for "error state, not real cooldown"
        return;
      }
      const data = await res.json();
      setCanPlay(!!data.can_play);
      setCooldown(data.cooldown_seconds || 0);
      setPrizes(data.prizes || []);
      if (data.can_play && data.prizes?.length) {
        setLayout(buildLayout(data.prizes));
        setFlipped(Array(8).fill(false));
        setMatched(Array(8).fill(false));
        setFirst(null);
        setWonPrize(null);
      }
    } catch (_e) {
      setError('Failed to load Card Picker. Check your connection.');
      setCooldown(-1);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (visible) {
      setError(null);
      fetchState();
    }
  }, [visible]);

  const handleTap = async (idx: number) => {
    if (busy || flipped[idx] || matched[idx] || wonPrize) return;
    tapSound.play();
    const next = [...flipped];
    next[idx] = true;
    setFlipped(next);

    // Use ref (synchronous) instead of state (async) so rapid taps can't
    // cause the 2nd tap to see first=null and both flips become "first".
    if (firstRef.current === null) {
      firstRef.current = idx;
      setFirst(idx);
      return;
    }

    const firstIdx = firstRef.current;

    // Second card flipped — check match
    setBusy(true);
    const a = layout[firstIdx];
    const b = layout[idx];
    const isMatch = a.label === b.label;

    setTimeout(async () => {
      if (isMatch) {
        const newMatched = [...matched];
        newMatched[firstIdx] = true;
        newMatched[idx] = true;
        setMatched(newMatched);
        matchSound.play();

        // Display the prize the USER MATCHED immediately (source of truth:
        // client-side layout). The server call below is still the authority
        // on balance updates — but we no longer rely on the server echoing
        // the label back for the display, so if anything is wrong with the
        // server round-trip the user still sees the correct prize.
        setWonPrize(a);

        // Claim prize from server — send the label of the pair the user
        // actually matched so the server grants the matching reward instead
        // of picking a random prize.
        try {
          const res = await fetch(
            `${apiUrl}/api/users/${userId}/card-picker/claim`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ prize_label: a.label }),
            }
          );
          const data = await res.json();
          if (res.ok && data.success) {
            // If server echoes a DIFFERENT label than what was matched, the
            // client value (`a`) stays displayed — protects against any
            // server-side regression. Balance is trusted from server.
            onPrizeWon();
          } else {
            setError(data?.detail || 'Failed to claim prize');
            // Roll back the celebration if the claim actually failed.
            setWonPrize(null);
          }
        } catch (_e) {
          setError('Failed to claim prize');
          setWonPrize(null);
        }
      } else {
        // Flip back
        const back = [...flipped];
        back[firstIdx] = false;
        back[idx] = false;
        setFlipped(back);
        dupeSound.play();
      }
      firstRef.current = null;
      setFirst(null);
      setBusy(false);
    }, 700);
  };

  const formatCooldown = (secs: number) => {
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    return `${h}h ${m}m`;
  };

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.overlay}>
        <View style={styles.container}>
          <View style={styles.header}>
            <Text style={styles.title} testID="card-picker-title">
              Card Picker
            </Text>
            <TouchableOpacity onPress={onClose} testID="card-picker-close-btn">
              <Ionicons name="close" size={24} color="#fff" />
            </TouchableOpacity>
          </View>
          <Text style={styles.subtitle}>
            Match a pair to win a prize!
          </Text>

          {loading ? (
            <ActivityIndicator size="large" color="#FFD700" style={{ marginVertical: 60 }} />
          ) : !canPlay && !wonPrize ? (
            <View style={styles.cooldownContainer}>
              {error ? (
                <>
                  <Ionicons name="cloud-offline" size={48} color="#FF5252" />
                  <Text style={styles.errorText}>{error}</Text>
                </>
              ) : (
                <>
                  <Ionicons name="time" size={48} color="#FFD700" />
                  <Text style={styles.cooldownText}>
                    Come back in {formatCooldown(cooldown)}
                  </Text>
                </>
              )}
            </View>
          ) : wonPrize ? (
            <View style={styles.wonContainer}>
              <Text style={styles.wonTitle}>You won!</Text>
              <View
                style={[
                  styles.prizeCardLarge,
                  { borderColor: PRIZE_COLORS[wonPrize.label] || '#FFD700' },
                ]}
              >
                <Ionicons
                  name={(PRIZE_ICONS[wonPrize.label] || 'star') as any}
                  size={56}
                  color={PRIZE_COLORS[wonPrize.label] || '#FFD700'}
                />
                <Text style={styles.prizeLabelLarge}>{wonPrize.label}</Text>
              </View>
              <TouchableOpacity
                style={styles.closeBtn}
                onPress={onClose}
                testID="card-picker-claim-close-btn"
              >
                <Text style={styles.closeBtnText}>Awesome!</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <>
              <View style={styles.grid}>
                {layout.map((prize, idx) => {
                  const isFlipped = flipped[idx] || matched[idx];
                  return (
                    <TouchableOpacity
                      key={idx}
                      style={[
                        styles.card,
                        isFlipped && styles.cardFlipped,
                        matched[idx] && {
                          borderColor: PRIZE_COLORS[prize.label] || '#FFD700',
                        },
                      ]}
                      onPress={() => handleTap(idx)}
                      activeOpacity={0.8}
                      disabled={busy}
                      testID={`card-picker-card-${idx}`}
                    >
                      {isFlipped ? (
                        <View style={styles.cardFace}>
                          <Ionicons
                            name={(PRIZE_ICONS[prize.label] || 'star') as any}
                            size={28}
                            color={PRIZE_COLORS[prize.label] || '#FFD700'}
                          />
                          <Text style={styles.cardPrizeText} numberOfLines={2}>
                            {prize.label}
                          </Text>
                        </View>
                      ) : (
                        <View style={styles.cardBack}>
                          <Text style={styles.cardBackText}>?</Text>
                        </View>
                      )}
                    </TouchableOpacity>
                  );
                })}
              </View>
              {error && <Text style={styles.errorText}>{error}</Text>}
            </>
          )}
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.85)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  container: {
    width: '92%',
    backgroundColor: '#1a1a2e',
    borderRadius: 20,
    padding: 20,
    borderWidth: 2,
    borderColor: '#FFD700',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFD700',
  },
  subtitle: {
    fontSize: 13,
    color: '#aaa',
    textAlign: 'center',
    marginBottom: 16,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 8,
  },
  card: {
    width: CARD_SIZE,
    height: CARD_SIZE * 1.4,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#444',
    backgroundColor: '#0a0a1f',
    overflow: 'hidden',
  },
  cardFlipped: {
    borderColor: '#FFD700',
    backgroundColor: '#15152e',
  },
  cardBack: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#2a2a4a',
  },
  cardBackText: {
    fontSize: 32,
    color: '#FFD700',
    fontWeight: 'bold',
  },
  cardFace: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 4,
    gap: 4,
  },
  cardPrizeText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '600',
    textAlign: 'center',
  },
  cooldownContainer: {
    alignItems: 'center',
    paddingVertical: 40,
    gap: 12,
  },
  cooldownText: {
    color: '#FFD700',
    fontSize: 18,
    fontWeight: '600',
  },
  wonContainer: {
    alignItems: 'center',
    paddingVertical: 20,
    gap: 16,
  },
  wonTitle: {
    color: '#FFD700',
    fontSize: 26,
    fontWeight: 'bold',
  },
  prizeCardLarge: {
    width: 180,
    height: 180,
    borderRadius: 16,
    borderWidth: 3,
    backgroundColor: 'rgba(255,215,0,0.08)',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 8,
  },
  prizeLabelLarge: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
  },
  closeBtn: {
    backgroundColor: '#FFD700',
    paddingVertical: 12,
    paddingHorizontal: 32,
    borderRadius: 24,
    marginTop: 8,
  },
  closeBtnText: {
    color: '#000',
    fontWeight: 'bold',
    fontSize: 16,
  },
  errorText: {
    color: '#F44336',
    fontSize: 13,
    textAlign: 'center',
    marginTop: 12,
  },
});

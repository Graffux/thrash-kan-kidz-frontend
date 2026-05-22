/**
 * FeaturedCards — Profile showcase of up to 5 player-pinned cards.
 *
 * - Renders 5 slots in a horizontal row (empty slots show a "+" prompt).
 * - Taps open a selection modal showing all OWNED cards (a `CardPickerSelect`).
 * - On confirm, calls AppContext.updateFeaturedCards() and refreshes user state.
 *
 * Visual: rusted-metal frame + slime drip glow on filled slots. Empty slots
 * are dashed-outline placeholders with the Thrash skull emoji.
 */
import React, { useMemo, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { Image as ExpoImage } from 'expo-image';
import { Ionicons } from '@expo/vector-icons';
import { useApp } from '../context/AppContext';
import { cardThumb } from '../utils/cardImage';

const SLOTS = 5;

interface Props {
  apiUrl: string;
  /** When true, render the slots without picker/edit affordances — used on
      a friend's profile so visitors can see the showcase but not modify it. */
  readOnly?: boolean;
  /** Optional override — when viewing another user's profile, pass their
      featured card IDs + cards so the component can render their showcase
      instead of pulling from the current viewer's AppContext. */
  featuredIds?: string[];
  cardsLookup?: Record<string, any>;
}

export const FeaturedCards: React.FC<Props> = ({ readOnly = false, featuredIds, cardsLookup }) => {
  const { user, userCards, updateFeaturedCards } = useApp();
  const [showPicker, setShowPicker] = useState(false);
  const [editingSlot, setEditingSlot] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  const featured = featuredIds ?? user?.featured_card_ids ?? [];

  // Map id -> card lookup. In readOnly mode use the passed-in cardsLookup
  // (the visitor doesn't own those cards, so AppContext.userCards wouldn't help).
  const ownedById = useMemo(() => {
    if (cardsLookup) return cardsLookup;
    const m: Record<string, any> = {};
    for (const uc of userCards) {
      if (uc.card?.id) m[uc.card.id] = uc.card;
    }
    return m;
  }, [userCards, cardsLookup]);

  const slots = useMemo(() => {
    const arr: (any | null)[] = Array(SLOTS).fill(null);
    featured.slice(0, SLOTS).forEach((id, i) => {
      arr[i] = ownedById[id] ?? null;
    });
    return arr;
  }, [featured, ownedById]);

  const openPicker = (slotIndex: number) => {
    if (readOnly) return;
    setEditingSlot(slotIndex);
    setShowPicker(true);
  };

  const handleSelect = async (cardId: string | null) => {
    if (editingSlot === null) return;
    const next = [...featured];
    while (next.length < SLOTS) next.push('');
    if (cardId === null) {
      next.splice(editingSlot, 1); // clear slot (shift left)
    } else {
      // Prevent duplicates: remove cardId from any other slot first
      for (let i = 0; i < next.length; i++) {
        if (i !== editingSlot && next[i] === cardId) next[i] = '';
      }
      next[editingSlot] = cardId;
    }
    const cleaned = next.filter((id) => id);
    setSaving(true);
    try {
      await updateFeaturedCards(cleaned);
      setShowPicker(false);
      setEditingSlot(null);
    } catch (e: any) {
      Alert.alert('Error', e?.message || 'Failed to update featured cards');
    } finally {
      setSaving(false);
    }
  };

  if (!user) return null;

  return (
    <View style={styles.container} testID="featured-cards-section">
      <View style={styles.headerRow}>
        <Text style={styles.title}>💀 FEATURED CARDS</Text>
        <Text style={styles.subtitle}>{featured.length}/{SLOTS}</Text>
      </View>
      {!readOnly && (
        <Text style={styles.help}>Pin your top 5 to flex on the homies.</Text>
      )}

      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.row}>
        {slots.map((card, idx) => (
          <TouchableOpacity
            key={idx}
            style={[styles.slot, card && styles.slotFilled]}
            onPress={() => openPicker(idx)}
            activeOpacity={0.85}
            testID={`featured-slot-${idx}`}
          >
            {card ? (
              <>
                <ExpoImage
                  source={{ uri: cardThumb(card, 360) }}
                  style={styles.slotImage}
                  contentFit="cover"
                  cachePolicy="memory-disk"
                  transition={150}
                  recyclingKey={card.id}
                />
                {/* Slime drip glow ring */}
                <View pointerEvents="none" style={styles.slotGlow} />
              </>
            ) : (
              <View style={styles.slotEmpty}>
                <Text style={styles.slotPlus}>+</Text>
                <Text style={styles.slotEmptyLabel}>Slot {idx + 1}</Text>
              </View>
            )}
          </TouchableOpacity>
        ))}
      </ScrollView>

      <Modal
        visible={showPicker}
        animationType="slide"
        transparent
        onRequestClose={() => setShowPicker(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>
                Pick a card for Slot {(editingSlot ?? 0) + 1}
              </Text>
              <TouchableOpacity onPress={() => setShowPicker(false)} testID="featured-modal-close">
                <Ionicons name="close" size={26} color="#fff" />
              </TouchableOpacity>
            </View>

            {saving && (
              <View style={styles.savingOverlay} pointerEvents="auto">
                <ActivityIndicator color="#39ff14" size="large" />
              </View>
            )}

            <TouchableOpacity
              style={styles.clearBtn}
              onPress={() => handleSelect(null)}
              testID="featured-clear-slot"
              disabled={saving}
            >
              <Ionicons name="trash-bin-outline" size={16} color="#ff6b6b" />
              <Text style={styles.clearBtnText}>Clear this slot</Text>
            </TouchableOpacity>

            <ScrollView contentContainerStyle={styles.gridScroll}>
              <View style={styles.grid}>
                {userCards.length === 0 && (
                  <Text style={styles.emptyText}>
                    You don't own any cards yet. Hit the shop to pull some!
                  </Text>
                )}
                {userCards.map((uc) => {
                  const isPicked = featured.includes(uc.card.id);
                  return (
                    <TouchableOpacity
                      key={uc.user_card_id}
                      style={[styles.gridCard, isPicked && styles.gridCardPicked]}
                      onPress={() => handleSelect(uc.card.id)}
                      disabled={saving}
                      testID={`featured-pick-${uc.card.id}`}
                    >
                      <ExpoImage
                        source={{ uri: cardThumb(uc.card, 160) }}
                        style={styles.gridImage}
                        contentFit="cover"
                        cachePolicy="memory-disk"
                        transition={150}
                        recyclingKey={uc.card.id}
                      />
                      {isPicked && (
                        <View style={styles.pickedBadge}>
                          <Ionicons name="checkmark" size={14} color="#000" />
                        </View>
                      )}
                    </TouchableOpacity>
                  );
                })}
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>
    </View>
  );
};

const SLOT_W = 96;
const SLOT_H = 132;

const styles = StyleSheet.create({
  container: {
    marginBottom: 24,
    paddingVertical: 14,
    paddingHorizontal: 12,
    borderRadius: 14,
    backgroundColor: 'rgba(15, 20, 15, 0.85)',
    borderWidth: 1,
    borderColor: 'rgba(57, 255, 20, 0.25)',
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    marginBottom: 4,
  },
  title: {
    color: '#39ff14',
    fontSize: 16,
    fontWeight: '900',
    letterSpacing: 1.2,
  },
  subtitle: {
    color: '#7aff7a',
    fontSize: 12,
    fontWeight: '700',
  },
  help: {
    color: '#789',
    fontSize: 11,
    marginBottom: 10,
    fontStyle: 'italic',
  },
  row: {
    gap: 10,
    paddingVertical: 4,
    paddingRight: 8,
  },
  slot: {
    width: SLOT_W,
    height: SLOT_H,
    borderRadius: 8,
    backgroundColor: '#0a0f0a',
    borderWidth: 2,
    borderColor: '#2a2a2a',
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
  },
  slotFilled: {
    borderColor: '#39ff14',
  },
  slotImage: {
    width: '100%',
    height: '100%',
  },
  slotGlow: {
    position: 'absolute',
    top: -2,
    left: -2,
    right: -2,
    bottom: -2,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: 'rgba(57, 255, 20, 0.55)',
    shadowColor: '#39ff14',
    shadowOpacity: 0.7,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 0 },
  },
  slotEmpty: {
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
  },
  slotPlus: {
    fontSize: 30,
    color: '#39ff14',
    fontWeight: '900',
    lineHeight: 32,
  },
  slotEmptyLabel: {
    color: '#666',
    fontSize: 10,
    fontWeight: '600',
  },
  // Modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.85)',
    justifyContent: 'flex-end',
  },
  modalCard: {
    backgroundColor: '#0d1410',
    borderTopLeftRadius: 18,
    borderTopRightRadius: 18,
    paddingTop: 16,
    paddingHorizontal: 16,
    paddingBottom: 24,
    maxHeight: '85%',
    borderTopWidth: 2,
    borderTopColor: '#39ff14',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  modalTitle: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '800',
  },
  clearBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    gap: 6,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    backgroundColor: 'rgba(255,107,107,0.1)',
    marginBottom: 10,
    borderWidth: 1,
    borderColor: 'rgba(255,107,107,0.3)',
  },
  clearBtnText: {
    color: '#ff6b6b',
    fontSize: 12,
    fontWeight: '700',
  },
  gridScroll: {
    paddingBottom: 12,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    justifyContent: 'flex-start',
  },
  gridCard: {
    width: 84,
    height: 116,
    borderRadius: 6,
    overflow: 'hidden',
    backgroundColor: '#000',
    borderWidth: 2,
    borderColor: '#333',
  },
  gridCardPicked: {
    borderColor: '#39ff14',
  },
  gridImage: {
    width: '100%',
    height: '100%',
  },
  pickedBadge: {
    position: 'absolute',
    top: 4,
    right: 4,
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: '#39ff14',
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyText: {
    color: '#888',
    fontSize: 13,
    padding: 16,
    textAlign: 'center',
  },
  savingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.5)',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 10,
  },
});

export default FeaturedCards;

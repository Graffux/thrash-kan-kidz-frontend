import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity, Modal, Pressable, ImageBackground } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Image as ExpoImage } from 'expo-image';
import { FONTS } from '../theme';

interface Badge {
  id: string;
  name: string;
  description: string;
  icon: string;
  tint: string;
  image_url: string | null;
  earned: boolean;
}

interface Props {
  userId: string;
  apiUrl: string;
}

/**
 * Badge Cabinet — grid of all defined badges with locked/unlocked state.
 * Fetches from /api/users/{user_id}/badges so the server stays the source
 * of truth for unlock conditions. Falls back to icon placeholders when
 * custom badge art isn't ready yet.
 */
export const BadgeCabinet: React.FC<Props> = ({ userId, apiUrl }) => {
  const [badges, setBadges] = useState<Badge[]>([]);
  const [loading, setLoading] = useState(true);
  const [earnedCount, setEarnedCount] = useState(0);
  const [selectedBadge, setSelectedBadge] = useState<Badge | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${apiUrl}/api/users/${userId}/badges`);
        const json = await res.json();
        if (!cancelled) {
          setBadges(json.badges || []);
          setEarnedCount(json.earned_count || 0);
        }
      } catch {
        // Network failure — leave state empty so the cabinet shows nothing
        // rather than half-rendered placeholders. The toast/error system
        // upstream surfaces the failure to the user already.
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [userId, apiUrl]);

  if (loading) {
    return (
      <View style={styles.loadingWrap} testID="badge-cabinet-loading">
        <ActivityIndicator color="#FFD700" />
      </View>
    );
  }

  if (badges.length === 0) return null;

  return (
    <View style={styles.wrap} testID="badge-cabinet">
      <View style={styles.header}>
        <Text style={styles.title}>BADGE CABINET</Text>
        <Text style={styles.counter}>
          {earnedCount} / {badges.length}
        </Text>
      </View>
      <View style={styles.grid}>
        {badges.map((b) => (
          <TouchableOpacity
            key={b.id}
            style={[styles.tile, !b.earned && styles.tileLocked]}
            testID={`badge-${b.id}`}
            activeOpacity={0.8}
            onPress={() => setSelectedBadge(b)}
          >
            {b.image_url ? (
              <ExpoImage
                source={{ uri: b.image_url }}
                style={[styles.image, !b.earned && styles.dimmed]}
                contentFit="contain"
                cachePolicy="memory-disk"
                transition={150}
              />
            ) : (
              <View
                style={[
                  styles.iconWrap,
                  { backgroundColor: b.earned ? b.tint : '#222' },
                ]}
              >
                <Ionicons
                  name={b.icon as any}
                  size={28}
                  color={b.earned ? '#000' : '#555'}
                />
              </View>
            )}
            <Text
              style={[styles.name, !b.earned && styles.nameLocked]}
              numberOfLines={2}
            >
              {b.name}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <Modal
        visible={selectedBadge !== null}
        transparent
        animationType="fade"
        onRequestClose={() => setSelectedBadge(null)}
      >
        <View style={styles.modalBackdrop}>
          <Pressable
            style={StyleSheet.absoluteFill}
            onPress={() => setSelectedBadge(null)}
          />

          {selectedBadge && (
            <ImageBackground
              source={require('../../assets/images/tkk_badge_modal_frame.png')}
              style={styles.modalFrame}
              imageStyle={styles.modalFrameImage}
              resizeMode="contain"
            >
              <TouchableOpacity
                style={styles.modalClose}
                onPress={() => setSelectedBadge(null)}
                activeOpacity={0.8}
              >
                <Text style={styles.modalCloseText}>X</Text>
              </TouchableOpacity>

              <View style={styles.modalContent}>
                <Text
                  style={styles.modalTitle}
                  numberOfLines={2}
                  adjustsFontSizeToFit
                >
                  {selectedBadge.name}
                </Text>

                <View style={styles.modalStatusPlate}>
                  <Text style={styles.modalStatusText}>
                    {selectedBadge.earned ? 'EARNED' : 'LOCKED'}
                  </Text>
                </View>

                <View style={styles.modalHowRow}>
                  <Text style={styles.modalSectionTitle}>HOW TO EARN</Text>
                </View>

                <View style={styles.modalDescriptionBox}>
                  <Text style={styles.modalDescription}>
                    {selectedBadge.description}
                  </Text>
                </View>

                <TouchableOpacity
                  style={styles.modalButton}
                  onPress={() => setSelectedBadge(null)}
                  activeOpacity={0.85}
                >
                  <Text style={styles.modalButtonText}>GOT IT</Text>
                </TouchableOpacity>
              </View>
            </ImageBackground>
          )}
        </View>
      </Modal>
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: {
    marginTop: 24,
    paddingHorizontal: 12,
  },
  loadingWrap: {
    paddingVertical: 20,
    alignItems: 'center',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    marginBottom: 12,
    paddingHorizontal: 4,
  },
  title: {
    color: '#FFD700',
    fontSize: 18,
    fontWeight: '900',
    letterSpacing: 2,
  },
  counter: {
    color: '#888',
    fontSize: 12,
    fontWeight: '700',
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'flex-start',
    gap: 10,
  },
  // Tile width is explicit instead of `width: '30%'` + `aspectRatio` —
  // the percentage+aspectRatio combo has been known to render at 0×0
  // on Android when the parent's row width hasn't been measured yet.
  tile: {
    width: '31%',
    minHeight: 110,
    backgroundColor: 'rgba(20,20,20,0.7)',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(255,215,0,0.25)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 8,
  },
  tileLocked: {
    opacity: 0.55,
    borderColor: 'rgba(255,255,255,0.06)',
  },
  iconWrap: {
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 6,
  },
  image: {
    width: 64,
    height: 64,
    marginBottom: 6,
  },
  dimmed: {
    opacity: 0.4,
  },
  name: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '700',
    textAlign: 'center',
  },
  nameLocked: {
    color: '#777',
  },


  modalFrame: {
    width: '100%',
    maxWidth: 410,
    aspectRatio: 1024 / 1536,
    alignSelf: 'center',
    position: 'relative',
  },

  modalFrameImage: {
    width: '100%',
    height: '100%',
  },
  modalBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.84)',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 22,
  },
  modalCard: {
    width: '100%',
    maxWidth: 420,
    backgroundColor: '#080b08',
    borderWidth: 2,
    borderColor: '#57b51f',
    borderRadius: 14,
    padding: 20,
    shadowColor: '#39ff14',
    shadowOpacity: 0.45,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 0 },
    elevation: 18,
  },
  modalContent: {
    ...StyleSheet.absoluteFillObject,
  },

  modalClose: {
    position: 'absolute',
    top: '4.5%',
    right: '5%',
    width: '13%',
    aspectRatio: 1,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 10,
  },

  modalCloseText: {
    color: '#ffffff',
    fontSize: 22,
    fontWeight: '900',
    textAlign: 'center',
  },

  modalTitle: {
    position: 'absolute',
    top: '22.0%',
    left: '14%',
    right: '14%',
    height: '7.5%',
    color: '#8dff32',
    fontSize: 24,
    fontWeight: '900',
    letterSpacing: 1,
    textAlign: 'center',
    textAlignVertical: 'center',
    transform: [{ translateY: -22 }],
    textTransform: 'uppercase',
  },

  modalStatusPlate: {
    position: 'absolute',
    top: '27.2%',
    left: '25%',
    right: '25%',
    height: '6.3%',
    alignItems: 'center',
    justifyContent: 'center',
  },

  modalStatusText: {
    color: '#ffffff',
    fontSize: 19,
    fontWeight: '900',
    letterSpacing: 1.2,
    textAlign: 'center',
    transform: [{ translateY: 12 }],
  },

  modalHowRow: {
    position: 'absolute',
    top: '36.3%',
    left: '17%',
    right: '17%',
    height: '6%',
    alignItems: 'center',
    justifyContent: 'center',
  },

  modalSectionTitle: {
    color: '#8dff32',
    fontSize: 18,
    lineHeight: 22,
    fontWeight: '900',
    letterSpacing: 1,
    textAlign: 'center',
  },

  modalDescriptionBox: {
    position: 'absolute',
    top: '45%',
    left: '19%',
    right: '19%',
    height: '24%',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 8,
  },

  modalDescription: {
    color: '#ffffff',
    fontSize: 15,
    lineHeight: 20,
    fontWeight: '700',
    textAlign: 'center',
  },

  modalButton: {
    position: 'absolute',
    left: '23%',
    right: '23%',
    bottom: '7.2%',
    height: '11%',
    alignItems: 'center',
    justifyContent: 'center',
  },

  modalButtonText: {
    color: '#8dff32',
    fontSize: 18,
    fontWeight: '900',
    letterSpacing: 1,
    textAlign: 'center',
    textAlignVertical: 'center',
    transform: [{ translateY: -22 }],
    includeFontPadding: false,
    width: '100%',
    height: '100%',
  },
});











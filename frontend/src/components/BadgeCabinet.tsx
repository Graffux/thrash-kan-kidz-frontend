import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Image as ExpoImage } from 'expo-image';

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
      <View style={styles.loadingWrap} data-testid="badge-cabinet-loading">
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
          <View
            key={b.id}
            style={[styles.tile, !b.earned && styles.tileLocked]}
            testID={`badge-${b.id}`}
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
          </View>
        ))}
      </View>
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
});

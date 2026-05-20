import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Image as ExpoImage } from 'expo-image';
import { FONTS } from '../theme';

// Server-side shape from /api/ranks and the `rank` field on user payloads.
export interface Rank {
  id: string;
  name: string;
  crest_url: string;
  min_series_cleared: number;
}

type Size = 'sm' | 'md' | 'lg';

// Sizes are tuned for the contexts where this component appears:
// sm = inline next to a username (header rows, leaderboard rows)
// md = below a username on a profile card
// lg = the hero crest on the Profile page
const DIMENSIONS: Record<Size, { crest: number; label: number }> = {
  sm: { crest: 28, label: 10 },
  md: { crest: 64, label: 12 },
  lg: { crest: 120, label: 16 },
};

interface Props {
  rank?: Rank | null;
  size?: Size;
  showLabel?: boolean;
}

/**
 * Displays a player's rank crest. Defensive against `rank` being null/undefined
 * (older clients, mid-load states) — falls back to nothing rather than crashing.
 */
export const RankCrest: React.FC<Props> = ({ rank, size = 'sm', showLabel = false }) => {
  if (!rank?.crest_url) return null;
  const dim = DIMENSIONS[size];
  return (
    <View style={styles.wrap} data-testid={`rank-crest-${rank.id}`}>
      <ExpoImage
        source={{ uri: rank.crest_url }}
        style={{ width: dim.crest, height: dim.crest }}
        contentFit="contain"
        transition={200}
      />
      {showLabel && (
        <Text style={[styles.label, { fontSize: dim.label }]} numberOfLines={1}>
          {rank.name.toUpperCase()}
        </Text>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  label: {
    color: '#FFD700',
    fontFamily: FONTS.metal,
    fontWeight: '900',
    letterSpacing: 2,
    marginTop: 4,
    textShadowColor: '#000',
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 2,
  },
});

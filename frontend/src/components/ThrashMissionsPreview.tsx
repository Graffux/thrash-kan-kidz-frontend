/**
 * ThrashMissionsPreview — top 3 active goals on Home with progress bars.
 * Tap any to jump to /goals.
 */
import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useApp } from '../context/AppContext';
import { SplatTitle } from './SplatTitle';

export const ThrashMissionsPreview: React.FC = () => {
  const router = useRouter();
  const { userGoals } = useApp();

  // Prefer in-progress (incomplete + has progress > 0), then incomplete, then completed.
  const active = [...userGoals]
    .filter((g) => !g.user_goal.completed)
    .sort((a, b) => {
      const pa = a.user_goal.progress || 0;
      const pb = b.user_goal.progress || 0;
      return pb - pa;
    })
    .slice(0, 3);

  if (active.length === 0) return null;

  return (
    <View style={styles.wrap} testID="thrash-missions-preview">
      <View style={styles.headerRow}>
        <SplatTitle>THRASH MISSIONS</SplatTitle>
        <TouchableOpacity
          onPress={() => router.push('/goals')}
          style={styles.viewAllBtn}
          testID="missions-view-all"
        >
          <Text style={styles.viewAllText}>VIEW ALL</Text>
          <Ionicons name="chevron-forward" size={14} color="#9aff5a" />
        </TouchableOpacity>
      </View>

      {active.map((g) => {
        const pct = g.goal.target_value > 0
          ? Math.min(100, Math.round(((g.user_goal.progress || 0) / g.goal.target_value) * 100))
          : 0;
        return (
          <TouchableOpacity
            key={g.user_goal.id}
            style={styles.row}
            onPress={() => router.push('/goals')}
            activeOpacity={0.85}
            testID={`mission-${g.user_goal.id}`}
          >
            <View style={styles.rowHeader}>
              <Text style={styles.rowTitle} numberOfLines={1}>{g.goal.title}</Text>
              <Text style={styles.rowReward}>+{g.goal.reward_coins}🪙</Text>
            </View>
            <View style={styles.barBg}>
              <View style={[styles.bar, { width: `${pct}%` }]} />
            </View>
            <Text style={styles.progressText}>
              {g.user_goal.progress || 0} / {g.goal.target_value} • {pct}%
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: { marginBottom: 24 },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  viewAllBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
    paddingHorizontal: 4,
    paddingBottom: 6,
  },
  viewAllText: {
    color: '#9aff5a',
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 1,
  },
  row: {
    backgroundColor: 'rgba(20, 25, 20, 0.85)',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(57, 255, 20, 0.2)',
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginBottom: 8,
  },
  rowHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  rowTitle: {
    color: '#fff',
    fontSize: 13,
    fontWeight: '700',
    flex: 1,
    paddingRight: 8,
  },
  rowReward: { color: '#ffd24a', fontSize: 12, fontWeight: '800' },
  barBg: {
    height: 6,
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderRadius: 3,
    overflow: 'hidden',
    marginBottom: 4,
  },
  bar: { height: '100%', backgroundColor: '#39ff14', borderRadius: 3 },
  progressText: { color: '#789', fontSize: 10, fontWeight: '600' },
});

export default ThrashMissionsPreview;

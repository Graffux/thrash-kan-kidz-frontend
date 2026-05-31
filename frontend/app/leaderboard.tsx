/**
 * Leaderboard — composite ranking with switchable metric tabs.
 *
 * Routes to /leaderboard (hidden tab). Accessed from a stat panel tap or
 * Home gear → settings shortcut later. URL param `?metric=` selects the
 * initial tab.
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';
import { useApp } from '../src/context/AppContext';
import { GrungeBackground } from '../src/components/GrungeBackground';
import { SplatTitle } from '../src/components/SplatTitle';

type Metric = 'composite' | 'cards' | 'coins' | 'series' | 'streak';

interface Row {
  rank: number;
  user_id: string;
  username: string;
  score: number;
  cards_count: number;
  coins: number;
  completed_series: number;
  daily_streak: number;
}

const TABS: { id: Metric; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { id: 'composite', label: 'OVERALL', icon: 'trophy' },
  { id: 'cards', label: 'CARDS', icon: 'albums' },
  { id: 'coins', label: 'COINS', icon: 'cash' },
  { id: 'series', label: 'SERIES', icon: 'medal' },
  { id: 'streak', label: 'STREAK', icon: 'flame' },
];

const metricLabel = (m: Metric, r: Row): string => {
  switch (m) {
    case 'cards': return `${r.cards_count} cards`;
    case 'coins': return `${r.coins.toLocaleString()} 🪙`;
    case 'series': return `${r.completed_series} complete`;
    case 'streak': return `${r.daily_streak}d streak`;
    default: return `${r.score.toLocaleString()} pts`;
  }
};

export default function LeaderboardScreen() {
  const router = useRouter();
  const { user, apiUrl } = useApp();
  const [metric, setMetric] = useState<Metric>('composite');
  const [rows, setRows] = useState<Row[]>([]);
  const [viewer, setViewer] = useState<Row | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (m: Metric) => {
    if (!user) return;
    try {
      const res = await axios.get(
        `${apiUrl}/api/leaderboard?metric=${m}&limit=100&viewer_id=${user.id}`,
      );
      setRows(res.data.rows);
      setViewer(res.data.viewer);
    } catch {
      // silent
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [apiUrl, user]);

  useEffect(() => { setLoading(true); load(metric); }, [metric, load]);

  if (!user) {
    return (
      <GrungeBackground>
        <SafeAreaView style={styles.container}>
          <View style={styles.center}><Text style={styles.muted}>Login required.</Text></View>
        </SafeAreaView>
      </GrungeBackground>
    );
  }

  const viewerInTop = viewer && rows.some((r) => r.user_id === viewer.user_id);

  return (
    <GrungeBackground>
      <SafeAreaView style={styles.container}>
        <View style={styles.topBar}>
          <TouchableOpacity onPress={() => router.back()} testID="lb-back-btn">
            <Ionicons name="chevron-back" size={28} color="#9aff5a" />
          </TouchableOpacity>
          <Image
            // eslint-disable-next-line @typescript-eslint/no-require-imports
            source={require('../src/assets/headers/leaderboard_logo.png')}
            style={styles.headerLogo}
            resizeMode="contain"
            testID="leaderboard-header-logo"
          />
          <View style={{ width: 28 }} />
        </View>

        {/* Metric tabs */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.tabsRow}>
          {TABS.map((t) => {
            const active = metric === t.id;
            return (
              <TouchableOpacity
                key={t.id}
                style={[styles.tab, active && styles.tabActive]}
                onPress={() => setMetric(t.id)}
                testID={`lb-tab-${t.id}`}
              >
                <Ionicons
                  name={t.icon}
                  size={16}
                  color={active ? '#000' : '#9aff5a'}
                  style={styles.tabIcon}
                />
                <Text
                  style={[styles.tabText, active && styles.tabTextActive]}
                  numberOfLines={1}
                >
                  {t.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>

        <ScrollView
          contentContainerStyle={styles.scroll}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => { setRefreshing(true); load(metric); }}
              tintColor="#39ff14"
            />
          }
        >
          <SplatTitle>TOP 100</SplatTitle>

          {loading ? (
            <View style={styles.center}><ActivityIndicator color="#39ff14" size="large" /></View>
          ) : rows.length === 0 ? (
            <View style={styles.emptyCard}>
              <Text style={styles.muted}>No rankings yet.</Text>
            </View>
          ) : (
            rows.map((r) => {
              const isViewer = r.user_id === user.id;
              const podium =
                r.rank === 1 ? '#FFD700' :
                r.rank === 2 ? '#C0C0C0' :
                r.rank === 3 ? '#cd7f32' : null;
              return (
                <TouchableOpacity
                  key={r.user_id}
                  style={[
                    styles.row,
                    isViewer && styles.rowViewer,
                    podium && { borderColor: podium },
                  ]}
                  onPress={() => router.push(`/profile?userId=${r.user_id}` as any)}
                  testID={`lb-row-${r.rank}`}
                >
                  <View style={[styles.rankBadge, podium && { backgroundColor: podium }]}>
                    <Text style={[styles.rankText, podium && { color: '#000' }]}>
                      {r.rank === 1 ? '🥇' : r.rank === 2 ? '🥈' : r.rank === 3 ? '🥉' : `#${r.rank}`}
                    </Text>
                  </View>
                  <View style={styles.userBlock}>
                    <Text style={[styles.userName, isViewer && { color: '#39ff14' }]} numberOfLines={1}>
                      {r.username}{isViewer ? ' (YOU)' : ''}
                    </Text>
                    <Text style={styles.userSub}>{metricLabel(metric, r)}</Text>
                  </View>
                  <Text style={styles.score}>{r.score.toLocaleString()}</Text>
                </TouchableOpacity>
              );
            })
          )}
        </ScrollView>

        {/* Pinned viewer row when not in top 100 */}
        {!loading && viewer && !viewerInTop && (
          <View style={styles.pinnedWrap}>
            <Text style={styles.pinnedHeader}>YOUR RANK</Text>
            <View style={[styles.row, styles.rowViewer, styles.rowPinned]}>
              <View style={styles.rankBadge}>
                <Text style={styles.rankText}>#{viewer.rank}</Text>
              </View>
              <View style={styles.userBlock}>
                <Text style={[styles.userName, { color: '#39ff14' }]}>{viewer.username} (YOU)</Text>
                <Text style={styles.userSub}>{metricLabel(metric, viewer)}</Text>
              </View>
              <Text style={styles.score}>{viewer.score.toLocaleString()}</Text>
            </View>
          </View>
        )}
      </SafeAreaView>
    </GrungeBackground>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: 'transparent' },
  center: { padding: 32, alignItems: 'center', justifyContent: 'center' },
  muted: { color: '#789', fontSize: 13 },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 4,
  },
  pageTitle: { color: '#39ff14', fontSize: 18, fontWeight: '900', letterSpacing: 3 },
  headerLogo: { width: 200, height: 64 },
  tabsRow: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    gap: 10,
  },
  tab: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 10,
    borderWidth: 1.5,
    borderColor: 'rgba(57, 255, 20, 0.5)',
    backgroundColor: 'rgba(20,25,20,0.9)',
  },
  tabIcon: {
    marginRight: 8,
  },
  tabActive: { backgroundColor: '#39ff14', borderColor: '#39ff14' },
  tabText: {
    color: '#9aff5a',
    fontSize: 13,
    fontWeight: '900',
    letterSpacing: 1.2,
    includeFontPadding: false,
  },
  tabTextActive: { color: '#000' },
  scroll: { padding: 16, paddingBottom: 24 },
  emptyCard: {
    backgroundColor: 'rgba(20, 25, 20, 0.85)',
    borderRadius: 10,
    padding: 24,
    alignItems: 'center',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(20,25,20,0.85)',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(57, 255, 20, 0.18)',
    paddingHorizontal: 10,
    paddingVertical: 10,
    marginBottom: 6,
    gap: 12,
  },
  rowViewer: { borderColor: '#39ff14', backgroundColor: 'rgba(57,255,20,0.08)' },
  rankBadge: {
    width: 44,
    height: 32,
    borderRadius: 6,
    backgroundColor: '#241a14',
    borderWidth: 1,
    borderColor: '#3a2a20',
    alignItems: 'center',
    justifyContent: 'center',
  },
  rankText: { color: '#fff', fontSize: 13, fontWeight: '900' },
  userBlock: { flex: 1 },
  userName: { color: '#fff', fontSize: 14, fontWeight: '800' },
  userSub: { color: '#789', fontSize: 11, marginTop: 1 },
  score: { color: '#ffd24a', fontSize: 15, fontWeight: '900' },

  pinnedWrap: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 12,
    backgroundColor: 'rgba(10,13,10,0.95)',
    borderTopWidth: 1,
    borderTopColor: '#39ff14',
  },
  pinnedHeader: {
    color: '#9aff5a',
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 2,
    marginBottom: 4,
    textAlign: 'center',
  },
  rowPinned: { marginBottom: 0 },
});

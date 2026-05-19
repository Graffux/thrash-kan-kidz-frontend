/**
 * MoshPitPreview — Home widget showing latest 3 posts from /api/mosh/feed.
 * "VIEW MOSH PIT" CTA pushes to /mosh.
 */
import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter, useFocusEffect } from 'expo-router';
import axios from 'axios';
import { useApp } from '../context/AppContext';
import { SplatTitle } from './SplatTitle';

interface MoshPost {
  id: string;
  username: string;
  content: string;
  created_at: string;
  reaction_count: number;
  viewer_reacted: boolean;
}

const relativeTime = (iso: string): string => {
  const ms = Date.now() - new Date(iso).getTime();
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h`;
  const d = Math.floor(h / 24);
  return `${d}d`;
};

export const MoshPitPreview: React.FC = () => {
  const router = useRouter();
  const { user, apiUrl } = useApp();
  const [posts, setPosts] = useState<MoshPost[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const res = await axios.get(
        `${apiUrl}/api/mosh/feed?limit=3${user ? `&viewer_id=${user.id}` : ''}`,
      );
      setPosts(res.data);
    } catch {
      // silent fail — empty state will handle it
    } finally {
      setLoading(false);
    }
  }, [apiUrl, user]);

  useEffect(() => { load(); }, [load]);
  // Refresh whenever Home gets focus (e.g. user came back from /mosh)
  useFocusEffect(useCallback(() => { load(); }, [load]));

  return (
    <View style={styles.wrap} testID="mosh-preview">
      <View style={styles.headerRow}>
        <SplatTitle>MOSH PIT</SplatTitle>
        <TouchableOpacity
          onPress={() => router.push('/mosh')}
          style={styles.viewAllBtn}
          testID="mosh-view-all"
        >
          <Text style={styles.viewAllText}>VIEW FEED</Text>
          <Ionicons name="chevron-forward" size={14} color="#9aff5a" />
        </TouchableOpacity>
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator color="#39ff14" /></View>
      ) : posts.length === 0 ? (
        <TouchableOpacity
          style={styles.emptyCard}
          onPress={() => router.push('/mosh')}
          testID="mosh-empty"
        >
          <Ionicons name="chatbubbles-outline" size={28} color="#39ff14" />
          <Text style={styles.emptyText}>Be the first to post!</Text>
          <Text style={styles.emptySub}>Tap to open Mosh Pit</Text>
        </TouchableOpacity>
      ) : (
        posts.map((p) => (
          <TouchableOpacity
            key={p.id}
            style={styles.post}
            onPress={() => router.push('/mosh')}
            activeOpacity={0.85}
            testID={`mosh-preview-post-${p.id}`}
          >
            <View style={styles.postHead}>
              <Text style={styles.postUser}>{p.username}</Text>
              <Text style={styles.postTime}>{relativeTime(p.created_at)}</Text>
            </View>
            <Text style={styles.postContent} numberOfLines={2}>{p.content}</Text>
            <View style={styles.postFoot}>
              <Ionicons
                name={p.viewer_reacted ? 'skull' : 'skull-outline'}
                size={14}
                color={p.viewer_reacted ? '#39ff14' : '#789'}
              />
              <Text style={[
                styles.reactCount,
                p.viewer_reacted && { color: '#39ff14' },
              ]}>
                {p.reaction_count}
              </Text>
            </View>
          </TouchableOpacity>
        ))
      )}
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
  viewAllText: { color: '#9aff5a', fontSize: 11, fontWeight: '900', letterSpacing: 1 },
  center: { padding: 24, alignItems: 'center' },
  emptyCard: {
    backgroundColor: 'rgba(20, 25, 20, 0.85)',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(57, 255, 20, 0.25)',
    padding: 24,
    alignItems: 'center',
    gap: 4,
  },
  emptyText: { color: '#fff', fontSize: 14, fontWeight: '800' },
  emptySub: { color: '#789', fontSize: 11 },
  post: {
    backgroundColor: 'rgba(20, 25, 20, 0.85)',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(57, 255, 20, 0.2)',
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginBottom: 8,
  },
  postHead: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  postUser: { color: '#9aff5a', fontSize: 12, fontWeight: '900', letterSpacing: 0.5 },
  postTime: { color: '#456', fontSize: 10 },
  postContent: { color: '#cde', fontSize: 13, lineHeight: 18 },
  postFoot: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 6,
  },
  reactCount: { color: '#789', fontSize: 11, fontWeight: '700' },
});

export default MoshPitPreview;

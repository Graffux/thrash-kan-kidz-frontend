/**
 * Mosh Pit — full community feed screen pushed via Home widget.
 *
 * - Composer at top (200ch text post)
 * - Feed list (newest first)
 * - Each post: skull react toggle, delete button (own posts only)
 * - Pull to refresh
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';
import { useApp } from '../src/context/AppContext';
import { GrungeBackground } from '../src/components/GrungeBackground';
import { SplatTitle } from '../src/components/SplatTitle';

interface MoshPost {
  id: string;
  user_id: string;
  username: string;
  content: string;
  created_at: string;
  reaction_count: number;
  viewer_reacted: boolean;
}

const relativeTime = (iso: string): string => {
  const ms = Date.now() - new Date(iso).getTime();
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
};

const MAX_LEN = 200;

export default function MoshPitScreen() {
  const router = useRouter();
  const { user, apiUrl } = useApp();
  const [posts, setPosts] = useState<MoshPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [composing, setComposing] = useState('');
  const [posting, setPosting] = useState(false);

  const load = useCallback(async () => {
    if (!user) return;
    try {
      const res = await axios.get(
        `${apiUrl}/api/mosh/feed?limit=50&viewer_id=${user.id}`,
      );
      setPosts(res.data);
    } catch {
      Alert.alert('Error', 'Failed to load Mosh Pit feed.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [apiUrl, user]);

  useEffect(() => { load(); }, [load]);

  const handlePost = async () => {
    if (!user) return;
    const trimmed = composing.trim();
    if (!trimmed) return Alert.alert('Empty post', 'Write something first.');
    setPosting(true);
    try {
      const res = await axios.post(`${apiUrl}/api/mosh/posts`, {
        user_id: user.id,
        content: trimmed,
      });
      setPosts((prev) => [res.data, ...prev]);
      setComposing('');
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'Failed to post.';
      Alert.alert('Error', msg);
    } finally {
      setPosting(false);
    }
  };

  const handleReact = async (postId: string) => {
    if (!user) return;
    // Optimistic toggle
    setPosts((prev) => prev.map((p) => p.id === postId ? {
      ...p,
      viewer_reacted: !p.viewer_reacted,
      reaction_count: p.viewer_reacted ? p.reaction_count - 1 : p.reaction_count + 1,
    } : p));
    try {
      const res = await axios.post(
        `${apiUrl}/api/mosh/posts/${postId}/react`,
        { user_id: user.id },
      );
      // Sync with server truth in case optimistic was off
      setPosts((prev) => prev.map((p) => p.id === postId ? res.data : p));
    } catch {
      // Revert by reloading
      load();
    }
  };

  const handleDelete = (postId: string) => {
    if (!user) return;
    Alert.alert('Delete post?', 'This can\'t be undone.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await axios.delete(`${apiUrl}/api/mosh/posts/${postId}`, {
              data: { user_id: user.id },
            });
            setPosts((prev) => prev.filter((p) => p.id !== postId));
          } catch (e: any) {
            const msg = e?.response?.data?.detail || 'Failed to delete.';
            Alert.alert('Error', msg);
          }
        },
      },
    ]);
  };

  if (!user) {
    return (
      <GrungeBackground>
        <SafeAreaView style={styles.container}>
          <View style={styles.center}>
            <Text style={styles.locked}>Login to enter the Mosh Pit.</Text>
          </View>
        </SafeAreaView>
      </GrungeBackground>
    );
  }

  return (
    <GrungeBackground>
      <SafeAreaView style={styles.container}>
        {/* Header */}
        <View style={styles.topBar}>
          <TouchableOpacity onPress={() => router.back()} testID="mosh-back-btn">
            <Ionicons name="chevron-back" size={28} color="#9aff5a" />
          </TouchableOpacity>
          <Text style={styles.pageTitle}>MOSH PIT</Text>
          <View style={{ width: 28 }} />
        </View>

        <ScrollView
          contentContainerStyle={styles.scroll}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => { setRefreshing(true); load(); }}
              tintColor="#39ff14"
            />
          }
        >
          {/* Composer */}
          <View style={styles.composer}>
            <SplatTitle>WHAT'S ON YOUR MIND?</SplatTitle>
            <TextInput
              style={styles.composerInput}
              placeholder="Drop a hot take, share a pull, post a roast..."
              placeholderTextColor="#666"
              value={composing}
              onChangeText={setComposing}
              multiline
              maxLength={MAX_LEN}
              testID="mosh-composer-input"
            />
            <View style={styles.composerFoot}>
              <Text style={styles.charCount}>{composing.length}/{MAX_LEN}</Text>
              <TouchableOpacity
                style={[styles.postBtn, (!composing.trim() || posting) && styles.postBtnDisabled]}
                onPress={handlePost}
                disabled={!composing.trim() || posting}
                testID="mosh-post-btn"
              >
                {posting ? (
                  <ActivityIndicator size="small" color="#000" />
                ) : (
                  <>
                    <Ionicons name="send" size={14} color="#000" />
                    <Text style={styles.postBtnText}>POST</Text>
                  </>
                )}
              </TouchableOpacity>
            </View>
          </View>

          {/* Feed */}
          <SplatTitle>FEED</SplatTitle>
          {loading ? (
            <View style={styles.center}><ActivityIndicator color="#39ff14" size="large" /></View>
          ) : posts.length === 0 ? (
            <View style={styles.emptyCard}>
              <Ionicons name="megaphone-outline" size={36} color="#39ff14" />
              <Text style={styles.emptyText}>It's silent in here.</Text>
              <Text style={styles.emptySub}>Be the first to post!</Text>
            </View>
          ) : (
            posts.map((p) => (
              <View key={p.id} style={styles.post} testID={`mosh-post-${p.id}`}>
                <View style={styles.postHead}>
                  <TouchableOpacity
                    onPress={() => router.push(`/profile?userId=${p.user_id}` as any)}
                  >
                    <Text style={styles.postUser}>{p.username}</Text>
                  </TouchableOpacity>
                  <View style={styles.postHeadRight}>
                    <Text style={styles.postTime}>{relativeTime(p.created_at)}</Text>
                    {p.user_id === user.id && (
                      <TouchableOpacity
                        onPress={() => handleDelete(p.id)}
                        testID={`mosh-delete-${p.id}`}
                      >
                        <Ionicons name="trash-outline" size={16} color="#ff6b6b" />
                      </TouchableOpacity>
                    )}
                  </View>
                </View>
                <Text style={styles.postContent}>{p.content}</Text>
                <TouchableOpacity
                  style={[styles.reactBtn, p.viewer_reacted && styles.reactBtnActive]}
                  onPress={() => handleReact(p.id)}
                  testID={`mosh-react-${p.id}`}
                >
                  <Ionicons
                    name={p.viewer_reacted ? 'skull' : 'skull-outline'}
                    size={16}
                    color={p.viewer_reacted ? '#39ff14' : '#789'}
                  />
                  <Text style={[
                    styles.reactCount,
                    p.viewer_reacted && { color: '#39ff14' },
                  ]}>
                    {p.reaction_count}
                  </Text>
                </TouchableOpacity>
              </View>
            ))
          )}
          <View style={{ height: 24 }} />
        </ScrollView>
      </SafeAreaView>
    </GrungeBackground>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: 'transparent' },
  center: { padding: 32, alignItems: 'center', justifyContent: 'center' },
  locked: { color: '#aaa', fontSize: 14 },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 4,
  },
  pageTitle: { color: '#39ff14', fontSize: 18, fontWeight: '900', letterSpacing: 3 },
  scroll: { padding: 16, paddingBottom: 40 },
  composer: { marginBottom: 24 },
  composerInput: {
    backgroundColor: 'rgba(20, 25, 20, 0.85)',
    color: '#fff',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(57, 255, 20, 0.25)',
    padding: 14,
    minHeight: 80,
    textAlignVertical: 'top',
    fontSize: 14,
  },
  composerFoot: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 8,
  },
  charCount: { color: '#789', fontSize: 11 },
  postBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#39ff14',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
  },
  postBtnDisabled: { opacity: 0.4 },
  postBtnText: { color: '#000', fontSize: 12, fontWeight: '900', letterSpacing: 1 },
  emptyCard: {
    backgroundColor: 'rgba(20, 25, 20, 0.85)',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(57, 255, 20, 0.25)',
    padding: 32,
    alignItems: 'center',
    gap: 8,
  },
  emptyText: { color: '#fff', fontSize: 16, fontWeight: '800' },
  emptySub: { color: '#789', fontSize: 12 },
  post: {
    backgroundColor: 'rgba(20, 25, 20, 0.85)',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(57, 255, 20, 0.2)',
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginBottom: 10,
  },
  postHead: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  postHeadRight: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  postUser: {
    color: '#9aff5a',
    fontSize: 13,
    fontWeight: '900',
    letterSpacing: 0.5,
    textDecorationLine: 'underline',
  },
  postTime: { color: '#456', fontSize: 11 },
  postContent: { color: '#fff', fontSize: 14, lineHeight: 20 },
  reactBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    alignSelf: 'flex-start',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    marginTop: 8,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
  },
  reactBtnActive: { borderColor: '#39ff14', backgroundColor: 'rgba(57,255,20,0.08)' },
  reactCount: { color: '#789', fontSize: 12, fontWeight: '700' },
});

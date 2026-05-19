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
  Image,
  Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import * as ImageManipulator from 'expo-image-manipulator';
import axios from 'axios';
import { useApp } from '../src/context/AppContext';
import { GrungeBackground } from '../src/components/GrungeBackground';
import { SplatTitle } from '../src/components/SplatTitle';
import { MoshComments } from '../src/components/MoshComments';

interface MoshPost {
  id: string;
  user_id: string;
  username: string;
  content: string;
  image?: string | null;
  created_at: string;
  reaction_count: number;
  viewer_reacted: boolean;
  comment_count: number;
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
  const { user, userCards, apiUrl } = useApp();
  const [posts, setPosts] = useState<MoshPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [composing, setComposing] = useState('');
  const [posting, setPosting] = useState(false);
  // Attached image (data URI) for the upcoming post.
  const [attachedImage, setAttachedImage] = useState<string | null>(null);
  const [showCardPicker, setShowCardPicker] = useState(false);
  const [showAttachMenu, setShowAttachMenu] = useState(false);

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
    if (!trimmed && !attachedImage) return Alert.alert('Empty', 'Add text or an image.');
    setPosting(true);
    try {
      const res = await axios.post(`${apiUrl}/api/mosh/posts`, {
        user_id: user.id,
        content: trimmed,
        image: attachedImage,
      });
      setPosts((prev) => [res.data, ...prev]);
      setComposing('');
      setAttachedImage(null);
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'Failed to post.';
      Alert.alert('Error', msg);
    } finally {
      setPosting(false);
    }
  };

  // Convert remote image URL → base64 data URI (for collection card pulls)
  const attachFromUrl = async (url: string) => {
    try {
      const manipulated = await ImageManipulator.manipulateAsync(
        url,
        [{ resize: { width: 600 } }],
        { compress: 0.7, format: ImageManipulator.SaveFormat.JPEG, base64: true },
      );
      if (!manipulated.base64) throw new Error('No base64');
      setAttachedImage(`data:image/jpeg;base64,${manipulated.base64}`);
      setShowCardPicker(false);
      setShowAttachMenu(false);
    } catch {
      Alert.alert('Error', 'Could not attach card image.');
    }
  };

  // Device picker → resize → base64
  const pickFromDevice = async () => {
    setShowAttachMenu(false);
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) {
      return Alert.alert('Permission needed', 'Photo library access is required.');
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      quality: 0.7,
    });
    if (result.canceled || !result.assets?.length) return;
    try {
      const asset = result.assets[0];
      const manipulated = await ImageManipulator.manipulateAsync(
        asset.uri,
        [{ resize: { width: 800 } }],
        { compress: 0.7, format: ImageManipulator.SaveFormat.JPEG, base64: true },
      );
      if (!manipulated.base64) throw new Error('No base64');
      const dataUri = `data:image/jpeg;base64,${manipulated.base64}`;
      // Guard against >1MB final payload
      if (dataUri.length > 1_400_000) {
        return Alert.alert('Too large', 'Pick a smaller image.');
      }
      setAttachedImage(dataUri);
    } catch {
      Alert.alert('Error', 'Could not process image.');
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
            {attachedImage && (
              <View style={styles.attachedPreview} testID="composer-attached-preview">
                <Image source={{ uri: attachedImage }} style={styles.attachedImage} resizeMode="cover" />
                <TouchableOpacity
                  style={styles.removeAttachBtn}
                  onPress={() => setAttachedImage(null)}
                  testID="composer-remove-attach"
                >
                  <Ionicons name="close" size={16} color="#fff" />
                </TouchableOpacity>
              </View>
            )}
            <View style={styles.composerFoot}>
              <View style={styles.composerLeft}>
                <TouchableOpacity
                  style={styles.attachBtn}
                  onPress={() => setShowAttachMenu(true)}
                  testID="composer-attach-btn"
                >
                  <Ionicons name="image" size={20} color="#39ff14" />
                </TouchableOpacity>
                <Text style={styles.charCount}>{composing.length}/{MAX_LEN}</Text>
              </View>
              <TouchableOpacity
                style={[styles.postBtn, (!composing.trim() && !attachedImage || posting) && styles.postBtnDisabled]}
                onPress={handlePost}
                disabled={(!composing.trim() && !attachedImage) || posting}
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
                {p.image && (
                  <Image
                    source={{ uri: p.image }}
                    style={styles.postImage}
                    resizeMode="cover"
                  />
                )}
                <View style={styles.postActions}>
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
                <MoshComments
                  postId={p.id}
                  initialCount={p.comment_count}
                  onCountChange={(n) =>
                    setPosts((prev) => prev.map((x) =>
                      x.id === p.id ? { ...x, comment_count: n } : x
                    ))
                  }
                />
              </View>
            ))
          )}
          <View style={{ height: 24 }} />
        </ScrollView>

        {/* Attach menu — choose source */}
        <Modal
          visible={showAttachMenu}
          transparent
          animationType="fade"
          onRequestClose={() => setShowAttachMenu(false)}
        >
          <TouchableOpacity
            style={styles.attachOverlay}
            activeOpacity={1}
            onPress={() => setShowAttachMenu(false)}
          >
            <View style={styles.attachSheet}>
              <Text style={styles.attachTitle}>ATTACH IMAGE</Text>
              <TouchableOpacity
                style={styles.attachOption}
                onPress={() => { setShowAttachMenu(false); setShowCardPicker(true); }}
                testID="attach-from-collection"
              >
                <Ionicons name="albums" size={22} color="#39ff14" />
                <View style={{ flex: 1 }}>
                  <Text style={styles.attachOptionTitle}>From Collection</Text>
                  <Text style={styles.attachOptionSub}>Share a card you own</Text>
                </View>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.attachOption}
                onPress={pickFromDevice}
                testID="attach-from-device"
              >
                <Ionicons name="image" size={22} color="#39ff14" />
                <View style={{ flex: 1 }}>
                  <Text style={styles.attachOptionTitle}>From Device</Text>
                  <Text style={styles.attachOptionSub}>Pick from photo gallery</Text>
                </View>
              </TouchableOpacity>
            </View>
          </TouchableOpacity>
        </Modal>

        {/* Card picker — grid of owned cards */}
        <Modal
          visible={showCardPicker}
          animationType="slide"
          transparent
          onRequestClose={() => setShowCardPicker(false)}
        >
          <View style={styles.cardPickerOverlay}>
            <View style={styles.cardPickerSheet}>
              <View style={styles.cardPickerHead}>
                <Text style={styles.cardPickerTitle}>Pick a card to share</Text>
                <TouchableOpacity onPress={() => setShowCardPicker(false)} testID="card-picker-close">
                  <Ionicons name="close" size={26} color="#fff" />
                </TouchableOpacity>
              </View>
              <ScrollView contentContainerStyle={styles.cardPickerGrid}>
                {userCards.length === 0 && (
                  <Text style={styles.muted}>You don't own any cards yet.</Text>
                )}
                {userCards.map((uc) => (
                  <TouchableOpacity
                    key={uc.user_card_id}
                    style={styles.cardPick}
                    onPress={() => attachFromUrl(uc.card.front_image_url)}
                    testID={`card-pick-${uc.card.id}`}
                  >
                    <Image
                      source={{ uri: uc.card.front_image_url }}
                      style={styles.cardPickImg}
                      resizeMode="cover"
                    />
                  </TouchableOpacity>
                ))}
              </ScrollView>
            </View>
          </View>
        </Modal>
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
  composerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  attachBtn: {
    width: 36,
    height: 36,
    borderRadius: 8,
    backgroundColor: 'rgba(57, 255, 20, 0.12)',
    borderWidth: 1,
    borderColor: 'rgba(57, 255, 20, 0.35)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  attachedPreview: {
    marginTop: 8,
    position: 'relative',
  },
  attachedImage: {
    width: '100%',
    height: 180,
    borderRadius: 8,
    backgroundColor: '#000',
  },
  removeAttachBtn: {
    position: 'absolute',
    top: 6,
    right: 6,
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: 'rgba(0,0,0,0.75)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  postImage: {
    width: '100%',
    height: 240,
    borderRadius: 8,
    marginTop: 8,
    backgroundColor: '#000',
  },
  postActions: {
    marginTop: 6,
  },
  // Attach menu
  attachOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'flex-end',
  },
  attachSheet: {
    backgroundColor: '#0d1410',
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    padding: 20,
    paddingBottom: 32,
    borderTopWidth: 2,
    borderTopColor: '#39ff14',
  },
  attachTitle: {
    color: '#39ff14',
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 2,
    marginBottom: 12,
    textAlign: 'center',
  },
  attachOption: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    padding: 14,
    borderRadius: 10,
    backgroundColor: 'rgba(20,25,20,0.85)',
    borderWidth: 1,
    borderColor: 'rgba(57, 255, 20, 0.2)',
    marginBottom: 8,
  },
  attachOptionTitle: { color: '#fff', fontSize: 14, fontWeight: '800' },
  attachOptionSub: { color: '#789', fontSize: 11, marginTop: 1 },
  // Card picker
  cardPickerOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.85)',
    justifyContent: 'flex-end',
  },
  cardPickerSheet: {
    backgroundColor: '#0d1410',
    borderTopLeftRadius: 18,
    borderTopRightRadius: 18,
    paddingTop: 14,
    paddingHorizontal: 12,
    paddingBottom: 16,
    maxHeight: '80%',
    borderTopWidth: 2,
    borderTopColor: '#39ff14',
  },
  cardPickerHead: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
    paddingHorizontal: 4,
  },
  cardPickerTitle: { color: '#fff', fontSize: 16, fontWeight: '800' },
  cardPickerGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    paddingVertical: 6,
  },
  cardPick: {
    width: 84,
    height: 116,
    borderRadius: 6,
    overflow: 'hidden',
    backgroundColor: '#000',
    borderWidth: 1,
    borderColor: '#333',
  },
  cardPickImg: { width: '100%', height: '100%' },
  muted: { color: '#789', fontSize: 13, padding: 24 },
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

/**
 * Profile — PUBLIC-FACING showcase page.
 *
 * Viewable by friends (or anyone with the user_id). Shows ONLY public info:
 *   - Avatar + username + LVL pill + rank crest
 *   - "Add Friend" button (when not viewing own profile)
 *   - Featured Cards (5-slot showcase — read-only for visitors)
 *   - Collection Progress (base cards + goals)
 *   - Badge Cabinet
 *   - Bio (read-only)
 *
 * Private stuff (Sound, Account, Quick Actions, Logout, Bio editor) lives
 * in `/app/settings.tsx` and is reachable via the gear icon on Home.
 *
 * Routing:
 *   /profile             → own profile (uses AppContext.user)
 *   /profile?userId=xyz  → viewing another user
 */
import React, { useEffect, useMemo, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import * as ImageManipulator from 'expo-image-manipulator';
import axios from 'axios';
import { useApp } from '../src/context/AppContext';
import { RankCrest } from '../src/components/RankCrest';
import { BadgeCabinet } from '../src/components/BadgeCabinet';
import { GrungeBackground } from '../src/components/GrungeBackground';
import { FeaturedCards } from '../src/components/FeaturedCards';
import { SplatTitle } from '../src/components/SplatTitle';
import { MASCOT_SIGNATURE } from '../src/assets/mascot';
import { FONTS } from '../src/theme';

interface PublicUser {
  id: string;
  username: string;
  bio?: string;
  avatar_url?: string;
  daily_login_streak?: number;
  created_at?: string;
  friend_code?: string;
  friend_count?: number;
  featured_card_ids?: string[];
  completed_series?: number[];
  rank?: any;
}

export default function ProfileScreen() {
  const params = useLocalSearchParams<{ userId?: string }>();
  const { user: currentUser, userCards, userGoals, allCards, apiUrl, updateAvatar } = useApp();

  const viewingUserId = params.userId && typeof params.userId === 'string' ? params.userId : null;
  const isOwn = !viewingUserId || (currentUser && viewingUserId === currentUser.id);

  // Public user state (own = AppContext.user, other = fetched)
  const [publicUser, setPublicUser] = useState<PublicUser | null>(null);
  const [otherCardsLookup, setOtherCardsLookup] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);
  const [friendStatus, setFriendStatus] = useState<'none' | 'pending' | 'friends'>('none');
  const [addingFriend, setAddingFriend] = useState(false);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);

  // Lets the user pick an image from device → resize → base64 → save.
  // Available only on own profile (tap blocked on others below).
  const handleChangeAvatar = async () => {
    if (!isOwn || uploadingAvatar) return;
    try {
      const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!perm.granted) {
        return Alert.alert('Permission needed', 'Photo access required.');
      }
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [1, 1],
        quality: 0.8,
      });
      if (result.canceled || !result.assets?.length) return;
      setUploadingAvatar(true);
      const manipulated = await ImageManipulator.manipulateAsync(
        result.assets[0].uri,
        [{ resize: { width: 400, height: 400 } }],
        { compress: 0.7, format: ImageManipulator.SaveFormat.JPEG, base64: true },
      );
      if (!manipulated.base64) throw new Error('No base64');
      const dataUri = `data:image/jpeg;base64,${manipulated.base64}`;
      // Mongo doc ceiling is 16MB but anything >500KB is overkill for an
      // avatar; the 400x400 0.7 JPEG should land around 30-80KB.
      if (dataUri.length > 600_000) {
        setUploadingAvatar(false);
        return Alert.alert('Too large', 'Try a different image.');
      }
      await updateAvatar(dataUri);
      // Optimistic local update — the AppContext setUser already happened
      // but we need to reflect it in this screen's publicUser state too.
      setPublicUser((prev) => prev ? { ...prev, avatar_url: dataUri } : prev);
    } catch (err) {
      console.warn('Avatar upload failed:', err);
      Alert.alert('Error', 'Could not save avatar.');
    } finally {
      setUploadingAvatar(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      if (isOwn) {
        setPublicUser(currentUser as any);
        return;
      }
      if (!viewingUserId) return;
      setLoading(true);
      try {
        const [u, cards] = await Promise.all([
          axios.get(`${apiUrl}/api/users/${viewingUserId}`),
          axios.get(`${apiUrl}/api/users/${viewingUserId}/cards`),
        ]);
        if (cancelled) return;
        setPublicUser(u.data);
        const lookup: Record<string, any> = {};
        for (const uc of cards.data) {
          if (uc.card?.id) lookup[uc.card.id] = uc.card;
        }
        setOtherCardsLookup(lookup);
      } catch {
        Alert.alert('Error', 'Failed to load profile.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [viewingUserId, isOwn, currentUser, apiUrl]);

  const handleAddFriend = async () => {
    if (!currentUser || !publicUser || isOwn) return;
    setAddingFriend(true);
    try {
      await axios.post(`${apiUrl}/api/friends/request`, {
        from_user_id: currentUser.id,
        to_user_id: publicUser.id,
      });
      setFriendStatus('pending');
      Alert.alert('Sent!', `Friend request sent to ${publicUser.username}.`);
    } catch (e: any) {
      const detail = e?.response?.data?.detail || 'Could not send friend request.';
      Alert.alert('Error', detail);
    } finally {
      setAddingFriend(false);
    }
  };

  // ── Collection progress (own profile only — other users' cards are also
  // available via otherCardsLookup but goals aren't public so we hide the
  // Goals progress for visitors).
  const isBaseCard = (c: any) =>
    !c.is_variant && c.rarity !== 'rare' && c.rarity !== 'epic' && c.rarity !== 'variant';
  const baseCardTotal = useMemo(() => allCards.filter(isBaseCard).length, [allCards]);
  const baseCardsOwned = useMemo(() => {
    if (isOwn) {
      return userCards.filter((uc) => uc.card && isBaseCard(uc.card)).length;
    }
    return Object.values(otherCardsLookup).filter(isBaseCard).length;
  }, [isOwn, userCards, otherCardsLookup]);
  const collectionProgress = baseCardTotal > 0
    ? Math.round((baseCardsOwned / baseCardTotal) * 100) : 0;
  const completedGoals = userGoals.filter((ug) => ug.user_goal.completed).length;
  const totalGoals = userGoals.length;
  const goalsPct = totalGoals > 0 ? Math.round((completedGoals / totalGoals) * 100) : 0;

  if (loading || !publicUser) {
    return (
      <GrungeBackground>
        <SafeAreaView style={styles.container}>
          <View style={styles.center}>
            {loading ? (
              <ActivityIndicator color="#39ff14" size="large" />
            ) : (
              <>
                <Text style={styles.lockIcon}>🔒</Text>
                <Text style={styles.lockedText}>Login to view profiles</Text>
              </>
            )}
          </View>
        </SafeAreaView>
      </GrungeBackground>
    );
  }

  const memberSince = publicUser.created_at
    ? new Date(publicUser.created_at).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
    : '';

  return (
    <GrungeBackground>
      <SafeAreaView style={styles.container}>
        <ScrollView showsVerticalScrollIndicator={false}>
          {/* Header — avatar, username, level pill, Add Friend, rank */}
          <View style={styles.header}>
            <TouchableOpacity
              style={styles.avatarWrap}
              onPress={handleChangeAvatar}
              disabled={!isOwn || uploadingAvatar}
              activeOpacity={isOwn ? 0.7 : 1}
              testID="profile-avatar-btn"
            >
              <Image
                source={
                  publicUser.avatar_url
                    ? { uri: publicUser.avatar_url }
                    : { uri: MASCOT_SIGNATURE }
                }
                style={styles.avatar}
              />
              {isOwn && (
                <View style={styles.avatarEditBadge}>
                  {uploadingAvatar ? (
                    <ActivityIndicator size="small" color="#000" />
                  ) : (
                    <Ionicons name="camera" size={14} color="#000" />
                  )}
                </View>
              )}
              <View style={styles.levelPill}>
                <Text style={styles.levelText}>LVL {publicUser.daily_login_streak || 1}</Text>
              </View>
            </TouchableOpacity>
            <View style={styles.nameRow}>
              <Text style={styles.username} testID="profile-username">
                {publicUser.username}
              </Text>
              {!isOwn && (
                <TouchableOpacity
                  style={[
                    styles.addFriendBtn,
                    friendStatus === 'pending' && styles.addFriendPending,
                    friendStatus === 'friends' && styles.addFriendActive,
                  ]}
                  onPress={handleAddFriend}
                  disabled={addingFriend || friendStatus !== 'none'}
                  testID="add-friend-btn"
                >
                  {addingFriend ? (
                    <ActivityIndicator size="small" color="#000" />
                  ) : (
                    <>
                      <Ionicons
                        name={
                          friendStatus === 'friends' ? 'checkmark-circle' :
                          friendStatus === 'pending' ? 'hourglass-outline' :
                          'person-add'
                        }
                        size={14}
                        color="#000"
                      />
                      <Text style={styles.addFriendText}>
                        {friendStatus === 'friends' ? 'FRIEND' :
                         friendStatus === 'pending' ? 'PENDING' :
                         'ADD FRIEND'}
                      </Text>
                    </>
                  )}
                </TouchableOpacity>
              )}
            </View>
            <RankCrest rank={publicUser.rank} size="lg" showLabel />
            {!!memberSince && (
              <Text style={styles.memberSince}>Member since {memberSince}</Text>
            )}
          </View>

          {/* Featured Cards */}
          <View style={styles.section}>
            <FeaturedCards
              apiUrl={apiUrl}
              readOnly={!isOwn}
              featuredIds={publicUser.featured_card_ids ?? []}
              cardsLookup={isOwn ? undefined : otherCardsLookup}
            />
          </View>

          {/* Collection Progress */}
          <View style={styles.section}>
            <SplatTitle>COLLECTION</SplatTitle>
            <View style={styles.progressCard}>
              <View style={styles.progressHeader}>
                <Text style={styles.progressTitle}>Base Cards</Text>
                <Text style={styles.progressPercent}>{collectionProgress}%</Text>
              </View>
              <View style={styles.progressBarBg}>
                <View style={[styles.progressBar, { width: `${collectionProgress}%` }]} />
              </View>
              <Text style={styles.progressSubtext}>
                {baseCardsOwned} / {baseCardTotal} cards
              </Text>
            </View>

            {isOwn && totalGoals > 0 && (
              <View style={styles.progressCard}>
                <View style={styles.progressHeader}>
                  <Text style={styles.progressTitle}>Goals</Text>
                  <Text style={styles.progressPercent}>{goalsPct}%</Text>
                </View>
                <View style={styles.progressBarBg}>
                  <View style={[styles.progressBar, styles.progressBarGold, { width: `${goalsPct}%` }]} />
                </View>
                <Text style={styles.progressSubtext}>
                  {completedGoals} / {totalGoals} goals
                </Text>
              </View>
            )}
          </View>

          {/* Badges */}
          <View style={styles.section}>
            <BadgeCabinet userId={publicUser.id} apiUrl={apiUrl} />
          </View>

          {/* Bio (read-only — editor is in Settings) */}
          {!!publicUser.bio && (
            <View style={styles.section}>
              <SplatTitle>BIO</SplatTitle>
              <View style={styles.bioCard}>
                <Text style={styles.bioText}>{publicUser.bio}</Text>
              </View>
            </View>
          )}

          <View style={{ height: 24 }} />
        </ScrollView>
      </SafeAreaView>
    </GrungeBackground>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: 'transparent' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  lockIcon: { fontSize: 64, marginBottom: 16 },
  lockedText: { color: '#aaa', fontSize: 16 },

  header: {
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 16,
  },
  avatarWrap: { alignItems: 'center', marginBottom: 10 },
  avatar: {
    width: 96,
    height: 96,
    borderRadius: 48,
    borderWidth: 3,
    borderColor: '#39ff14',
    backgroundColor: '#0a0d0a',
  },
  avatarEditBadge: {
    position: 'absolute',
    bottom: 36,
    right: '32%',
    backgroundColor: '#39ff14',
    borderRadius: 12,
    width: 24,
    height: 24,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: '#0a0d0a',
  },
  levelPill: {
    marginTop: 6,
    backgroundColor: '#5a1e8a',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderWidth: 1,
    borderColor: '#9c66cc',
  },
  levelText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 1,
  },
  nameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 8,
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  username: {
    color: '#9aff5a',
    fontSize: 30,
    fontFamily: FONTS.metal,
    fontWeight: '900',
    letterSpacing: 1.5,
    textShadowColor: 'rgba(57,255,20,0.5)',
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 10,
  },
  addFriendBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    backgroundColor: '#39ff14',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#1a8a02',
  },
  addFriendPending: { backgroundColor: '#ffd24a' },
  addFriendActive: { backgroundColor: '#9aff5a' },
  addFriendText: {
    color: '#000',
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 1,
  },
  memberSince: { color: '#789', fontSize: 12, fontStyle: 'italic', marginTop: 8 },

  section: { paddingHorizontal: 16, marginBottom: 8 },
  progressCard: {
    backgroundColor: 'rgba(20, 25, 20, 0.85)',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(57, 255, 20, 0.2)',
    padding: 14,
    marginBottom: 10,
  },
  progressHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  progressTitle: { color: '#fff', fontSize: 14, fontWeight: '700' },
  progressPercent: { color: '#39ff14', fontSize: 16, fontWeight: '900' },
  progressBarBg: {
    height: 10,
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderRadius: 5,
    overflow: 'hidden',
  },
  progressBar: { height: '100%', backgroundColor: '#39ff14', borderRadius: 5 },
  progressBarGold: { backgroundColor: '#ffd24a' },
  progressSubtext: { color: '#789', fontSize: 11, marginTop: 6 },

  bioCard: {
    backgroundColor: 'rgba(20, 25, 20, 0.85)',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(57, 255, 20, 0.2)',
    padding: 14,
  },
  bioText: { color: '#cde', fontSize: 14, lineHeight: 20 },
});

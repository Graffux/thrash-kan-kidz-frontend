/**
 * Settings — private account screen pushed from the Home gear icon.
 *
 * Lives outside the bottom-tab nav (declared as a hidden tab in _layout.tsx
 * so Stack-style pushes work cleanly via expo-router).
 *
 * Contents (all moved here from the old Profile page so Profile can become
 * publicly-viewable by friends):
 *   - Sound Settings (SFX + Music toggles)
 *   - Account Info (username, friend code, last login)
 *   - Bio Editor
 *   - Quick Actions (Buy Coins, Payment History, Send Feedback)
 *   - Logout
 *   - Legal (Privacy Policy)
 *   - Version footer + Feedback Modal
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  ActivityIndicator,
  Modal,
  Switch,
  Share,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import Constants from 'expo-constants';
import { useApp } from '../src/context/AppContext';
import { useSoundSettings, setSfxEnabled, setMusicEnabled } from '../src/utils/sounds';
import { GrungeBackground } from '../src/components/GrungeBackground';
import { SplatTitle } from '../src/components/SplatTitle';

export default function SettingsScreen() {
  const { user, logout, updateProfile, apiUrl } = useApp();
  const router = useRouter();
  const soundSettings = useSoundSettings();
  const [editing, setEditing] = useState(false);
  const [bio, setBio] = useState(user?.bio || '');
  const [saving, setSaving] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackRating, setFeedbackRating] = useState(0);
  const [feedbackMessage, setFeedbackMessage] = useState('');
  const [sendingFeedback, setSendingFeedback] = useState(false);

  if (!user) {
    return (
      <GrungeBackground>
        <SafeAreaView style={styles.container}>
          <View style={styles.centerContainer}>
            <Text style={styles.lockedText}>Please login first.</Text>
          </View>
        </SafeAreaView>
      </GrungeBackground>
    );
  }

  const handleSaveProfile = async () => {
    setSaving(true);
    try {
      await updateProfile(bio);
      setEditing(false);
      Alert.alert('Saved', 'Bio updated.');
    } catch {
      Alert.alert('Error', 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = () => {
    Alert.alert('Logout', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Logout', style: 'destructive', onPress: async () => { await logout(); } },
    ]);
  };

  const handleSubmitFeedback = async () => {
    if (!feedbackMessage.trim()) return Alert.alert('Error', 'Please write your feedback');
    if (feedbackRating === 0) return Alert.alert('Error', 'Please select a rating');
    setSendingFeedback(true);
    try {
      const res = await fetch(`${apiUrl}/api/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          username: user.username,
          rating: feedbackRating,
          message: feedbackMessage.trim(),
        }),
      });
      const data = await res.json();
      if (data.success) {
        Alert.alert('Thank You!', 'Feedback submitted.');
        setShowFeedback(false);
        setFeedbackRating(0);
        setFeedbackMessage('');
      } else {
        Alert.alert('Error', data.detail || 'Failed to submit feedback');
      }
    } catch {
      Alert.alert('Error', 'Failed to submit feedback. Try again.');
    } finally {
      setSendingFeedback(false);
    }
  };

  const handleCopyFriendCode = async () => {
    const code = user.friend_code || '';
    if (!code) return Alert.alert('No code', 'Your friend code is being generated, try again in a moment.');
    // Use Share sheet as a portable "copy" — Android shows clipboard option.
    try {
      await Share.share({ message: code, title: 'Friend Code' });
    } catch {
      Alert.alert('Friend Code', code);
    }
  };

  const handleShareFriendCode = async () => {
    const code = user.friend_code || '';
    if (!code) return;
    try {
      await Share.share({
        message: `Add me on Thrash Kan Kidz! My friend code is ${code}`,
      });
    } catch {
      // user cancelled
    }
  };

  return (
    <GrungeBackground>
      <SafeAreaView style={styles.container}>
        {/* Header */}
        <View style={styles.topBar}>
          <TouchableOpacity onPress={() => router.back()} testID="settings-back-btn">
            <Ionicons name="chevron-back" size={28} color="#9aff5a" />
          </TouchableOpacity>
          <Text style={styles.pageTitle}>SETTINGS</Text>
          <View style={{ width: 28 }} />
        </View>

        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          {/* Account */}
          <SplatTitle>ACCOUNT</SplatTitle>
          <View style={styles.card}>
            <View style={styles.row}>
              <Text style={styles.rowLabel}>Username</Text>
              <Text style={styles.rowValue}>{user.username}</Text>
            </View>
            <View style={styles.rowDivider} />
            <View style={styles.row}>
              <Text style={styles.rowLabel}>Friend Code</Text>
              <View style={styles.friendCodeRow}>
                <Text style={styles.friendCode}>{user.friend_code || '— — —'}</Text>
                <TouchableOpacity onPress={handleCopyFriendCode} testID="copy-friend-code-btn">
                  <Ionicons name="copy-outline" size={18} color="#9aff5a" />
                </TouchableOpacity>
                <TouchableOpacity onPress={handleShareFriendCode} testID="share-friend-code-btn">
                  <Ionicons name="share-social-outline" size={18} color="#9aff5a" />
                </TouchableOpacity>
              </View>
            </View>
            <View style={styles.rowDivider} />
            <View style={styles.row}>
              <Text style={styles.rowLabel}>Last Login</Text>
              <Text style={styles.rowValue}>
                {user.last_login_date
                  ? new Date(user.last_login_date).toLocaleDateString()
                  : 'Today'}
              </Text>
            </View>
          </View>

          {/* Bio */}
          <SplatTitle>BIO</SplatTitle>
          <View style={styles.card}>
            {editing ? (
              <>
                <TextInput
                  style={styles.bioInput}
                  value={bio}
                  onChangeText={setBio}
                  placeholder="Tell other thrashers about yourself..."
                  placeholderTextColor="#666"
                  multiline
                  maxLength={200}
                  testID="settings-bio-input"
                />
                <View style={styles.bioActions}>
                  <TouchableOpacity
                    style={styles.cancelBtn}
                    onPress={() => { setBio(user.bio || ''); setEditing(false); }}
                  >
                    <Text style={styles.cancelBtnText}>Cancel</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={styles.saveBtn}
                    onPress={handleSaveProfile}
                    disabled={saving}
                    testID="settings-bio-save"
                  >
                    {saving ? (
                      <ActivityIndicator size="small" color="#000" />
                    ) : (
                      <Text style={styles.saveBtnText}>Save</Text>
                    )}
                  </TouchableOpacity>
                </View>
              </>
            ) : (
              <>
                <Text style={styles.bioText}>{user.bio || 'No bio yet.'}</Text>
                <TouchableOpacity
                  style={styles.editBtn}
                  onPress={() => setEditing(true)}
                  testID="settings-bio-edit"
                >
                  <Ionicons name="create-outline" size={16} color="#9aff5a" />
                  <Text style={styles.editBtnText}>Edit Bio</Text>
                </TouchableOpacity>
              </>
            )}
          </View>

          {/* Sound */}
          <SplatTitle>SOUND</SplatTitle>
          <View style={styles.card}>
            <View style={styles.row}>
              <View style={styles.rowIconLabel}>
                <Ionicons name="volume-high" size={20} color="#ffd24a" />
                <Text style={styles.rowLabel}>Sound Effects</Text>
              </View>
              <Switch
                value={soundSettings.sfxEnabled}
                onValueChange={setSfxEnabled}
                trackColor={{ false: '#333', true: '#39ff14' }}
                thumbColor={soundSettings.sfxEnabled ? '#fff' : '#888'}
                testID="settings-sfx-toggle"
              />
            </View>
            <View style={styles.rowDivider} />
            <View style={styles.row}>
              <View style={styles.rowIconLabel}>
                <Ionicons name="musical-notes" size={20} color="#ffd24a" />
                <Text style={styles.rowLabel}>Music</Text>
              </View>
              <Switch
                value={soundSettings.musicEnabled}
                onValueChange={setMusicEnabled}
                trackColor={{ false: '#333', true: '#39ff14' }}
                thumbColor={soundSettings.musicEnabled ? '#fff' : '#888'}
                testID="settings-music-toggle"
              />
            </View>
          </View>

          {/* Quick Actions */}
          <SplatTitle>QUICK ACTIONS</SplatTitle>
          <TouchableOpacity
            style={styles.actionBtn}
            onPress={() => router.push('/shop')}
            testID="settings-buy-coins"
          >
            <View style={[styles.actionIcon, { backgroundColor: 'rgba(255, 210, 74, 0.15)' }]}>
              <Ionicons name="cart" size={22} color="#ffd24a" />
            </View>
            <View style={styles.actionText}>
              <Text style={styles.actionTitle}>Buy Coins</Text>
              <Text style={styles.actionSubtitle}>Purchase coin packages</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#666" />
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.actionBtn}
            testID="settings-payment-history"
            onPress={async () => {
              try {
                const res = await fetch(`${apiUrl}/api/users/${user.id}/payment-history`);
                const hist = await res.json();
                if (!hist.length) return Alert.alert('Payment History', 'No purchases yet.');
                const recent = hist.slice(0, 3).map((t: any) =>
                  `${t.package_id} • ${t.coins_amount} coins • ${t.payment_status}`
                ).join('\n');
                Alert.alert('Recent Purchases', recent);
              } catch {
                Alert.alert('Error', 'Failed to load payment history');
              }
            }}
          >
            <View style={[styles.actionIcon, { backgroundColor: 'rgba(76, 175, 80, 0.15)' }]}>
              <Ionicons name="receipt" size={22} color="#4CAF50" />
            </View>
            <View style={styles.actionText}>
              <Text style={styles.actionTitle}>Payment History</Text>
              <Text style={styles.actionSubtitle}>View your purchases</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#666" />
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.actionBtn}
            onPress={() => setShowFeedback(true)}
            testID="settings-feedback"
          >
            <View style={[styles.actionIcon, { backgroundColor: 'rgba(156, 39, 176, 0.15)' }]}>
              <Ionicons name="chatbubble-ellipses" size={22} color="#CE93D8" />
            </View>
            <View style={styles.actionText}>
              <Text style={styles.actionTitle}>Send Feedback</Text>
              <Text style={styles.actionSubtitle}>Help us improve the app</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#666" />
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.actionBtn}
            onPress={() => router.push('/privacy')}
            testID="settings-privacy"
          >
            <View style={[styles.actionIcon, { backgroundColor: 'rgba(120, 120, 120, 0.15)' }]}>
              <Ionicons name="shield-checkmark-outline" size={22} color="#aaa" />
            </View>
            <View style={styles.actionText}>
              <Text style={styles.actionTitle}>Privacy Policy</Text>
              <Text style={styles.actionSubtitle}>How we handle your data</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#666" />
          </TouchableOpacity>

          {/* Logout */}
          <TouchableOpacity
            style={styles.logoutBtn}
            onPress={handleLogout}
            testID="settings-logout"
          >
            <Ionicons name="log-out-outline" size={22} color="#ff6b6b" />
            <Text style={styles.logoutText}>LOGOUT</Text>
          </TouchableOpacity>

          {/* Footer */}
          <Text style={styles.footer}>
            Thrash Kan Kidz v{Constants.expoConfig?.version || '?'} · build {Constants.expoConfig?.android?.versionCode || '?'}
          </Text>
        </ScrollView>

        {/* Feedback modal */}
        <Modal
          visible={showFeedback}
          animationType="fade"
          transparent
          onRequestClose={() => setShowFeedback(false)}
        >
          <View style={styles.fbOverlay}>
            <View style={styles.fbModal}>
              <TouchableOpacity
                style={styles.fbClose}
                onPress={() => setShowFeedback(false)}
                testID="feedback-close-btn"
              >
                <Ionicons name="close" size={24} color="#fff" />
              </TouchableOpacity>
              <Text style={styles.fbTitle}>Send Feedback</Text>
              <Text style={styles.fbSubtitle}>How are you enjoying Thrash Kan Kidz?</Text>

              <View style={styles.rating}>
                {[1, 2, 3, 4, 5].map((star) => (
                  <TouchableOpacity
                    key={star}
                    onPress={() => setFeedbackRating(star)}
                    testID={`feedback-star-${star}`}
                  >
                    <Ionicons
                      name={star <= feedbackRating ? 'star' : 'star-outline'}
                      size={40}
                      color={star <= feedbackRating ? '#FFD700' : '#555'}
                    />
                  </TouchableOpacity>
                ))}
              </View>
              <Text style={styles.ratingLabel}>
                {feedbackRating === 0 ? 'Tap to rate' :
                  feedbackRating === 1 ? 'Needs work' :
                  feedbackRating === 2 ? 'Could be better' :
                  feedbackRating === 3 ? 'Pretty good' :
                  feedbackRating === 4 ? 'Love it!' : 'THRASH APPROVED!'}
              </Text>

              <TextInput
                style={styles.fbInput}
                placeholder="Tell us what you think... bugs, suggestions, favorite cards?"
                placeholderTextColor="#666"
                value={feedbackMessage}
                onChangeText={setFeedbackMessage}
                multiline
                maxLength={500}
                testID="feedback-message-input"
              />
              <Text style={styles.charCount}>{feedbackMessage.length}/500</Text>

              <TouchableOpacity
                style={[styles.fbSubmit, sendingFeedback && { opacity: 0.5 }]}
                onPress={handleSubmitFeedback}
                disabled={sendingFeedback}
                testID="feedback-submit-btn"
              >
                {sendingFeedback ? (
                  <ActivityIndicator size="small" color="#000" />
                ) : (
                  <Text style={styles.fbSubmitText}>SUBMIT FEEDBACK</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </Modal>
      </SafeAreaView>
    </GrungeBackground>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: 'transparent' },
  centerContainer: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  lockedText: { color: '#aaa', fontSize: 16 },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 4,
  },
  pageTitle: {
    color: '#39ff14',
    fontSize: 18,
    fontWeight: '900',
    letterSpacing: 3,
  },
  scroll: { padding: 16, paddingBottom: 40 },
  card: {
    backgroundColor: 'rgba(20, 25, 20, 0.85)',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(57, 255, 20, 0.25)',
    paddingHorizontal: 14,
    paddingVertical: 6,
    marginBottom: 16,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 12,
  },
  rowIconLabel: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  rowLabel: { color: '#cde', fontSize: 14, fontWeight: '600' },
  rowValue: { color: '#fff', fontSize: 14, fontWeight: '700' },
  rowDivider: { height: 1, backgroundColor: 'rgba(255,255,255,0.06)' },
  friendCodeRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  friendCode: {
    color: '#9aff5a',
    fontSize: 14,
    fontWeight: '900',
    letterSpacing: 1.5,
    fontFamily: 'monospace',
  },
  bioInput: {
    color: '#fff',
    fontSize: 14,
    minHeight: 70,
    textAlignVertical: 'top',
    paddingVertical: 6,
  },
  bioText: { color: '#cde', fontSize: 14, lineHeight: 20, paddingVertical: 8 },
  bioActions: { flexDirection: 'row', justifyContent: 'flex-end', gap: 8, paddingVertical: 6 },
  cancelBtn: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 6, backgroundColor: '#333' },
  cancelBtnText: { color: '#aaa', fontWeight: '700' },
  saveBtn: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 6, backgroundColor: '#39ff14' },
  saveBtnText: { color: '#000', fontWeight: '800' },
  editBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, alignSelf: 'flex-start', paddingVertical: 8 },
  editBtnText: { color: '#9aff5a', fontSize: 13, fontWeight: '700' },
  actionBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(20, 25, 20, 0.85)',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: 'rgba(57, 255, 20, 0.15)',
  },
  actionIcon: {
    width: 40, height: 40, borderRadius: 20,
    alignItems: 'center', justifyContent: 'center',
    marginRight: 12,
  },
  actionText: { flex: 1 },
  actionTitle: { color: '#fff', fontSize: 14, fontWeight: '800' },
  actionSubtitle: { color: '#789', fontSize: 11, marginTop: 1 },
  logoutBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: 'rgba(255, 107, 107, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(255, 107, 107, 0.4)',
    paddingVertical: 14,
    borderRadius: 10,
    marginTop: 16,
    marginBottom: 16,
  },
  logoutText: { color: '#ff6b6b', fontSize: 14, fontWeight: '900', letterSpacing: 2 },
  footer: { color: '#456', fontSize: 11, textAlign: 'center', marginTop: 8 },
  // Feedback modal
  fbOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.85)', alignItems: 'center', justifyContent: 'center', padding: 16 },
  fbModal: {
    width: '100%',
    maxWidth: 380,
    backgroundColor: '#0d1410',
    borderRadius: 16,
    padding: 20,
    borderWidth: 2,
    borderColor: '#39ff14',
  },
  fbClose: { position: 'absolute', top: 12, right: 12, zIndex: 2, padding: 4 },
  fbTitle: { color: '#39ff14', fontSize: 20, fontWeight: '900', textAlign: 'center', marginBottom: 4 },
  fbSubtitle: { color: '#aaa', fontSize: 13, textAlign: 'center', marginBottom: 12 },
  rating: { flexDirection: 'row', justifyContent: 'space-evenly', marginVertical: 10 },
  ratingLabel: { color: '#ffd24a', fontSize: 13, textAlign: 'center', marginBottom: 12, fontWeight: '700' },
  fbInput: {
    backgroundColor: '#1a1f1a',
    color: '#fff',
    borderRadius: 8,
    padding: 12,
    minHeight: 100,
    textAlignVertical: 'top',
    fontSize: 14,
    borderWidth: 1,
    borderColor: '#2a3a2a',
  },
  charCount: { color: '#789', fontSize: 11, alignSelf: 'flex-end', marginTop: 4 },
  fbSubmit: {
    backgroundColor: '#39ff14',
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 12,
  },
  fbSubmitText: { color: '#000', fontSize: 14, fontWeight: '900', letterSpacing: 2 },
});

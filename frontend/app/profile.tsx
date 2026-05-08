import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
  TextInput,
  Alert,
  ActivityIndicator,
  Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Image as ExpoImage } from 'expo-image';
import { useApp } from '../src/context/AppContext';
import Constants from 'expo-constants';
import { Switch } from 'react-native';
import { useSoundSettings, setSfxEnabled, setMusicEnabled } from '../src/utils/sounds';

const BACKGROUND_IMAGE = 'https://customer-assets.emergentagent.com/job_earn-cards/artifacts/zgy2com2_enhanced-1771247671181.jpg';

export default function ProfileScreen() {
  const { user, userCards, userGoals, allCards, logout, updateProfile, apiUrl } = useApp();
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const soundSettings = useSoundSettings();
  const [bio, setBio] = useState(user?.bio || '');
  const [saving, setSaving] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackRating, setFeedbackRating] = useState(0);
  const [feedbackMessage, setFeedbackMessage] = useState('');
  const [sendingFeedback, setSendingFeedback] = useState(false);

  if (!user) {
    return (
      <SafeAreaView style={styles.container}>
        <Image source={{ uri: BACKGROUND_IMAGE }} style={styles.backgroundImage} resizeMode="cover" />
        <View style={styles.backgroundOverlay} />
        <View style={styles.centerContainer}>
          <Text style={styles.lockIcon}>🔒</Text>
          <Text style={styles.lockedText}>Please login to view your profile</Text>
        </View>
      </SafeAreaView>
    );
  }

  const handleSaveProfile = async () => {
    setSaving(true);
    try {
      await updateProfile(bio);
      setEditing(false);
      Alert.alert('Success', 'Profile updated!');
    } catch (error) {
      Alert.alert('Error', 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = () => {
    Alert.alert(
      'Logout',
      'Are you sure you want to logout?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Logout',
          style: 'destructive',
          onPress: async () => {
            await logout();
          },
        },
      ]
    );
  };

  const handleSubmitFeedback = async () => {
    if (!feedbackMessage.trim()) {
      Alert.alert('Error', 'Please write your feedback');
      return;
    }
    if (feedbackRating === 0) {
      Alert.alert('Error', 'Please select a rating');
      return;
    }
    setSendingFeedback(true);
    try {
      const response = await fetch(`${apiUrl}/api/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          username: user.username,
          rating: feedbackRating,
          message: feedbackMessage.trim(),
        }),
      });
      const data = await response.json();
      if (data.success) {
        Alert.alert('Thank You!', 'Your feedback has been submitted. We appreciate it!');
        setShowFeedback(false);
        setFeedbackRating(0);
        setFeedbackMessage('');
      } else {
        Alert.alert('Error', data.detail || 'Failed to submit feedback');
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to submit feedback. Please try again.');
    } finally {
      setSendingFeedback(false);
    }
  };

  // Calculate stats
  const totalCards = userCards.reduce((sum, uc) => sum + uc.quantity, 0);
  const uniqueCards = userCards.length;
  // "Cards Collected" progress is based on BASE cards only (variants and epic rewards
  // are tracked separately via Variant Master goals and the reward unlock system).
  const isBaseCard = (c: any) =>
    !c.is_variant && c.rarity !== 'rare' && c.rarity !== 'epic' && c.rarity !== 'variant';
  const baseCardTotal = allCards.filter(isBaseCard).length;
  const baseCardsOwned = userCards.filter(uc => uc.card && isBaseCard(uc.card)).length;
  const completedGoals = userGoals.filter(ug => ug.user_goal.completed).length;
  const totalGoals = userGoals.length;

  // Calculate collection completion percentage (base cards only)
  const collectionProgress = baseCardTotal > 0 ? Math.round((baseCardsOwned / baseCardTotal) * 100) : 0;

  // Format date
  const memberSince = user.created_at 
    ? new Date(user.created_at).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
    : 'Unknown';

  return (
    <SafeAreaView style={styles.container}>
      <Image source={{ uri: BACKGROUND_IMAGE }} style={styles.backgroundImage} resizeMode="cover" />
      <View style={styles.backgroundOverlay} />
      
      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        {/* Profile Header */}
        <View style={styles.profileHeader}>
          <View style={styles.avatarContainer}>
            <Text style={styles.avatarEmoji}>🤘</Text>
          </View>
          <Text style={styles.username}>{user.username}</Text>
          <Text style={styles.memberSince}>Member since {memberSince}</Text>
        </View>

        {/* Stats Grid */}
        <View style={styles.statsSection}>
          <ExpoImage source={{ uri: 'https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/lkv85a9v_enhanced-1776904351419.png' }} style={styles.headerImage} contentFit="contain" />
          <View style={styles.statsGrid}>
            <View style={styles.statCard}>
              <Text style={styles.statEmoji}>💰</Text>
              <Text style={styles.statValue}>{user.coins}</Text>
              <Text style={styles.statLabel}>Coins</Text>
            </View>
            <View style={styles.statCard}>
              <Text style={styles.statEmoji}>🔥</Text>
              <Text style={styles.statValue}>{user.daily_login_streak}</Text>
              <Text style={styles.statLabel}>Day Streak</Text>
            </View>
            <View style={styles.statCard}>
              <Text style={styles.statEmoji}>🃏</Text>
              <Text style={styles.statValue}>{totalCards}</Text>
              <Text style={styles.statLabel}>Total Cards</Text>
            </View>
            <View style={styles.statCard}>
              <Text style={styles.statEmoji}>⭐</Text>
              <Text style={styles.statValue}>{uniqueCards}</Text>
              <Text style={styles.statLabel}>Unique Cards</Text>
            </View>
          </View>
        </View>

        {/* Sound Settings — moved to top per tester request */}
        <View style={styles.settingsSection}>
          <Text style={styles.settingsTitle}>Sound Settings</Text>
          <View style={styles.settingRow}>
            <View style={styles.settingLabelWrap}>
              <Ionicons name="volume-high" size={20} color="#FFD700" />
              <Text style={styles.settingLabel}>Sound Effects</Text>
            </View>
            <Switch
              value={soundSettings.sfxEnabled}
              onValueChange={setSfxEnabled}
              trackColor={{ false: '#333', true: '#FFD700' }}
              thumbColor={soundSettings.sfxEnabled ? '#fff' : '#888'}
              testID="sfx-toggle"
            />
          </View>
          <View style={styles.settingRow}>
            <View style={styles.settingLabelWrap}>
              <Ionicons name="musical-notes" size={20} color="#FFD700" />
              <Text style={styles.settingLabel}>Music</Text>
            </View>
            <Switch
              value={soundSettings.musicEnabled}
              onValueChange={setMusicEnabled}
              trackColor={{ false: '#333', true: '#FFD700' }}
              thumbColor={soundSettings.musicEnabled ? '#fff' : '#888'}
              testID="music-toggle"
            />
          </View>
        </View>

        {/* Collection Progress */}
        <View style={styles.progressSection}>
          <Text style={styles.sectionTitle}>🏆 Collection Progress</Text>
          <View style={styles.progressCard}>
            <View style={styles.progressHeader}>
              <Text style={styles.progressTitle}>Cards Collected</Text>
              <Text style={styles.progressPercent}>{collectionProgress}%</Text>
            </View>
            <View style={styles.progressBarContainer}>
              <View style={[styles.progressBar, { width: `${collectionProgress}%` }]} />
            </View>
            <Text style={styles.progressSubtext}>
              {baseCardsOwned} of {baseCardTotal} base cards
            </Text>
          </View>
          
          <View style={styles.progressCard}>
            <View style={styles.progressHeader}>
              <Text style={styles.progressTitle}>Goals Completed</Text>
              <Text style={styles.progressPercent}>
                {totalGoals > 0 ? Math.round((completedGoals / totalGoals) * 100) : 0}%
              </Text>
            </View>
            <View style={styles.progressBarContainer}>
              <View 
                style={[
                  styles.progressBar, 
                  styles.progressBarGreen,
                  { width: `${totalGoals > 0 ? (completedGoals / totalGoals) * 100 : 0}%` }
                ]} 
              />
            </View>
            <Text style={styles.progressSubtext}>
              {completedGoals} of {totalGoals} goals
            </Text>
          </View>
        </View>

        {/* Bio Section */}
        <View style={styles.bioSection}>
          <View style={styles.bioHeader}>
            <Text style={styles.sectionTitle}>📝 About Me</Text>
            {!editing && (
              <TouchableOpacity onPress={() => setEditing(true)}>
                <Text style={styles.editButton}>Edit</Text>
              </TouchableOpacity>
            )}
          </View>
          
          {editing ? (
            <View style={styles.bioEditContainer}>
              <TextInput
                style={styles.bioInput}
                value={bio}
                onChangeText={setBio}
                placeholder="Tell us about yourself..."
                placeholderTextColor="#666"
                multiline
                maxLength={200}
              />
              <View style={styles.bioActions}>
                <TouchableOpacity 
                  style={styles.cancelButton}
                  onPress={() => {
                    setBio(user.bio || '');
                    setEditing(false);
                  }}
                >
                  <Text style={styles.cancelButtonText}>Cancel</Text>
                </TouchableOpacity>
                <TouchableOpacity 
                  style={styles.saveButton}
                  onPress={handleSaveProfile}
                  disabled={saving}
                >
                  {saving ? (
                    <ActivityIndicator size="small" color="#000" />
                  ) : (
                    <Text style={styles.saveButtonText}>Save</Text>
                  )}
                </TouchableOpacity>
              </View>
            </View>
          ) : (
            <View style={styles.bioCard}>
              <Text style={styles.bioText}>
                {user.bio || 'No bio yet. Tap Edit to add one!'}
              </Text>
            </View>
          )}
        </View>

        {/* Account Section */}
        <View style={styles.accountSection}>
          <Text style={styles.sectionTitle}>⚙️ Account</Text>
          
          <View style={styles.accountCard}>
            <View style={styles.accountItem}>
              <Text style={styles.accountLabel}>Username</Text>
              <Text style={styles.accountValue}>{user.username}</Text>
            </View>
            
            <View style={styles.accountItem}>
              <Text style={styles.accountLabel}>User ID</Text>
              <Text style={styles.accountValueSmall}>{user.id.slice(0, 8)}...</Text>
            </View>
            
            <View style={styles.accountItem}>
              <Text style={styles.accountLabel}>Last Login</Text>
              <Text style={styles.accountValue}>
                {user.last_login_date 
                  ? new Date(user.last_login_date).toLocaleDateString()
                  : 'Today'}
              </Text>
            </View>
          </View>
        </View>

        {/* Quick Actions Section */}
        <View style={styles.actionsSection}>
          <Text style={styles.sectionTitle}>💳 Quick Actions</Text>
          
          <TouchableOpacity 
            style={styles.actionButton}
            onPress={() => router.push('/shop')}
          >
            <View style={styles.actionIconContainer}>
              <Ionicons name="cart" size={24} color="#FFD700" />
            </View>
            <View style={styles.actionTextContainer}>
              <Text style={styles.actionTitle}>Buy Coins</Text>
              <Text style={styles.actionSubtitle}>Purchase coin packages</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#666" />
          </TouchableOpacity>

          <TouchableOpacity 
            style={styles.actionButton}
            onPress={async () => {
              try {
                const response = await fetch(`${apiUrl}/api/users/${user.id}/payment-history`);
                const history = await response.json();
                if (history.length === 0) {
                  Alert.alert('Payment History', 'No purchases yet. Buy some coins to get started!');
                } else {
                  const recent = history.slice(0, 3);
                  const historyText = recent.map((t: any) => 
                    `${t.package_id} - ${t.coins_amount} coins - ${t.payment_status}`
                  ).join('\n');
                  Alert.alert('Recent Purchases', historyText);
                }
              } catch (error) {
                Alert.alert('Error', 'Failed to load payment history');
              }
            }}
          >
            <View style={styles.actionIconContainer}>
              <Ionicons name="receipt" size={24} color="#4CAF50" />
            </View>
            <View style={styles.actionTextContainer}>
              <Text style={styles.actionTitle}>Payment History</Text>
              <Text style={styles.actionSubtitle}>View your purchases</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#666" />
          </TouchableOpacity>

          <TouchableOpacity 
            style={styles.actionButton}
            onPress={() => setShowFeedback(true)}
            data-testid="send-feedback-btn"
          >
            <View style={[styles.actionIconContainer, { backgroundColor: 'rgba(156, 39, 176, 0.1)' }]}>
              <Ionicons name="chatbubble-ellipses" size={24} color="#CE93D8" />
            </View>
            <View style={styles.actionTextContainer}>
              <Text style={styles.actionTitle}>Send Feedback</Text>
              <Text style={styles.actionSubtitle}>Help us improve the app</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#666" />
          </TouchableOpacity>
        </View>

        {/* Logout Button */}
        <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
          <Ionicons name="log-out-outline" size={24} color="#ff6b6b" />
          <Text style={styles.logoutText}>Logout</Text>
        </TouchableOpacity>

        {/* Legal Section */}
        <View style={styles.legalSection}>
          <TouchableOpacity 
            style={styles.legalButton}
            onPress={() => router.push('/privacy')}
          >
            <Ionicons name="shield-checkmark-outline" size={20} color="#888" />
            <Text style={styles.legalButtonText}>Privacy Policy</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.footer}>
          <Text style={styles.footerText}>
            Thrash Kan Kidz v{Constants.expoConfig?.version || '?'} (build {Constants.expoConfig?.android?.versionCode || '?'})
          </Text>
          <Text style={styles.footerSubtext}>Collect 'em all!</Text>
        </View>
      </ScrollView>

      {/* Feedback Modal */}
      <Modal
        visible={showFeedback}
        animationType="fade"
        transparent={true}
        onRequestClose={() => setShowFeedback(false)}
      >
        <View style={styles.feedbackOverlay}>
          <View style={styles.feedbackModal}>
            <TouchableOpacity
              style={styles.feedbackCloseBtn}
              onPress={() => setShowFeedback(false)}
            >
              <Ionicons name="close" size={24} color="#fff" />
            </TouchableOpacity>

            <Text style={styles.feedbackTitle}>Send Feedback</Text>
            <Text style={styles.feedbackSubtitle}>How are you enjoying Thrash Kan Kidz?</Text>

            {/* Star Rating */}
            <View style={styles.ratingContainer}>
              {[1, 2, 3, 4, 5].map((star) => (
                <TouchableOpacity
                  key={star}
                  onPress={() => setFeedbackRating(star)}
                  data-testid={`rating-star-${star}`}
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

            {/* Message Input */}
            <TextInput
              style={styles.feedbackInput}
              placeholder="Tell us what you think... bugs, suggestions, favorite cards?"
              placeholderTextColor="#666"
              value={feedbackMessage}
              onChangeText={setFeedbackMessage}
              multiline
              maxLength={500}
              data-testid="feedback-message-input"
            />
            <Text style={styles.charCount}>{feedbackMessage.length}/500</Text>

            {/* Submit Button */}
            <TouchableOpacity
              style={[styles.feedbackSubmitBtn, sendingFeedback && { opacity: 0.5 }]}
              onPress={handleSubmitFeedback}
              disabled={sendingFeedback}
              data-testid="submit-feedback-btn"
            >
              {sendingFeedback ? (
                <ActivityIndicator size="small" color="#000" />
              ) : (
                <Text style={styles.feedbackSubmitText}>SUBMIT FEEDBACK</Text>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f0f1a',
  },
  backgroundImage: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    width: '100%',
    height: '100%',
  },
  backgroundOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  lockIcon: {
    fontSize: 64,
    marginBottom: 16,
  },
  lockedText: {
    color: '#aaa',
    fontSize: 16,
    textAlign: 'center',
  },
  scrollView: {
    flex: 1,
    paddingHorizontal: 16,
  },
  // Profile Header
  profileHeader: {
    alignItems: 'center',
    paddingVertical: 24,
  },
  avatarContainer: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: 'rgba(255, 215, 0, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 3,
    borderColor: '#FFD700',
    marginBottom: 16,
  },
  avatarEmoji: {
    fontSize: 48,
  },
  username: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 4,
  },
  memberSince: {
    fontSize: 14,
    color: '#888',
  },
  // Stats Section
  statsSection: {
    marginBottom: 24,
  },
  headerImage: {
    width: 180,
    height: 80,
    alignSelf: 'center',
    marginBottom: 8,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 12,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  statCard: {
    width: '48%',
    backgroundColor: 'rgba(26, 26, 46, 0.9)',
    borderRadius: 16,
    padding: 16,
    alignItems: 'center',
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  statEmoji: {
    fontSize: 28,
    marginBottom: 8,
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFD700',
  },
  statLabel: {
    fontSize: 12,
    color: '#888',
    marginTop: 4,
  },
  // Progress Section
  progressSection: {
    marginBottom: 24,
  },
  progressCard: {
    backgroundColor: 'rgba(26, 26, 46, 0.9)',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  progressHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  progressTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  progressPercent: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FFD700',
  },
  progressBarContainer: {
    height: 12,
    backgroundColor: '#333',
    borderRadius: 6,
    overflow: 'hidden',
    marginBottom: 8,
  },
  progressBar: {
    height: '100%',
    backgroundColor: '#FFD700',
    borderRadius: 6,
  },
  progressBarGreen: {
    backgroundColor: '#4CAF50',
  },
  progressSubtext: {
    fontSize: 12,
    color: '#888',
  },
  // Bio Section
  bioSection: {
    marginBottom: 24,
  },
  bioHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  editButton: {
    color: '#FFD700',
    fontSize: 14,
    fontWeight: '600',
  },
  bioCard: {
    backgroundColor: 'rgba(26, 26, 46, 0.9)',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: '#333',
  },
  bioText: {
    color: '#ccc',
    fontSize: 14,
    lineHeight: 22,
  },
  bioEditContainer: {
    backgroundColor: 'rgba(26, 26, 46, 0.9)',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: '#FFD700',
  },
  bioInput: {
    color: '#fff',
    fontSize: 14,
    minHeight: 80,
    textAlignVertical: 'top',
  },
  bioActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    marginTop: 12,
  },
  cancelButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    marginRight: 12,
  },
  cancelButtonText: {
    color: '#888',
    fontSize: 14,
    fontWeight: '600',
  },
  saveButton: {
    backgroundColor: '#FFD700',
    paddingHorizontal: 24,
    paddingVertical: 10,
    borderRadius: 20,
  },
  saveButtonText: {
    color: '#000',
    fontSize: 14,
    fontWeight: 'bold',
  },
  // Account Section
  accountSection: {
    marginBottom: 24,
  },
  accountCard: {
    backgroundColor: 'rgba(26, 26, 46, 0.9)',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: '#333',
  },
  accountItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  accountLabel: {
    fontSize: 14,
    color: '#888',
  },
  accountValue: {
    fontSize: 14,
    color: '#fff',
    fontWeight: '600',
  },
  accountValueSmall: {
    fontSize: 12,
    color: '#666',
    fontFamily: 'monospace',
  },
  // Quick Actions Section
  actionsSection: {
    marginBottom: 24,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(26, 26, 46, 0.9)',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  actionIconContainer: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(255, 215, 0, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  actionTextContainer: {
    flex: 1,
  },
  actionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  actionSubtitle: {
    fontSize: 12,
    color: '#888',
    marginTop: 2,
  },
  // Logout Button
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(244, 67, 54, 0.2)',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: '#F44336',
    marginBottom: 16,
    gap: 8,
  },
  logoutIcon: {
    fontSize: 20,
    marginRight: 8,
  },
  logoutText: {
    color: '#ff6b6b',
    fontSize: 16,
    fontWeight: 'bold',
  },
  // Legal Section
  settingsSection: {
    marginHorizontal: 16,
    marginBottom: 16,
    padding: 16,
    backgroundColor: 'rgba(26, 26, 46, 0.85)',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: 'rgba(255, 215, 0, 0.25)',
  },
  settingsTitle: {
    color: '#FFD700',
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 12,
  },
  settingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 8,
  },
  settingLabelWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  settingLabel: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '500',
  },
  legalSection: {
    alignItems: 'center',
    marginBottom: 16,
  },
  legalButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
    gap: 8,
  },
  legalButtonText: {
    color: '#888',
    fontSize: 14,
    textDecorationLine: 'underline',
  },
  // Footer
  footer: {
    alignItems: 'center',
    paddingVertical: 24,
    marginBottom: 24,
  },
  footerText: {
    color: '#666',
    fontSize: 14,
  },
  footerSubtext: {
    color: '#444',
    fontSize: 12,
    marginTop: 4,
  },
  // Feedback Modal
  feedbackOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.9)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  feedbackModal: {
    width: '90%',
    backgroundColor: '#1a1a2e',
    borderRadius: 20,
    padding: 24,
    borderWidth: 2,
    borderColor: '#9C27B0',
  },
  feedbackCloseBtn: {
    position: 'absolute',
    top: 12,
    right: 12,
    zIndex: 10,
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: 20,
    padding: 6,
  },
  feedbackTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFD700',
    textAlign: 'center',
    marginBottom: 4,
  },
  feedbackSubtitle: {
    fontSize: 14,
    color: '#aaa',
    textAlign: 'center',
    marginBottom: 20,
  },
  ratingContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 8,
    marginBottom: 8,
  },
  ratingLabel: {
    fontSize: 14,
    color: '#CE93D8',
    textAlign: 'center',
    fontWeight: '600',
    marginBottom: 16,
  },
  feedbackInput: {
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderRadius: 12,
    padding: 14,
    color: '#fff',
    fontSize: 14,
    minHeight: 100,
    textAlignVertical: 'top',
    borderWidth: 1,
    borderColor: '#333',
  },
  charCount: {
    fontSize: 11,
    color: '#666',
    textAlign: 'right',
    marginTop: 4,
    marginBottom: 16,
  },
  feedbackSubmitBtn: {
    backgroundColor: '#FFD700',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  feedbackSubmitText: {
    color: '#000',
    fontSize: 16,
    fontWeight: 'bold',
  },
});

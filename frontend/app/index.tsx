import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'expo-router';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  ScrollView,
  ActivityIndicator,
  Alert,
  Image,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useApp } from '../src/context/AppContext';
import { LinearGradient } from 'expo-linear-gradient';
import { useSoundPlayer } from '../src/utils/sounds';
import { DailyWheelModal } from '../src/components/DailyWheelModal';
import { CardPickerModal } from '../src/components/CardPickerModal';
import MascotSplash from '../src/components/MascotSplash';
import { RankCrest } from '../src/components/RankCrest';
import { GrungeBackground } from '../src/components/GrungeBackground';
import { FONTS } from '../src/theme';
import { RippableDailyPack } from '../src/components/RippableDailyPack';
import { DrippingLogo } from '../src/components/DrippingLogo';
import { MetalStatPanel } from '../src/components/MetalStatPanel';
import { SplatTitle } from '../src/components/SplatTitle';
import { HeroCarousel } from '../src/components/HeroCarousel';
import { ThrashMissionsPreview } from '../src/components/ThrashMissionsPreview';
import { MoshPitPreview } from '../src/components/MoshPitPreview';
import { MASCOT_SIGNATURE } from '../src/assets/mascot';
import { ICONS } from '../src/assets/icons';

export default function HomeScreen() {
  const { user, loading, login, logout, claimDailyLogin, userCards, refreshData, apiUrl } = useApp();
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [dailyMessage, setDailyMessage] = useState<string | null>(null);
  const [claiming, setClaiming] = useState(false);

  // Daily wheel + Card picker (moved from Shop to Home so they show up the
  // moment a player lands after login — primary daily retention driver).
  const [showDailyWheel, setShowDailyWheel] = useState(false);
  const [showCardPicker, setShowCardPicker] = useState(false);
  const [wheelStreak, setWheelStreak] = useState(0);
  const [dailyWheelChecked, setDailyWheelChecked] = useState(false);
  const buttonTapSound = useSoundPlayer('button_tap');
  const prizeWonSound = useSoundPlayer('prize_won');

  const loginRiff = useSoundPlayer('login_riff');
  const riffPlayedRef = useRef(false);

  useEffect(() => {
    if (user) {
      refreshData();
      // Play login riff once per session when user logs in
      if (!riffPlayedRef.current) {
        riffPlayedRef.current = true;
        loginRiff.play();
      }
      // Auto-pop the Daily Wheel if the user hasn't spun today. Runs once
      // per session — `dailyWheelChecked` short-circuits later renders.
      checkDailyWheel();
    } else {
      // Reset so riff plays again on next login
      riffPlayedRef.current = false;
      setDailyWheelChecked(false);
    }
  }, [user?.id]);

  const checkDailyWheel = async () => {
    if (!user || dailyWheelChecked) return;
    try {
      const res = await fetch(`${apiUrl}/api/users/${user.id}/daily-wheel`);
      const data = await res.json();
      setWheelStreak(data.wheel_streak || 0);
      if (data.can_spin) {
        setShowDailyWheel(true);
      }
      setDailyWheelChecked(true);
    } catch (err) {
      console.error('Error checking daily wheel:', err);
    }
  };

  const handleWheelSpin = async () => {
    if (!user) throw new Error('Not logged in');
    const res = await fetch(`${apiUrl}/api/users/${user.id}/daily-wheel/spin`, { method: 'POST' });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to spin');
    }
    const data = await res.json();
    setWheelStreak(data.streak || 0);
    // refreshData() updates AppContext so the Shop screen + stats reflect
    // the new medal / free-pack balance the next time they render.
    refreshData();
    return data;
  };

  const handleLogin = async () => {
    if (!username.trim()) {
      Alert.alert('Error', 'Please enter a username');
      return;
    }
    if (!password.trim()) {
      Alert.alert('Error', 'Please enter a password');
      return;
    }
    setIsLoggingIn(true);
    try {
      await login(username.trim(), password);
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Login failed');
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleRegister = async () => {
    if (!username.trim()) {
      Alert.alert('Error', 'Please enter a username');
      return;
    }
    if (!password.trim() || password.length < 4) {
      Alert.alert('Error', 'Password must be at least 4 characters');
      return;
    }
    setIsLoggingIn(true);
    try {
      await login(username.trim(), password, true); // true = register mode
      Alert.alert('Success', 'Account created! Welcome to Thrash Kan Kidz!');
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Registration failed');
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleClaimDaily = async () => {
    setClaiming(true);
    try {
      const result = await claimDailyLogin();
      setDailyMessage(result.message);
      setTimeout(() => setDailyMessage(null), 3000);
    } catch (error: any) {
      Alert.alert('Already Claimed', error.response?.data?.detail || 'Come back tomorrow!');
    } finally {
      setClaiming(false);
    }
  };

  // Show Ronch's entrance once per component mount. On real Android cold
  // start the home screen mounts fresh and this fires; tab-switches back
  // to Home preserve component state via React Navigation, so the splash
  // won't replay annoyingly. Component self-unmounts after its animation.
  const [renderSplash, setRenderSplash] = useState(true);
  useEffect(() => {
    const t = setTimeout(() => setRenderSplash(false), 1600);
    return () => clearTimeout(t);
  }, []);

  if (loading) {
    return (
      <GrungeBackground>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#FFD700" />
          {renderSplash && <MascotSplash holdMs={1500} />}
        </View>
      </GrungeBackground>
    );
  }

  if (!user) {
    return (
      <GrungeBackground>
        <SafeAreaView style={styles.container}>
        {renderSplash && <MascotSplash holdMs={1500} />}
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={styles.loginContainer}
        >
          <View style={styles.loginContent}>
            {/* Logo */}
            <Image
              source={{ uri: 'https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/gxse2ebd_Screenshot_20260423_212101_Gallery.png' }}
              style={styles.logoImage}
              resizeMode="contain"
            />
            
            <View style={styles.inputContainer}>
              <TextInput
                style={styles.input}
                placeholder="Username"
                placeholderTextColor="#999"
                value={username}
                onChangeText={setUsername}
                autoCapitalize="none"
                autoCorrect={false}
              />
              <TextInput
                style={styles.input}
                placeholder="Password"
                placeholderTextColor="#999"
                value={password}
                onChangeText={setPassword}
                secureTextEntry
                autoCapitalize="none"
                autoCorrect={false}
              />
              
              {isRegistering ? (
                <>
                  <TouchableOpacity
                    style={styles.loginButton}
                    onPress={handleRegister}
                    disabled={isLoggingIn}
                  >
                    {isLoggingIn ? (
                      <ActivityIndicator color="#000" />
                    ) : (
                      <Text style={styles.loginButtonText}>CREATE ACCOUNT</Text>
                    )}
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={styles.switchButton}
                    onPress={() => setIsRegistering(false)}
                  >
                    <Text style={styles.switchButtonText}>Already have an account? Login</Text>
                  </TouchableOpacity>
                </>
              ) : (
                <>
                  <TouchableOpacity
                    style={styles.loginButton}
                    onPress={handleLogin}
                    disabled={isLoggingIn}
                  >
                    {isLoggingIn ? (
                      <ActivityIndicator color="#000" />
                    ) : (
                      <Text style={styles.loginButtonText}>LOGIN</Text>
                    )}
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={styles.switchButton}
                    onPress={() => setIsRegistering(true)}
                  >
                    <Text style={styles.switchButtonText}>New here? Create Account</Text>
                  </TouchableOpacity>
                </>
              )}
            </View>
            
            <Text style={styles.creditText}>Art by Graffux Graphics</Text>
          </View>
        </KeyboardAvoidingView>
        </SafeAreaView>
      </GrungeBackground>
    );
  }

  const canClaimDaily = user.last_login_date !== new Date().toISOString().split('T')[0];

  return (
    <GrungeBackground>
      <SafeAreaView style={styles.container}>
      {renderSplash && <MascotSplash holdMs={1500} />}
      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        {/* Header — Ronch avatar + LEVEL + dripping logo + logout */}
        <View style={styles.topBar}>
          <View style={styles.avatarBlock}>
            <Image source={{ uri: MASCOT_SIGNATURE }} style={styles.ronchAvatar} />
            <View style={styles.levelPill}>
              <Text style={styles.levelText}>LVL {user.daily_login_streak || 1}</Text>
            </View>
          </View>
          <DrippingLogo width={220} height={60} />
          <TouchableOpacity
            onPress={() => router.push('/settings')}
            style={styles.logoutButton}
            testID="home-settings-btn"
          >
            <Ionicons name="settings-outline" size={24} color="#9aff5a" />
          </TouchableOpacity>
        </View>

        {/* Welcome strip */}
        <View style={styles.welcomeStrip}>
          <Text style={styles.welcomeText}>Welcome back,</Text>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
            <Text style={styles.usernameText}>{user.username}!</Text>
            <RankCrest rank={user.rank} size="sm" />
          </View>
        </View>

        {/* 4-up Metal Stat Panel grid */}
        <View style={styles.statsGrid}>
          <MetalStatPanel
            iconSource={ICONS.statCards}
            value={userCards.length}
            label="MY CARDS"
            style={styles.statCell}
          />
          <MetalStatPanel
            iconSource={ICONS.statCoins}
            value={user.coins}
            label="COINS"
            style={styles.statCell}
          />
          <MetalStatPanel
            iconSource={ICONS.statStreak}
            value={user.daily_login_streak}
            label="STREAK"
            style={styles.statCell}
          />
          <TouchableOpacity
            style={styles.statCell}
            onPress={() => router.push('/leaderboard')}
            activeOpacity={0.85}
            testID="home-stat-leaderboard"
          >
            <MetalStatPanel
              iconSource={ICONS.statTrophy}
              value={(user.completed_series ?? []).length}
              label="LEADERBOARD"
            />
          </TouchableOpacity>
        </View>

        {/* Hero promo carousel — sits right under stats so it's the first
            tappable promotion users see when scrolling. */}
        <HeroCarousel />

        {/* Daily Login — rip-able pack replaces the legacy button. */}
        <View style={styles.dailyContainer}>
          <SplatTitle>DAILY BONUS</SplatTitle>
          {dailyMessage && (
            <View style={styles.successMessage}>
              <Ionicons name="checkmark-circle" size={20} color="#4CAF50" />
              <Text style={styles.successText}>{dailyMessage}</Text>
            </View>
          )}
          <View style={styles.dailyPackWrap}>
            <RippableDailyPack
              width={320}
              height={130}
              claimed={!canClaimDaily}
              loading={claiming}
              onClaim={handleClaimDaily}
            />
          </View>
        </View>

        {/* Mini-games: Daily Wheel re-open + Card Picker. The Daily Wheel
            auto-pops on first login each day (see useEffect above); these
            buttons let the user replay/re-launch either game whenever they
            want during the session. Both modals manage their own state via
            the AppContext refresh, so awards reflect immediately on the
            Shop screen the next time it renders. */}
        {/* Thrash Missions preview — top 3 in-progress goals */}
        <ThrashMissionsPreview />

        <View style={styles.miniGamesContainer}>
          <SplatTitle>MINI-GAMES</SplatTitle>          <TouchableOpacity
            style={styles.miniGameButton}
            onPress={() => {
              buttonTapSound.play();
              setShowDailyWheel(true);
            }}
            data-testid="home-daily-wheel-btn"
          >
            <Text style={styles.miniGameEmoji}>🎡</Text>
            <View style={{ flex: 1 }}>
              <Text style={styles.miniGameTitle}>Daily Wheel</Text>
              <Text style={styles.miniGameSub}>One free spin every day</Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color="#FFD700" />
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.miniGameButton}
            onPress={() => {
              buttonTapSound.play();
              setShowCardPicker(true);
            }}
            data-testid="home-card-picker-btn"
          >
            <Text style={styles.miniGameEmoji}>🎴</Text>
            <View style={{ flex: 1 }}>
              <Text style={styles.miniGameTitle}>Card Picker</Text>
              <Text style={styles.miniGameSub}>Match a pair, win a prize!</Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color="#FFD700" />
          </TouchableOpacity>
        </View>

        {/* Mosh Pit community feed preview — latest 3 posts */}
        <MoshPitPreview />

        {/* Featured Card Preview — shows pinned slots if user has them set,
            otherwise falls back to the user's first 3 owned cards. */}
        <View style={styles.featuredContainer}>
          <SplatTitle>FEATURED CARDS</SplatTitle>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            {(() => {
              const pinnedIds = user.featured_card_ids ?? [];
              const pinned = pinnedIds
                .map((id) => userCards.find((uc) => uc.card.id === id))
                .filter(Boolean) as typeof userCards;
              const displayCards = pinned.length > 0 ? pinned : userCards.slice(0, 3);
              return displayCards.map((uc) => (
                <View key={uc.user_card_id} style={styles.featuredCard}>
                  <Image
                    source={{ uri: uc.card.front_image_url }}
                    style={styles.featuredImage}
                    resizeMode="cover"
                  />
                  <View style={[styles.rarityBadge, getRarityStyle(uc.card.rarity)]}>
                    <Text style={styles.rarityText}>{uc.card.rarity.toUpperCase()}</Text>
                  </View>
                </View>
              ));
            })()}
            {userCards.length === 0 && (
              <View style={styles.emptyFeatured}>
                <Ionicons name="albums-outline" size={48} color="#666" />
                <Text style={styles.emptyText}>No cards yet!</Text>
                <Text style={styles.emptySubtext}>Visit the shop to buy cards</Text>
              </View>
            )}
          </ScrollView>
        </View>
      </ScrollView>

      {/* Daily Wheel Modal — auto-pops on first session login each day. */}
      <DailyWheelModal
        visible={showDailyWheel}
        onClose={() => {
          setShowDailyWheel(false);
          refreshData();
        }}
        onSpin={handleWheelSpin}
        streak={wheelStreak}
        onSpinStart={() => buttonTapSound.play()}
        onPrizeWon={() => prizeWonSound.play()}
      />

      {/* Card Picker Modal */}
      <CardPickerModal
        visible={showCardPicker}
        onClose={() => {
          setShowCardPicker(false);
          refreshData();
        }}
        apiUrl={apiUrl}
        userId={user.id}
        onPrizeWon={() => prizeWonSound.play()}
      />
      </SafeAreaView>
    </GrungeBackground>
  );
}

const getRarityStyle = (rarity: string) => {
  switch (rarity) {
    case 'common':
      return { backgroundColor: '#808080' };
    case 'rare':
      return { backgroundColor: '#4169E1' };
    case 'epic':
      return { backgroundColor: '#9932CC' };
    default:
      return { backgroundColor: '#808080' };
  }
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: 'transparent',
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
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0f0f1a',
  },
  scrollView: {
    flex: 1,
    paddingHorizontal: 16,
  },
  loginContainer: {
    flex: 1,
    justifyContent: 'flex-end',
    paddingHorizontal: 32,
    paddingBottom: 100,
  },
  loginContent: {
    width: '100%',
  },
  logoContainer: {
    alignItems: 'center',
    marginBottom: 48,
  },
  logoImage: {
    width: 300,
    height: 150,
    marginBottom: 8,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#FFD700',
    marginTop: 16,
    textAlign: 'center',
  },
  giftEmoji: {
    fontSize: 18,
    marginRight: 8,
  },
  creditText: {
    color: '#666',
    fontSize: 12,
    textAlign: 'center',
    marginTop: 24,
  },
  subtitle: {
    fontSize: 18,
    color: '#888',
    marginTop: 8,
  },
  inputContainer: {
    marginBottom: 16,
  },
  input: {
    backgroundColor: 'rgba(26, 26, 46, 0.9)',
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
    color: '#fff',
    borderWidth: 1,
    borderColor: 'rgba(255, 215, 0, 0.3)',
    marginBottom: 16,
  },
  loginButton: {
    backgroundColor: '#FFD700',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  },
  loginButtonText: {
    color: '#000',
    fontSize: 16,
    fontWeight: 'bold',
  },
  switchButton: {
    marginTop: 16,
    alignItems: 'center',
  },
  switchButtonText: {
    color: '#FFD700',
    fontSize: 14,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 20,
  },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 8,
    paddingHorizontal: 4,
  },
  avatarBlock: {
    alignItems: 'center',
  },
  ronchAvatar: {
    width: 52,
    height: 52,
    borderRadius: 26,
    borderWidth: 2,
    borderColor: '#39ff14',
    backgroundColor: '#0a0d0a',
  },
  levelPill: {
    marginTop: 4,
    backgroundColor: '#5a1e8a',
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderWidth: 1,
    borderColor: '#9c66cc',
  },
  levelText: {
    color: '#fff',
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 0.8,
  },
  welcomeStrip: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 6,
    marginBottom: 10,
  },
  statsGrid: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 20,
    paddingHorizontal: 2,
  },
  statCell: {
    // MetalStatPanel uses flex:1 internally
  },
  welcomeText: {
    fontSize: 14,
    color: '#888',
  },
  usernameText: {
    fontSize: 28,
    fontFamily: FONTS.metal,
    fontWeight: '900',
    color: '#9aff5a',
    letterSpacing: 1.5,
    textShadowColor: 'rgba(57,255,20,0.45)',
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 6,
  },
  logoutButton: {
    padding: 8,
  },
  statsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 12,
    marginBottom: 24,
  },
  statCard: {
    flex: 1,
    backgroundColor: '#1a1a2e',
    borderRadius: 16,
    padding: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#333',
  },
  statEmoji: {
    fontSize: 28,
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
    marginTop: 8,
  },
  statLabel: {
    fontSize: 12,
    color: '#888',
    marginTop: 4,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 16,
  },
  dailyContainer: {
    marginBottom: 24,
  },
  dailyPackWrap: {
    alignItems: 'center',
    marginBottom: 4,
  },
  miniGamesContainer: {
    marginBottom: 24,
  },
  miniGameButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(20, 20, 32, 0.85)',
    borderWidth: 1,
    borderColor: 'rgba(255, 215, 0, 0.35)',
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginBottom: 10,
    gap: 14,
  },
  miniGameEmoji: {
    fontSize: 28,
  },
  miniGameTitle: {
    color: '#FFD700',
    fontSize: 16,
    fontWeight: 'bold',
    letterSpacing: 0.5,
  },
  miniGameSub: {
    color: '#aaa',
    fontSize: 12,
    marginTop: 2,
  },
  dailyButton: {
    backgroundColor: '#FFD700',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  dailyButtonDisabled: {
    backgroundColor: '#333',
  },
  dailyButtonText: {
    color: '#000',
    fontSize: 16,
    fontWeight: 'bold',
  },
  dailyButtonTextDisabled: {
    color: '#666',
  },
  successMessage: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(76, 175, 80, 0.1)',
    padding: 12,
    borderRadius: 8,
    marginBottom: 12,
    gap: 8,
  },
  successText: {
    color: '#4CAF50',
    fontSize: 14,
  },
  featuredContainer: {
    marginBottom: 24,
  },
  featuredCard: {
    width: 150,
    height: 200,
    marginRight: 12,
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: '#1a1a2e',
  },
  featuredImage: {
    width: '100%',
    height: '100%',
  },
  rarityBadge: {
    position: 'absolute',
    bottom: 8,
    right: 8,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  rarityText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: 'bold',
  },
  emptyFeatured: {
    width: 200,
    height: 200,
    backgroundColor: '#1a1a2e',
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#333',
    borderStyle: 'dashed',
  },
  emptyText: {
    color: '#666',
    fontSize: 16,
    marginTop: 8,
  },
  emptySubtext: {
    color: '#444',
    fontSize: 12,
    marginTop: 4,
  },
});

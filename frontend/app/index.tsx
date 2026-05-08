import React, { useState, useEffect, useRef } from 'react';
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

export default function HomeScreen() {
  const { user, loading, login, logout, claimDailyLogin, userCards, refreshData } = useApp();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [dailyMessage, setDailyMessage] = useState<string | null>(null);
  const [claiming, setClaiming] = useState(false);

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
    } else {
      // Reset so riff plays again on next login
      riffPlayedRef.current = false;
    }
  }, [user?.id]);

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

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#FFD700" />
      </View>
    );
  }

  if (!user) {
    return (
      <SafeAreaView style={styles.container}>
        <Image
          source={{ uri: 'https://customer-assets.emergentagent.com/job_earn-cards/artifacts/zgy2com2_enhanced-1771247671181.jpg' }}
          style={styles.backgroundImage}
          resizeMode="cover"
        />
        <View style={styles.backgroundOverlay} />
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
    );
  }

  const canClaimDaily = user.last_login_date !== new Date().toISOString().split('T')[0];

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.welcomeText}>Welcome back,</Text>
            <Text style={styles.usernameText}>{user.username}!</Text>
          </View>
          <TouchableOpacity onPress={logout} style={styles.logoutButton}>
            <Ionicons name="log-out-outline" size={24} color="#FF4500" />
          </TouchableOpacity>
        </View>

        {/* Stats Cards */}
        <View style={styles.statsContainer}>
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
            <Text style={styles.statValue}>{userCards.length}</Text>
            <Text style={styles.statLabel}>Cards</Text>
          </View>
        </View>

        {/* Daily Login */}
        <View style={styles.dailyContainer}>
          <Text style={styles.sectionTitle}>Daily Bonus</Text>
          {dailyMessage && (
            <View style={styles.successMessage}>
              <Ionicons name="checkmark-circle" size={20} color="#4CAF50" />
              <Text style={styles.successText}>{dailyMessage}</Text>
            </View>
          )}
          <TouchableOpacity
            style={[styles.dailyButton, !canClaimDaily && styles.dailyButtonDisabled]}
            onPress={handleClaimDaily}
            disabled={!canClaimDaily || claiming}
          >
            {claiming ? (
              <ActivityIndicator color="#000" />
            ) : (
              <>
                <Text style={styles.giftEmoji}>🎁</Text>
                <Text style={[styles.dailyButtonText, !canClaimDaily && styles.dailyButtonTextDisabled]}>
                  {canClaimDaily ? 'CLAIM DAILY BONUS' : 'ALREADY CLAIMED TODAY'}
                </Text>
              </>
            )}
          </TouchableOpacity>
        </View>

        {/* Featured Card Preview */}
        <View style={styles.featuredContainer}>
          <Text style={styles.sectionTitle}>Featured Cards</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            {userCards.slice(0, 3).map((uc, index) => (
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
            ))}
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
    </SafeAreaView>
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
  welcomeText: {
    fontSize: 14,
    color: '#888',
  },
  usernameText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
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

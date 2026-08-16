import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Image,
  Pressable,
  SafeAreaView,
  ScrollView,
  Share,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import axios from 'axios';

import { useApp } from '../src/context/AppContext';

const API = 'https://thrash-kan-kidz-api.onrender.com';

type ReferralStatus = {
  referral_code?: string;
  code?: string;
  successful_referrals?: number;
  reward?: {
    coins_each?: number;
    free_packs_each?: number;
  };
  milestone?: {
    required_referrals?: number;
    current_referrals?: number;
    unlocked?: boolean;
  };
  code_used?: string | null;
  referred_by_username?: string | null;
  referral_rewarded?: boolean;
};

export default function ReferralScreen() {
  const { user, refreshData } = useApp();

  const [status, setStatus] = useState<ReferralStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [redeeming, setRedeeming] = useState(false);
  const [enteredCode, setEnteredCode] = useState('');

  const loadStatus = useCallback(async () => {
    if (!user?.id) return;

    try {
      setLoading(true);

      const response = await axios.get(
        `${API}/api/users/${user.id}/referral`
      );

      setStatus(response.data);
    } catch (error: any) {
      console.error('Failed to load referral status:', error);
      Alert.alert(
        'Referral Error',
        error?.response?.data?.detail ||
          'Could not load your referral information.'
      );
    } finally {
      setLoading(false);
    }
  }, [user?.id]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const referralCode =
    status?.referral_code ||
    status?.code ||
    '';

  const successfulReferrals =
    status?.milestone?.current_referrals ??
    status?.successful_referrals ??
    0;

  const requiredReferrals =
    status?.milestone?.required_referrals ??
    5;

  const milestoneUnlocked =
    status?.milestone?.unlocked ??
    successfulReferrals >= requiredReferrals;

  const codeAlreadyUsed = Boolean(status?.code_used);

  const shareReferral = async () => {
    if (!referralCode) {
      Alert.alert(
        'Referral Code',
        'Your referral code is not available yet.'
      );
      return;
    }

    const message =
      `Join me on Thrash Kan Kidz!\n\n` +
      `Use my referral code: ${referralCode}\n\n` +
      `Open your first pack and we BOTH get 500 coins + 1 free pack!\n\n` +
      `Download Thrash Kan Kidz on Google Play.`;

    try {
      const result = await Share.share({
        message,
      });

      console.log('Referral share result:', result);
    } catch (error: any) {
      console.error('Referral share failed:', error);

      Alert.alert(
        'Share Failed',
        error?.message ||
          String(error) ||
          'Your device could not open the share menu.'
      );
    }
  };

  const redeemCode = async () => {
    if (!user?.id || redeeming) return;

    const code = enteredCode.trim().toUpperCase();

    if (!code) {
      Alert.alert('Enter a Code', 'Enter your friend’s referral code first.');
      return;
    }

    try {
      setRedeeming(true);

      const response = await axios.post(
        `${API}/api/users/${user.id}/referral/redeem`,
        { code }
      );

      Alert.alert(
        'REFERRAL ACCEPTED! 🤘',
        response.data?.message ||
          'Open your first pack and both players will get 500 coins + 1 free pack!'
      );

      setEnteredCode('');
      await loadStatus();

      try {
        await refreshData();
      } catch {}
    } catch (error: any) {
      Alert.alert(
        'Referral Code',
        error?.response?.data?.detail ||
          'Could not redeem that referral code.'
      );
    } finally {
      setRedeeming(false);
    }
  };

  if (!user) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.center}>
          <Text style={styles.errorText}>No player signed in.</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
      >
        <View style={styles.header}>
          <Pressable
            onPress={() => router.back()}
            style={styles.backButton}
          >
            <Ionicons
              name="arrow-back"
              size={26}
              color="#39ff14"
            />
          </Pressable>

          <View style={{ flex: 1 }}>
            <Text style={styles.title}>REFER A METALHEAD</Text>
            <Text style={styles.subtitle}>
              Grow the pit. Get rewarded.
            </Text>
          </View>
        </View>

        {loading ? (
          <View style={styles.loadingBox}>
            <ActivityIndicator
              size="large"
              color="#39ff14"
            />
          </View>
        ) : (
          <>
            <View style={styles.rewardCard}>
              <Ionicons
                name="gift"
                size={40}
                color="#FFD700"
              />

              <Text style={styles.rewardHeadline}>
                YOU BOTH GET
              </Text>

              <Text style={styles.rewardAmount}>
                500 COINS
              </Text>

              <Text style={styles.plus}>+</Text>

              <Text style={styles.rewardAmount}>
                1 FREE PACK
              </Text>

              <Text style={styles.rewardFine}>
                Your friend enters your code and opens their first pack.
                Then both accounts get the reward.
              </Text>
            </View>

            <View style={styles.section}>
              <Text style={styles.sectionLabel}>
                YOUR REFERRAL CODE
              </Text>

              <View style={styles.codeBox}>
                <Text style={styles.codeText}>
                  {referralCode || '------'}
                </Text>
              </View>

              <Pressable
                style={styles.primaryButton}
                onPress={shareReferral}
                disabled={!referralCode}
              >
                <Ionicons
                  name="share-social"
                  size={20}
                  color="#050505"
                />
                <Text style={styles.primaryButtonText}>
                  SHARE MY CODE
                </Text>
              </Pressable>
            </View>

            <View style={styles.section}>
              <Text style={styles.sectionLabel}>
                REFERRAL PROGRESS
              </Text>

              <View style={styles.progressRow}>
                <Text style={styles.progressBig}>
                  {successfulReferrals}
                </Text>

                <Text style={styles.progressDivider}>
                  / {requiredReferrals}
                </Text>
              </View>

              <View style={styles.progressTrack}>
                <View
                  style={[
                    styles.progressFill,
                    {
                      width: `${
                        Math.min(
                          successfulReferrals / requiredReferrals,
                          1
                        ) * 100
                      }%`,
                    },
                  ]}
                />
              </View>

              <Text style={styles.progressText}>
                {milestoneUnlocked
                  ? 'EXCLUSIVE REFERRAL CARD UNLOCKED!'
                  : `${
                      requiredReferrals - successfulReferrals
                    } more successful referral${
                      requiredReferrals - successfulReferrals === 1
                        ? ''
                        : 's'
                    } until your exclusive referral card.`}
              </Text>

              {successfulReferrals >= 5 && (
                <View style={styles.referralRewardCardWrap}>
                  <Image
                    source={{
                      uri: 'https://thrash-kan-kidz-api.onrender.com/static/cards/reffer_madness.jpg',
                    }}
                    style={styles.referralRewardCard}
                    resizeMode="contain"
                  />
                  <Text style={styles.referralRewardName}>
                    REFFER MADNESS
                  </Text>
                  <Text style={styles.referralRewardUnlocked}>
                    5 REFERRALS ? UNLOCKED
                  </Text>
                </View>
              )}
            </View>

            <View style={styles.section}>
              <Text style={styles.sectionLabel}>
                GOT A FRIEND'S CODE?
              </Text>

              {codeAlreadyUsed ? (
                <View style={styles.usedBox}>
                  <Ionicons
                    name="checkmark-circle"
                    size={26}
                    color="#39ff14"
                  />

                  <View style={{ flex: 1 }}>
                    <Text style={styles.usedTitle}>
                      Referral code used
                    </Text>

                    <Text style={styles.usedText}>
                      {status?.code_used}
                      {status?.referred_by_username
                        ? ` • Referred by ${status.referred_by_username}`
                        : ''}
                    </Text>

                    {!status?.referral_rewarded && (
                      <Text style={styles.pendingText}>
                        Open your first pack to trigger both rewards.
                      </Text>
                    )}
                  </View>
                </View>
              ) : (
                <>
                  <Text style={styles.enterHelp}>
                    New players can enter one referral code before
                    opening their first pack.
                  </Text>

                  <TextInput
                    value={enteredCode}
                    onChangeText={(value) =>
                      setEnteredCode(value.toUpperCase())
                    }
                    placeholder="ENTER CODE"
                    placeholderTextColor="#666"
                    autoCapitalize="characters"
                    autoCorrect={false}
                    maxLength={12}
                    style={styles.input}
                  />

                  <Pressable
                    style={[
                      styles.redeemButton,
                      redeeming && styles.buttonDisabled,
                    ]}
                    onPress={redeemCode}
                    disabled={redeeming}
                  >
                    {redeeming ? (
                      <ActivityIndicator color="#fff" />
                    ) : (
                      <>
                        <Ionicons
                          name="flame"
                          size={20}
                          color="#fff"
                        />
                        <Text style={styles.redeemButtonText}>
                          USE REFERRAL CODE
                        </Text>
                      </>
                    )}
                  </Pressable>
                </>
              )}
            </View>

            <Text style={styles.rules}>
              One referral code per account. You cannot use your own code.
              Rewards are issued once after the referred player successfully
              opens their first qualifying pack.
            </Text>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: '#050505',
  },

  container: {
    flex: 1,
  },

  content: {
    padding: 18,
    paddingBottom: 50,
  },

  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 22,
  },

  backButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: '#39ff14',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },

  title: {
    color: '#39ff14',
    fontSize: 27,
    fontWeight: '900',
    letterSpacing: 1,
  },

  subtitle: {
    color: '#aaa',
    fontSize: 14,
    marginTop: 2,
  },

  loadingBox: {
    paddingVertical: 80,
  },

  rewardCard: {
    borderWidth: 2,
    borderColor: '#39ff14',
    backgroundColor: '#101010',
    borderRadius: 18,
    padding: 22,
    alignItems: 'center',
    marginBottom: 18,
  },

  rewardHeadline: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '800',
    marginTop: 8,
  },

  rewardAmount: {
    color: '#FFD700',
    fontSize: 29,
    fontWeight: '900',
    marginTop: 3,
  },

  plus: {
    color: '#39ff14',
    fontSize: 22,
    fontWeight: '900',
  },

  rewardFine: {
    color: '#bbb',
    fontSize: 13,
    lineHeight: 19,
    textAlign: 'center',
    marginTop: 12,
  },

  section: {
    backgroundColor: '#111',
    borderWidth: 1,
    borderColor: '#292929',
    borderRadius: 16,
    padding: 17,
    marginBottom: 15,
  },

  sectionLabel: {
    color: '#fff',
    fontWeight: '900',
    fontSize: 15,
    marginBottom: 12,
    letterSpacing: 0.8,
  },

  codeBox: {
    backgroundColor: '#030303',
    borderWidth: 2,
    borderStyle: 'dashed',
    borderColor: '#39ff14',
    borderRadius: 12,
    paddingVertical: 15,
    paddingHorizontal: 10,
    alignItems: 'center',
    marginBottom: 12,
  },

  codeText: {
    color: '#39ff14',
    fontSize: 30,
    fontWeight: '900',
    letterSpacing: 6,
  },

  primaryButton: {
    height: 50,
    backgroundColor: '#39ff14',
    borderRadius: 11,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },

  primaryButtonText: {
    color: '#050505',
    fontWeight: '900',
    fontSize: 15,
  },

  progressRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
  },

  progressBig: {
    color: '#39ff14',
    fontSize: 34,
    fontWeight: '900',
  },

  progressDivider: {
    color: '#777',
    fontSize: 20,
    fontWeight: '800',
  },

  progressTrack: {
    height: 12,
    backgroundColor: '#252525',
    borderRadius: 6,
    overflow: 'hidden',
    marginVertical: 10,
  },

  progressFill: {
    height: '100%',
    backgroundColor: '#39ff14',
    borderRadius: 6,
  },

  progressText: {
    color: '#bbb',
    fontSize: 13,
    lineHeight: 19,
  },

  enterHelp: {
    color: '#999',
    fontSize: 13,
    lineHeight: 18,
    marginBottom: 10,
  },

  input: {
    height: 52,
    backgroundColor: '#050505',
    borderColor: '#444',
    borderWidth: 1,
    borderRadius: 10,
    color: '#fff',
    fontSize: 20,
    fontWeight: '900',
    letterSpacing: 3,
    paddingHorizontal: 14,
    textAlign: 'center',
    marginBottom: 10,
  },

  redeemButton: {
    height: 50,
    backgroundColor: '#7d1818',
    borderRadius: 11,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 8,
  },

  redeemButtonText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '900',
  },

  buttonDisabled: {
    opacity: 0.55,
  },

  usedBox: {
    flexDirection: 'row',
    gap: 10,
    alignItems: 'flex-start',
    backgroundColor: '#071207',
    borderWidth: 1,
    borderColor: '#215621',
    borderRadius: 11,
    padding: 13,
  },

  usedTitle: {
    color: '#39ff14',
    fontWeight: '900',
    fontSize: 15,
  },

  usedText: {
    color: '#bbb',
    fontSize: 13,
    marginTop: 2,
  },

  pendingText: {
    color: '#FFD700',
    marginTop: 5,
    fontSize: 12,
  },

  rules: {
    color: '#666',
    textAlign: 'center',
    fontSize: 11,
    lineHeight: 17,
    marginTop: 4,
  },

  errorText: {
    color: '#fff',
  },
  referralRewardCardWrap: {
    alignItems: 'center',
    marginTop: 18,
    paddingTop: 14,
    borderTopWidth: 1,
    borderTopColor: '#244224',
  },
  referralRewardCard: {
    width: 180,
    height: 260,
    borderRadius: 10,
  },
  referralRewardName: {
    color: '#39ff14',
    fontSize: 18,
    fontWeight: '900',
    letterSpacing: 1.5,
    marginTop: 8,
  },
  referralRewardUnlocked: {
    color: '#00BFFF',
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1,
    marginTop: 3,
  },

});

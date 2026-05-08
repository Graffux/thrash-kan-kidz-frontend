import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Image as ExpoImage } from 'expo-image';
import { useApp } from '../src/context/AppContext';

const BACKGROUND_IMAGE = 'https://customer-assets.emergentagent.com/job_earn-cards/artifacts/zgy2com2_enhanced-1771247671181.jpg';

export default function GoalsScreen() {
  const { user, userGoals, allCards } = useApp();

  if (!user) {
    return (
      <SafeAreaView style={styles.container}>
        <Image source={{ uri: BACKGROUND_IMAGE }} style={styles.backgroundImage} resizeMode="cover" />
        <View style={styles.backgroundOverlay} />
        <View style={styles.centerContainer}>
          <Text style={styles.lockIcon}>🔒</Text>
          <Text style={styles.lockedText}>Please login to view your goals</Text>
        </View>
      </SafeAreaView>
    );
  }

  const getGoalIcon = (goalType: string) => {
    switch (goalType) {
      case 'daily_login':
        return '📅';
      case 'profile_complete':
        return '👤';
      case 'collect_coins':
        return '💰';
      case 'collect_cards':
        return '🃏';
      case 'collect_all_variants_series':
        return '✨';
      case 'collect_all_rarities':
        return '🏆';
      default:
        return '⭐';
    }
  };

  // Variant series goals store series number in target_value; the real
  // denominator is the total number of variant cards in that series (64).
  const VARIANTS_PER_SERIES = 64;
  const getDenominator = (goal: any) => {
    if (goal.goal_type === 'collect_all_variants_series') {
      return VARIANTS_PER_SERIES;
    }
    return goal.target_value;
  };

  const getRewardCardName = (cardId: string | null) => {
    if (!cardId) return null;
    const card = allCards.find(c => c.id === cardId);
    return card?.name || 'Mystery Card';
  };

  const completedGoals = userGoals.filter(ug => ug.user_goal.completed);
  const inProgressGoals = userGoals.filter(ug => !ug.user_goal.completed);

  return (
    <SafeAreaView style={styles.container}>
      <Image source={{ uri: BACKGROUND_IMAGE }} style={styles.backgroundImage} resizeMode="cover" />
      <View style={styles.backgroundOverlay} />
      <View style={styles.header}>
        <ExpoImage source={{ uri: 'https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/gkgk0gcw_enhanced-1776904123985.png' }} style={styles.headerImage} contentFit="contain" />
        <Text style={styles.subtitle}>
          {completedGoals.length} / {userGoals.length} Completed
        </Text>
      </View>

      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        {/* Progress Overview */}
        <View style={styles.progressOverview}>
          <View style={styles.progressCircle}>
            <Text style={styles.progressPercent}>
              {userGoals.length > 0
                ? Math.round((completedGoals.length / userGoals.length) * 100)
                : 0}%
            </Text>
            <Text style={styles.progressLabel}>Complete</Text>
          </View>
        </View>

        {/* In Progress */}
        {inProgressGoals.length > 0 && (
          <>
            <Text style={styles.sectionTitle}>In Progress</Text>
            {inProgressGoals.map(({ user_goal, goal }) => (
              <View key={user_goal.id} style={styles.goalCard}>
                <View style={styles.goalIcon}>
                  <Text style={styles.goalIconEmoji}>{getGoalIcon(goal.goal_type)}</Text>
                </View>
                <View style={styles.goalContent}>
                  <Text style={styles.goalTitle}>{goal.title}</Text>
                  <Text style={styles.goalDescription}>{goal.description}</Text>
                  
                  {/* Progress Bar */}
                  <View style={styles.progressBarContainer}>
                    <View style={styles.progressBarBg}>
                      <View
                        style={[
                          styles.progressBarFill,
                          {
                            width: `${Math.min(
                              (user_goal.progress / getDenominator(goal)) * 100,
                              100
                            )}%`,
                          },
                        ]}
                      />
                    </View>
                    <Text style={styles.progressText}>
                      {user_goal.progress} / {getDenominator(goal)}
                    </Text>
                  </View>

                  {/* Rewards */}
                  <View style={styles.rewardsContainer}>
                    <View style={styles.rewardItem}>
                      <Text style={styles.rewardEmoji}>💰</Text>
                      <Text style={styles.rewardText}>+{goal.reward_coins}</Text>
                    </View>
                    {goal.reward_card_id && (
                      <View style={styles.rewardItem}>
                        <Ionicons name="gift" size={14} color="#9932CC" />
                        <Text style={styles.rewardText}>
                          {getRewardCardName(goal.reward_card_id)}
                        </Text>
                      </View>
                    )}
                  </View>
                </View>
              </View>
            ))}
          </>
        )}

        {/* Completed */}
        {completedGoals.length > 0 && (
          <>
            <Text style={styles.sectionTitle}>Completed</Text>
            {completedGoals.map(({ user_goal, goal }) => (
              <View key={user_goal.id} style={[styles.goalCard, styles.goalCardCompleted]}>
                <View style={[styles.goalIcon, styles.goalIconCompleted]}>
                  <Ionicons name="checkmark" size={24} color="#4CAF50" />
                </View>
                <View style={styles.goalContent}>
                  <Text style={[styles.goalTitle, styles.goalTitleCompleted]}>
                    {goal.title}
                  </Text>
                  <Text style={styles.goalDescription}>{goal.description}</Text>
                  <View style={styles.completedBadge}>
                    <Ionicons name="checkmark-circle" size={16} color="#4CAF50" />
                    <Text style={styles.completedText}>Completed</Text>
                  </View>
                </View>
              </View>
            ))}
          </>
        )}

        {userGoals.length === 0 && (
          <View style={styles.emptyState}>
            <Ionicons name="trophy-outline" size={64} color="#666" />
            <Text style={styles.emptyText}>No goals available yet</Text>
          </View>
        )}

        <View style={styles.spacer} />
      </ScrollView>
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
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
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
    marginTop: 16,
    textAlign: 'center',
  },
  header: {
    paddingHorizontal: 16,
    paddingVertical: 20,
  },
  headerImage: {
    width: 180,
    height: 80,
    alignSelf: 'center',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
  },
  subtitle: {
    fontSize: 14,
    color: '#ccc',
    marginTop: 4,
  },
  scrollView: {
    flex: 1,
    paddingHorizontal: 16,
  },
  progressOverview: {
    alignItems: 'center',
    marginBottom: 24,
  },
  progressCircle: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: '#1a1a2e',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 4,
    borderColor: '#FFD700',
  },
  progressPercent: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#FFD700',
  },
  progressLabel: {
    fontSize: 12,
    color: '#888',
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 16,
    marginTop: 8,
  },
  goalCard: {
    flexDirection: 'row',
    backgroundColor: 'rgba(26, 26, 46, 0.9)',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  goalCardCompleted: {
    opacity: 0.7,
    borderColor: '#4CAF50',
  },
  goalIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(255, 215, 0, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16,
  },
  goalIconEmoji: {
    fontSize: 24,
  },
  goalIconCompleted: {
    backgroundColor: 'rgba(76, 175, 80, 0.1)',
  },
  goalContent: {
    flex: 1,
  },
  goalTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 4,
  },
  goalTitleCompleted: {
    color: '#4CAF50',
  },
  goalDescription: {
    fontSize: 13,
    color: '#888',
    marginBottom: 12,
  },
  progressBarContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 12,
  },
  progressBarBg: {
    flex: 1,
    height: 8,
    backgroundColor: '#333',
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: '#FFD700',
    borderRadius: 4,
  },
  progressText: {
    color: '#888',
    fontSize: 12,
    minWidth: 50,
  },
  rewardsContainer: {
    flexDirection: 'row',
    marginTop: 8,
  },
  rewardItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 16,
  },
  rewardEmoji: {
    fontSize: 14,
    marginRight: 4,
  },
  rewardText: {
    color: '#ccc',
    fontSize: 12,
  },
  completedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  completedText: {
    color: '#4CAF50',
    fontSize: 12,
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 48,
  },
  emptyText: {
    color: '#666',
    fontSize: 16,
    marginTop: 16,
  },
  spacer: {
    height: 24,
  },
});

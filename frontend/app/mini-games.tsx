import React, { useState } from 'react';
import {
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';

import { useApp } from '../src/context/AppContext';
import { useSoundPlayer } from '../src/utils/sounds';
import { DailyWheelModal } from '../src/components/DailyWheelModal';
import { CardPickerModal } from '../src/components/CardPickerModal';

export default function MiniGamesScreen() {
  const { user, apiUrl, refreshData } = useApp();

  const [showDailyWheel, setShowDailyWheel] = useState(false);
  const [showCardPicker, setShowCardPicker] = useState(false);
  const [wheelStreak, setWheelStreak] = useState(0);

  const buttonTapSound = useSoundPlayer('button_tap');
  const prizeWonSound = useSoundPlayer('prize_won');

  const openDailyWheel = async () => {
    if (!user) return;

    buttonTapSound.play();

    try {
      const res = await fetch(
        `${apiUrl}/api/users/${user.id}/daily-wheel`
      );

      const data = await res.json();

      setWheelStreak(data.wheel_streak || 0);
    } catch (err) {
      console.error('Error loading daily wheel:', err);
    }

    setShowDailyWheel(true);
  };

  const handleWheelSpin = async () => {
    if (!user) {
      throw new Error('Not logged in');
    }

    const res = await fetch(
      `${apiUrl}/api/users/${user.id}/daily-wheel/spin`,
      {
        method: 'POST',
      }
    );

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to spin');
    }

    const data = await res.json();

    setWheelStreak(data.streak || 0);

    refreshData();

    return data;
  };

  if (!user) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.center}>
          <Text style={styles.emptyText}>No player signed in.</Text>
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
          <TouchableOpacity
            style={styles.backButton}
            onPress={() => router.back()}
          >
            <Ionicons
              name="arrow-back"
              size={26}
              color="#39ff14"
            />
          </TouchableOpacity>

          <View style={{ flex: 1 }}>
            <Text style={styles.title}>MINI-GAMES</Text>
            <Text style={styles.subtitle}>
              Spin it. Pick it. Win stuff.
            </Text>
          </View>
        </View>

        <TouchableOpacity
          style={styles.gameCard}
          activeOpacity={0.85}
          onPress={openDailyWheel}
        >
          <View style={styles.iconCircle}>
            <Text style={styles.emoji}>??</Text>
          </View>

          <View style={{ flex: 1 }}>
            <Text style={styles.gameTitle}>
              DAILY WHEEL
            </Text>

            <Text style={styles.gameSub}>
              One free spin every day
            </Text>
          </View>

          <Ionicons
            name="chevron-forward"
            size={24}
            color="#FFD700"
          />
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.gameCard}
          activeOpacity={0.85}
          onPress={() => {
            buttonTapSound.play();
            setShowCardPicker(true);
          }}
        >
          <View style={styles.iconCircle}>
            <Text style={styles.emoji}>??</Text>
          </View>

          <View style={{ flex: 1 }}>
            <Text style={styles.gameTitle}>
              CARD PICKER
            </Text>

            <Text style={styles.gameSub}>
              Match a pair, win a prize
            </Text>
          </View>

          <Ionicons
            name="chevron-forward"
            size={24}
            color="#FFD700"
          />
        </TouchableOpacity>

        <Text style={styles.note}>
          Metal Musick Trivia has its own menu card.
        </Text>
      </ScrollView>

      <DailyWheelModal
        visible={showDailyWheel}
        onClose={() => {
          setShowDailyWheel(false);
          refreshData();
        }}
        onSpin={handleWheelSpin}
        streak={wheelStreak}
        onSpinStart={() => buttonTapSound.play()}
        onPrizeWon={() => {
          prizeWonSound.play();
          refreshData();
        }}
      />

      <CardPickerModal
        visible={showCardPicker}
        onClose={() => {
          setShowCardPicker(false);
          refreshData();
        }}
        apiUrl={apiUrl}
        userId={user.id}
        onPrizeWon={() => {
          prizeWonSound.play();
          refreshData();
        }}
      />
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
    paddingBottom: 40,
  },

  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },

  emptyText: {
    color: '#fff',
  },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 24,
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
    fontSize: 30,
    fontWeight: '900',
    letterSpacing: 1.5,
  },

  subtitle: {
    color: '#aaa',
    fontSize: 14,
    marginTop: 2,
  },

  gameCard: {
    minHeight: 100,
    borderRadius: 16,
    borderWidth: 2,
    borderColor: '#39ff14',
    backgroundColor: '#111',
    padding: 16,
    marginBottom: 16,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
  },

  iconCircle: {
    width: 62,
    height: 62,
    borderRadius: 31,
    backgroundColor: '#191919',
    borderWidth: 1,
    borderColor: '#444',
    alignItems: 'center',
    justifyContent: 'center',
  },

  emoji: {
    fontSize: 34,
  },

  gameTitle: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '900',
    letterSpacing: 1,
  },

  gameSub: {
    color: '#aaa',
    marginTop: 3,
    fontSize: 13,
  },

  note: {
    color: '#666',
    textAlign: 'center',
    fontSize: 12,
    marginTop: 8,
  },
});

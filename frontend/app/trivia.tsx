import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
  Image
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useApp } from '../src/context/AppContext';

type TriviaQuestion = {
  id: string;
  category: string;
  difficulty: string;
  question: string;
  answers: string[];
};

type TriviaStatus = {
  played_today: boolean;
  session_started: boolean;
  perfect_days: number;
  perfect_days_toward_next_pack: number;
  perfect_days_required: number;
  no_dupes_packs: number;
  last_score: number | null;
};

type TriviaPayload = {
  title: string;
  question_count: number;
  questions: TriviaQuestion[];
};

type TriviaResult = {
  success: boolean;
  score: number;
  total_questions: number;
  perfect: boolean;
  coins_awarded: number;
  total_coins: number;
  perfect_days: number;
  perfect_days_toward_next_pack: number;
  perfect_days_required: number;
  no_dupes_pack_awarded: boolean;
  no_dupes_packs: number;
};

export default function TriviaScreen() {
  const { user, apiUrl, refreshData } = useApp();

  const [status, setStatus] = useState<TriviaStatus | null>(null);
  const [questions, setQuestions] = useState<TriviaQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [currentIndex, setCurrentIndex] = useState(0);
  const [result, setResult] = useState<TriviaResult | null>(null);

  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [openingPack, setOpeningPack] = useState(false);

  const currentQuestion = questions[currentIndex] ?? null;
  const selectedAnswer = currentQuestion
    ? answers[currentQuestion.id]
    : undefined;

  const answeredCount = useMemo(
    () => Object.keys(answers).length,
    [answers],
  );

  const loadStatus = useCallback(async () => {
    if (!user?.id) return;

    try {
      const response = await fetch(
        `${apiUrl}/api/users/${user.id}/trivia/status`,
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.detail || 'Could not load trivia status.');
      }

      setStatus(data);
    } catch (error: any) {
      Alert.alert(
        'Trivia Error',
        error?.message || 'Could not load Metal Musick Trivia.',
      );
    } finally {
      setLoading(false);
    }
  }, [apiUrl, user?.id]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const startTrivia = async () => {
    if (!user?.id || starting) return;

    setStarting(true);

    try {
      const response = await fetch(
        `${apiUrl}/api/users/${user.id}/trivia/questions`,
      );

      const data: TriviaPayload & { detail?: string } =
        await response.json();

      if (!response.ok) {
        throw new Error(data?.detail || 'Could not start trivia.');
      }

      setQuestions(data.questions || []);
      setAnswers({});
      setCurrentIndex(0);
      setResult(null);
    } catch (error: any) {
      Alert.alert(
        'Cannot Start',
        error?.message || 'Could not start today’s trivia.',
      );
    } finally {
      setStarting(false);
    }
  };

  const selectAnswer = (answerIndex: number) => {
    if (!currentQuestion || submitting) return;

    setAnswers(previous => ({
      ...previous,
      [currentQuestion.id]: answerIndex,
    }));
  };

  const goNext = () => {
    if (selectedAnswer === undefined) {
      Alert.alert('Pick an Answer', 'Choose one answer before continuing.');
      return;
    }

    if (currentIndex < questions.length - 1) {
      setCurrentIndex(index => index + 1);
    }
  };

  const submitTrivia = async () => {
    if (!user?.id || submitting) return;

    if (answeredCount !== questions.length) {
      Alert.alert(
        'Not Finished',
        'Answer all five questions before submitting.',
      );
      return;
    }

    setSubmitting(true);

    try {
      const response = await fetch(
        `${apiUrl}/api/users/${user.id}/trivia/submit`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            answers: questions.map(question => ({
              question_id: question.id,
              answer_index: answers[question.id],
            })),
          }),
        },
      );

      const data: TriviaResult & { detail?: string } =
        await response.json();

      if (!response.ok) {
        throw new Error(data?.detail || 'Could not submit trivia.');
      }

      setResult(data);
      setStatus(previous => previous
        ? {
            ...previous,
            played_today: true,
            last_score: data.score,
            perfect_days: data.perfect_days,
            perfect_days_toward_next_pack:
              data.perfect_days_toward_next_pack,
            perfect_days_required: data.perfect_days_required,
            no_dupes_packs: data.no_dupes_packs,
          }
        : null);

      await refreshData();
    } catch (error: any) {
      Alert.alert(
        'Submission Error',
        error?.message || 'Could not submit trivia answers.',
      );
    } finally {
      setSubmitting(false);
    }
  };

  const openNoDupesPack = async () => {
    if (!user?.id || openingPack || !status?.no_dupes_packs) return;

    setOpeningPack(true);

    try {
      const response = await fetch(
        `${apiUrl}/api/users/${user.id}/open-no-dupes-pack`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            series: 1,
          }),
        },
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.detail || 'Could not open No-Dupes Pack.');
      }

      setStatus(previous => previous
        ? {
            ...previous,
            no_dupes_packs:
              data.remaining_no_dupes_packs ??
              Math.max(0, previous.no_dupes_packs - 1),
          }
        : previous);

      await refreshData();

      const cardNames = (data.won_cards || [])
        .map((item: any) => {
          const duplicateText = item.is_duplicate ? ' (Duplicate)' : '';
          return `${item.card?.name || 'Unknown Card'}${duplicateText}`;
        })
        .join('\n');

      const exhaustedText = data.guarantee_exhausted
        ? '\n\nSeries 1 is complete, so duplicates were possible.'
        : '';

      Alert.alert(
        'NO-DUPES PACK OPENED',
        `${cardNames}${exhaustedText}`,
      );
    } catch (error: any) {
      Alert.alert(
        'Pack Error',
        error?.message || 'Could not open No-Dupes Pack.',
      );
    } finally {
      setOpeningPack(false);
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.screen}>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color="#FFD700" />
          <Text style={styles.loadingText}>LOADING METAL KNOWLEDGE...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.screen}>
      <View style={styles.header}>
        <Pressable
          onPress={() => router.back()}
          hitSlop={12}
          testID="trivia-back-btn"
        >
          <Ionicons name="chevron-back" size={30} color="#FFD700" />
        </Pressable>

        <Image
          source={require('../assets/images/metal-trivia-header.png')}
          style={{ width: 210, height: 72 }}
          resizeMode="contain"
        />

        <View style={{ width: 30 }} />
      </View>

      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        {!questions.length && !result && (
          <>
            <View style={styles.hero}>
              <Text style={styles.heroEmoji}>🤘</Text>
              <Text style={styles.heroTitle}>PROVE YOUR METAL KNOWLEDGE</Text>
              <Text style={styles.heroText}>
                Five questions. One play per day. Get all five right on
                three different days to earn a No-Dupes Pack.
              </Text>
            </View>

            <View style={styles.progressCard}>
              <Text style={styles.cardLabel}>PERFECT-DAY PROGRESS</Text>

              <View style={styles.skullRow}>
                {Array.from({
                  length: status?.perfect_days_required || 3,
                }).map((_, index) => {
                  const filled =
                    index <
                    (status?.perfect_days_toward_next_pack || 0);

                  return (
                    <Text
                      key={index}
                      style={[
                        styles.skull,
                        filled && styles.skullFilled,
                      ]}
                    >
                      ☠
                    </Text>
                  );
                })}
              </View>

              <Text style={styles.progressText}>
                {status?.perfect_days_toward_next_pack || 0}
                {' / '}
                {status?.perfect_days_required || 3}
                {' perfect days'}
              </Text>

              <Text style={styles.packCount}>
                NO-DUPES PACKS: {status?.no_dupes_packs || 0}
              </Text>
            </View>

            {status?.played_today ? (
              <View style={styles.completedCard}>
                <Ionicons
                  name="checkmark-circle"
                  size={54}
                  color="#7CFF4F"
                />
                <Text style={styles.completedTitle}>
                  TODAY’S TRIVIA COMPLETE
                </Text>
                <Text style={styles.completedText}>
                  Score: {status.last_score ?? 0} / 5
                </Text>
                <Text style={styles.completedText}>
                  Come back after the daily reset.
                </Text>
              </View>
            ) : (
              <Pressable
                style={({ pressed }) => [
                  styles.startButton,
                  pressed && styles.buttonPressed,
                ]}
                onPress={startTrivia}
                disabled={starting}
                testID="trivia-start-btn"
              >
                {starting ? (
                  <ActivityIndicator color="#090909" />
                ) : (
                  <>
                    <Ionicons
                      name="flash"
                      size={22}
                      color="#090909"
                    />
                    <Text style={styles.startButtonText}>
                      START TODAY’S TRIVIA
                    </Text>
                  </>
                )}
              </Pressable>
            )}
          </>
        )}

        {!!questions.length && !result && currentQuestion && (
          <>
            <View style={styles.questionTop}>
              <Text style={styles.questionNumber}>
                QUESTION {currentIndex + 1} OF {questions.length}
              </Text>

              <Text style={styles.category}>
                {currentQuestion.category.toUpperCase()}
                {' • '}
                {currentQuestion.difficulty.toUpperCase()}
              </Text>
            </View>

            <View style={styles.progressTrack}>
              <View
                style={[
                  styles.progressFill,
                  {
                    width:
                      `${((currentIndex + 1) / questions.length) * 100}%`,
                  },
                ]}
              />
            </View>

            <View style={styles.questionCard}>
              <Text style={styles.questionText}>
                {currentQuestion.question}
              </Text>
            </View>

            <View style={styles.answerList}>
              {currentQuestion.answers.map((answer, answerIndex) => {
                const selected = selectedAnswer === answerIndex;

                return (
                  <Pressable
                    key={`${currentQuestion.id}-${answerIndex}`}
                    style={({ pressed }) => [
                      styles.answerButton,
                      selected && styles.answerButtonSelected,
                      pressed && styles.buttonPressed,
                    ]}
                    onPress={() => selectAnswer(answerIndex)}
                    testID={`trivia-answer-${answerIndex}`}
                  >
                    <View
                      style={[
                        styles.answerLetter,
                        selected && styles.answerLetterSelected,
                      ]}
                    >
                      <Text
                        style={[
                          styles.answerLetterText,
                          selected && styles.answerLetterTextSelected,
                        ]}
                      >
                        {String.fromCharCode(65 + answerIndex)}
                      </Text>
                    </View>

                    <Text
                      style={[
                        styles.answerText,
                        selected && styles.answerTextSelected,
                      ]}
                    >
                      {answer}
                    </Text>
                  </Pressable>
                );
              })}
            </View>

            <View style={styles.navigationRow}>
              <Pressable
                style={[
                  styles.secondaryButton,
                  currentIndex === 0 && styles.disabledButton,
                ]}
                disabled={currentIndex === 0}
                onPress={() =>
                  setCurrentIndex(index => Math.max(0, index - 1))
                }
              >
                <Ionicons
                  name="chevron-back"
                  size={20}
                  color="#FFD700"
                />
                <Text style={styles.secondaryButtonText}>BACK</Text>
              </Pressable>

              {currentIndex < questions.length - 1 ? (
                <Pressable
                  style={({ pressed }) => [
                    styles.nextButton,
                    selectedAnswer === undefined &&
                      styles.disabledButton,
                    pressed && styles.buttonPressed,
                  ]}
                  disabled={selectedAnswer === undefined}
                  onPress={goNext}
                >
                  <Text style={styles.nextButtonText}>NEXT</Text>
                  <Ionicons
                    name="chevron-forward"
                    size={20}
                    color="#090909"
                  />
                </Pressable>
              ) : (
                <Pressable
                  style={({ pressed }) => [
                    styles.nextButton,
                    answeredCount !== questions.length &&
                      styles.disabledButton,
                    pressed && styles.buttonPressed,
                  ]}
                  disabled={
                    answeredCount !== questions.length || submitting
                  }
                  onPress={submitTrivia}
                  testID="trivia-submit-btn"
                >
                  {submitting ? (
                    <ActivityIndicator color="#090909" />
                  ) : (
                    <>
                      <Text style={styles.nextButtonText}>
                        SUBMIT
                      </Text>
                      <Ionicons
                        name="skull"
                        size={20}
                        color="#090909"
                      />
                    </>
                  )}
                </Pressable>
              )}
            </View>
          </>
        )}

        {result && (
          <View style={styles.resultCard}>
            <Text style={styles.resultEmoji}>
              {result.perfect ? '🏆' : result.score >= 3 ? '🤘' : '💀'}
            </Text>

            <Text style={styles.resultTitle}>
              {result.perfect
                ? 'PERFECT SCORE!'
                : result.score >= 3
                  ? 'SOLID METAL KNOWLEDGE'
                  : 'BACK TO THE REHEARSAL ROOM'}
            </Text>

            <Text style={styles.resultScore}>
              {result.score} / {result.total_questions}
            </Text>

            <Text style={styles.rewardText}>
              +{result.coins_awarded} COINS
            </Text>

            {result.no_dupes_pack_awarded && (
              <View style={styles.packAward}>
                <Ionicons name="gift" size={30} color="#7CFF4F" />
                <Text style={styles.packAwardTitle}>
                  NO-DUPES PACK EARNED!
                </Text>
                <Text style={styles.packAwardText}>
                  Your new pack has been added to your account.
                </Text>
              </View>
            )}

            <Text style={styles.resultProgress}>
              Perfect-day progress:{' '}
              {result.perfect_days_toward_next_pack}
              {' / '}
              {result.perfect_days_required}
            </Text>

            <Pressable
              style={({ pressed }) => [
                styles.startButton,
                pressed && styles.buttonPressed,
              ]}
              onPress={() => router.back()}
            >
              <Text style={styles.startButtonText}>BACK TO HOME</Text>
            </Pressable>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#08080d',
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  loadingText: {
    color: '#FFD700',
    fontWeight: '900',
    marginTop: 16,
    letterSpacing: 1,
  },
  header: {
    minHeight: 58,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 215, 0, 0.35)',
    backgroundColor: '#111118',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerTitle: {
    color: '#FFD700',
    fontSize: 17,
    fontWeight: '900',
    letterSpacing: 1,
  },
  content: {
    padding: 18,
    paddingBottom: 60,
  },
  hero: {
    alignItems: 'center',
    paddingVertical: 22,
  },
  heroEmoji: {
    fontSize: 70,
  },
  heroTitle: {
    color: '#FFFFFF',
    fontSize: 23,
    lineHeight: 29,
    fontWeight: '900',
    textAlign: 'center',
    marginTop: 10,
  },
  heroText: {
    color: '#BBBBBB',
    fontSize: 15,
    lineHeight: 22,
    textAlign: 'center',
    marginTop: 12,
  },
  progressCard: {
    backgroundColor: '#14141d',
    borderWidth: 1,
    borderColor: 'rgba(255, 215, 0, 0.45)',
    borderRadius: 14,
    padding: 18,
    alignItems: 'center',
    marginBottom: 20,
  },
  cardLabel: {
    color: '#FFD700',
    fontWeight: '900',
    letterSpacing: 1,
    fontSize: 13,
  },
  skullRow: {
    flexDirection: 'row',
    gap: 16,
    marginVertical: 14,
  },
  skull: {
    fontSize: 42,
    color: '#454550',
  },
  skullFilled: {
    color: '#7CFF4F',
  },
  progressText: {
    color: '#DDDDDD',
    fontWeight: '700',
  },
  packCount: {
    color: '#7CFF4F',
    fontWeight: '900',
    marginTop: 10,
  },
  completedCard: {
    backgroundColor: '#121b12',
    borderWidth: 1,
    borderColor: '#7CFF4F',
    borderRadius: 14,
    padding: 24,
    alignItems: 'center',
  },
  completedTitle: {
    color: '#7CFF4F',
    fontWeight: '900',
    fontSize: 19,
    marginTop: 10,
  },
  completedText: {
    color: '#DDDDDD',
    marginTop: 7,
  },
  startButton: {
    minHeight: 56,
    borderRadius: 12,
    backgroundColor: '#FFD700',
    flexDirection: 'row',
    gap: 9,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 20,
  },
  startButtonText: {
    color: '#090909',
    fontWeight: '900',
    fontSize: 15,
    letterSpacing: 0.7,
  },
  questionTop: {
    marginBottom: 10,
  },
  questionNumber: {
    color: '#FFD700',
    fontWeight: '900',
    fontSize: 16,
  },
  category: {
    color: '#888899',
    fontWeight: '700',
    marginTop: 4,
    fontSize: 12,
  },
  progressTrack: {
    height: 7,
    backgroundColor: '#252531',
    borderRadius: 20,
    overflow: 'hidden',
    marginBottom: 20,
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#7CFF4F',
  },
  questionCard: {
    minHeight: 145,
    justifyContent: 'center',
    backgroundColor: '#15151f',
    borderWidth: 1.5,
    borderColor: '#FFD700',
    borderRadius: 14,
    padding: 22,
    marginBottom: 18,
  },
  questionText: {
    color: '#FFFFFF',
    fontSize: 21,
    lineHeight: 29,
    fontWeight: '900',
    textAlign: 'center',
  },
  answerList: {
    gap: 11,
  },
  answerButton: {
    minHeight: 65,
    backgroundColor: '#15151f',
    borderWidth: 1,
    borderColor: '#3b3b49',
    borderRadius: 12,
    padding: 12,
    flexDirection: 'row',
    alignItems: 'center',
  },
  answerButtonSelected: {
    backgroundColor: '#2c2608',
    borderColor: '#FFD700',
    borderWidth: 2,
  },
  answerLetter: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: '#2a2a36',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  answerLetterSelected: {
    backgroundColor: '#FFD700',
  },
  answerLetterText: {
    color: '#FFFFFF',
    fontWeight: '900',
  },
  answerLetterTextSelected: {
    color: '#090909',
  },
  answerText: {
    flex: 1,
    color: '#E8E8E8',
    fontSize: 16,
    fontWeight: '700',
  },
  answerTextSelected: {
    color: '#FFFFFF',
  },
  navigationRow: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 22,
  },
  secondaryButton: {
    flex: 1,
    minHeight: 54,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#FFD700',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
  },
  secondaryButtonText: {
    color: '#FFD700',
    fontWeight: '900',
  },
  nextButton: {
    flex: 1.4,
    minHeight: 54,
    borderRadius: 12,
    backgroundColor: '#FFD700',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 5,
  },
  nextButtonText: {
    color: '#090909',
    fontWeight: '900',
    fontSize: 15,
  },
  disabledButton: {
    opacity: 0.35,
  },
  buttonPressed: {
    transform: [{ scale: 0.98 }],
    opacity: 0.85,
  },
  resultCard: {
    backgroundColor: '#14141d',
    borderWidth: 1.5,
    borderColor: '#FFD700',
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
  },
  resultEmoji: {
    fontSize: 70,
  },
  resultTitle: {
    color: '#FFFFFF',
    fontSize: 22,
    fontWeight: '900',
    textAlign: 'center',
    marginTop: 10,
  },
  resultScore: {
    color: '#FFD700',
    fontWeight: '900',
    fontSize: 42,
    marginTop: 16,
  },
  rewardText: {
    color: '#7CFF4F',
    fontWeight: '900',
    fontSize: 21,
    marginBottom: 20,
  },
  packAward: {
    width: '100%',
    backgroundColor: '#10200d',
    borderWidth: 1,
    borderColor: '#7CFF4F',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginBottom: 18,
  },
  packAwardTitle: {
    color: '#7CFF4F',
    fontWeight: '900',
    fontSize: 17,
    marginTop: 8,
  },
  packAwardText: {
    color: '#D8FFD0',
    textAlign: 'center',
    marginTop: 6,
  },
  resultProgress: {
    color: '#CCCCCC',
    marginBottom: 22,
    fontWeight: '700',
  },
});


import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  Modal,
  Dimensions,
  Alert,
  ScrollView,
  FlatList,
  Animated,
  Easing,
  Share,
} from 'react-native';
import { Image as ExpoImage } from 'expo-image';
import { headerSource } from '../src/assets/headerCatalog';
import { SafeAreaView } from 'react-native-safe-area-context';
import { GrungeBackground } from '../src/components/GrungeBackground';
import { Ionicons } from '@expo/vector-icons';
import { useApp } from '../src/context/AppContext';
import type { SeriesCatalogEntry } from '../src/context/AppContext';
import { useSoundPlayer } from '../src/utils/sounds';
import { cardThumb, scratchCoverThumb } from '../src/utils/cardImage';
import ScratchCard from '../src/components/ScratchCard';
import OozeProgressBar from '../src/components/OozeProgressBar';
import MetalButton from '../src/components/MetalButton';
import MascotStamp from '../src/components/MascotStamp';
import MascotEmptyState from '../src/components/MascotEmptyState';
import {
  scheduleLaunchNotification,
  cancelLaunchNotification,
  getScheduledNotificationId,
} from '../src/utils/seriesLaunchNotifier';
import { useFocusEffect } from 'expo-router';

const { width } = Dimensions.get('window');
const CARD_WIDTH = (width - 56) / 3;
const CARD_HEIGHT = CARD_WIDTH * 1.5;

interface Card {
  id: string;
  name: string;
  description: string;
  rarity: string;
  front_image_url: string;
  back_image_url: string;
  coin_cost: number;
  series?: number;
  series_reward?: number;
  band?: string;
  card_type?: string;
  base_card_id?: string;
  variant_name?: string;
}

interface UserCard {
  user_card_id: string;
  card: Card;
  quantity: number;
  acquired_at: string;
}

const MYSTERY_CARD_IMAGE = 'https://customer-assets.emergentagent.com/job_d1401514-883f-459a-9a0f-b23503598272/artifacts/tf5khv09_enhanced-1771280968644.jpg';

// Simple Card Component - Shows mystery card if not owned
const SimpleCard = React.memo(({ 
  card,
  isOwned,
  quantity,
  onPress,
  cardFlipPlay,
}: { 
  card: Card;
  isOwned: boolean;
  quantity: number;
  onPress: () => void;
  cardFlipPlay: () => void;
}) => {
  const isVariant = !!card.base_card_id;
  const isReward = card.rarity === 'rare' || card.rarity === 'epic';
  const rewardColor = card.rarity === 'epic' ? '#FF2A2A' : '#FFD700';

  // If not owned, show mystery card
  if (!isOwned) {
    return (
      <RewardGlow active={isReward} color={rewardColor}>
        <View style={[styles.cardContainer, styles.mysteryCard, isReward && { borderWidth: 3, borderColor: rewardColor }]}>
          <ExpoImage
            source={{ uri: MYSTERY_CARD_IMAGE }}
            style={styles.cardImage}
            contentFit="cover"
            cachePolicy="memory-disk"
            recyclingKey="mystery"
            priority="low"
          />
          <View style={styles.mysteryOverlay}>
            <Text style={styles.mysteryText}>?</Text>
          </View>
          {isReward && (
            <View style={[styles.rewardBadge, { backgroundColor: rewardColor }]}>
              <Text style={[styles.rewardBadgeText, card.rarity === 'epic' && { color: '#fff' }]}>REWARD</Text>
            </View>
          )}
        </View>
      </RewardGlow>
    );
  }

  return (
    <RewardGlow active={isReward} color={rewardColor}>
      <SimpleCardOwned
        card={card}
        quantity={quantity}
        onPress={onPress}
        isVariant={isVariant}
        isReward={isReward}
        cardFlipPlay={cardFlipPlay}
      />
    </RewardGlow>
  );
});
SimpleCard.displayName = 'SimpleCard';

// Pulsing halo that wraps any "reward" card (series-completion rares/epics).
// Color is rarity-aware: gold (#FFD700) for `rare`, red (#FF2A2A) for `epic`.
// Why a separate component?
//   * Allows native-driver opacity animation on Android (true glow shadows
//     don't animate on Android — only `elevation`, which can't be smoothly
//     interpolated). The halo View pulses cheaply via opacity instead.
//   * Single Animated.Value per wrapper instance keeps the animation
//     independent across cards but avoids re-rendering the whole component.
// Only ~7 reward cards exist in the catalog, so the animation cost is
// negligible.
const RewardGlow: React.FC<{ active: boolean; color?: string; children: React.ReactNode }> = ({ active, color = '#FFD700', children }) => {
  const pulse = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!active) return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 1, duration: 1100, useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 0, duration: 1100, useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [active, pulse]);

  if (!active) return <>{children}</>;

  const haloOpacity = pulse.interpolate({ inputRange: [0, 1], outputRange: [0.35, 0.95] });
  const haloScale = pulse.interpolate({ inputRange: [0, 1], outputRange: [1, 1.04] });

  return (
    <View style={styles.rewardGlowWrap}>
      <Animated.View
        pointerEvents="none"
        style={[
          styles.rewardGlowHalo,
          { backgroundColor: color, shadowColor: color, opacity: haloOpacity, transform: [{ scale: haloScale }] },
        ]}
      />
      {children}
    </View>
  );
};
RewardGlow.displayName = 'RewardGlow';

// Owned-card subcomponent. Long-press flips the thumbnail in place via a
// single animation value; single tap opens the detail modal.
//
// Memory-tuned (Samsung OOM fix, May 2026): back-face image is lazy-mounted
// only after the user has flipped at least once. This avoids decoding 486
// back-image bitmaps into memory simultaneously when the Collection screen
// first mounts — which was the primary source of
// `java.lang.OutOfMemoryError` on lower-RAM Android devices.
const SimpleCardOwned = React.memo(({
  card,
  quantity,
  onPress,
  isVariant,
  isReward,
  cardFlipPlay,
}: {
  card: Card;
  quantity: number;
  onPress: () => void;
  isVariant: boolean;
  isReward: boolean;
  cardFlipPlay: () => void;
}) => {
  const flipAnim = useRef(new Animated.Value(0)).current;
  const flippingRef = useRef(false);
  const [isFlipped, setIsFlipped] = useState(false);
  // Track whether the user has ever flipped this card. Back image is only
  // mounted after first flip, saving hundreds of image decodes at mount.
  const [hasFlipped, setHasFlipped] = useState(false);

  const flip = () => {
    if (flippingRef.current) return;
    flippingRef.current = true;
    cardFlipPlay();
    setHasFlipped(true);
    const target = isFlipped ? 0 : 1;
    Animated.timing(flipAnim, {
      toValue: target,
      duration: 420,
      useNativeDriver: true,
    }).start(() => {
      flippingRef.current = false;
    });
    setTimeout(() => setIsFlipped(!isFlipped), 210);
  };

  const frontRotate = flipAnim.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '180deg'] });
  const backRotate = flipAnim.interpolate({ inputRange: [0, 1], outputRange: ['180deg', '360deg'] });
  const frontOpacity = flipAnim.interpolate({ inputRange: [0, 0.49, 0.5, 1], outputRange: [1, 1, 0, 0] });
  const backOpacity = flipAnim.interpolate({ inputRange: [0, 0.49, 0.5, 1], outputRange: [0, 0, 1, 1] });

  return (
    <TouchableOpacity
      onPress={onPress}
      onLongPress={flip}
      delayLongPress={250}
      style={[
        styles.cardContainer,
        isVariant && styles.variantCardBorder,
        isReward && { borderWidth: 3, borderColor: card.rarity === 'epic' ? '#FF2A2A' : '#FFD700' },
      ]}
      data-testid={`grid-card-${card.id}`}
    >
      <Animated.View
        style={[
          styles.gridFlipFace,
          { opacity: frontOpacity, transform: [{ rotateY: frontRotate }] },
        ]}
      >
        <ExpoImage
          source={{ uri: cardThumb(card, 240) }}
          style={styles.cardImage}
          contentFit="cover"
          cachePolicy="memory-disk"
          recyclingKey={card.id}
          priority="low"
        />
      </Animated.View>
      {hasFlipped && (
        <Animated.View
          style={[
            styles.gridFlipFace,
            { opacity: backOpacity, transform: [{ rotateY: backRotate }] },
          ]}
        >
          <ExpoImage
            source={{ uri: card.back_image_url || cardThumb(card, 240) }}
            style={styles.cardImage}
            contentFit="cover"
            cachePolicy="memory-disk"
            recyclingKey={`${card.id}-back`}
            priority="low"
          />
        </Animated.View>
      )}
      {quantity > 1 && (
        <View style={styles.quantityBadge}>
          <Text style={styles.quantityText}>x{quantity}</Text>
        </View>
      )}
      {isVariant && (
        <View style={styles.variantBadge}>
          <Text style={styles.variantBadgeText}>VAR</Text>
        </View>
      )}
      {(card as any).is_daily_reward && (
        <View style={styles.dailyRewardBadge} testID={`daily-badge-${card.id}`}>
          <Text style={styles.dailyRewardBadgeText}>🌙</Text>
        </View>
      )}
      <View style={styles.cardNameBadge}>
        <Text style={styles.cardNameText} numberOfLines={1}>
          {card.name}
        </Text>
      </View>
    </TouchableOpacity>
  );
});
SimpleCardOwned.displayName = 'SimpleCardOwned';

// Compact countdown helper. Returns "in 4d 12h", "in 23m", "Live!", or
// null when no date is set.
function formatCountdown(iso: string | null): string | null {
  if (!iso) return null;
  const ms = new Date(iso).getTime() - Date.now();
  if (Number.isNaN(ms)) return null;
  if (ms <= 0) return 'Live!';
  const totalMin = Math.floor(ms / 60000);
  const days = Math.floor(totalMin / (60 * 24));
  const hours = Math.floor((totalMin % (60 * 24)) / 60);
  const mins = totalMin % 60;
  if (days >= 1) return `in ${days}d ${hours}h`;
  if (hours >= 1) return `in ${hours}h ${mins}m`;
  return `in ${mins}m`;
}

// Tile rendered for a series the player can't reach yet. Two flavours:
//   * status="scheduled"   → shows a live countdown to release_date
//                            + "🔔 Notify me at launch" button (subscribes
//                            via expo-notifications, fires at the OS level
//                            even if the app is closed at release time)
//   * status="coming_soon" → shows just "Coming Soon" (no date, no button)
const ComingSoonTile: React.FC<{ entry: SeriesCatalogEntry }> = ({ entry }) => {
  const [, setTick] = useState(0);
  const [subscribed, setSubscribed] = useState(false);
  const [busy, setBusy] = useState(false);

  // Re-render once a minute so the countdown ticks naturally without
  // needing to listen for app focus events.
  useEffect(() => {
    if (entry.status !== 'scheduled') return;
    const id = setInterval(() => setTick(t => t + 1), 60000);
    return () => clearInterval(id);
  }, [entry.status]);

  // Hydrate the subscribed state from AsyncStorage on mount + whenever the
  // release date changes. If the admin reschedules, the existing
  // notification is stale; the helper handles cancel+reschedule on click.
  useEffect(() => {
    let alive = true;
    getScheduledNotificationId(entry.series).then(id => {
      if (alive) setSubscribed(!!id);
    });
    return () => {
      alive = false;
    };
  }, [entry.series, entry.release_date]);

  const countdown = formatCountdown(entry.release_date);
  const subtitle =
    entry.status === 'scheduled' && countdown
      ? `Drops ${countdown}`
      : 'Coming Soon';

  const onTapNotify = async () => {
    if (!entry.release_date || busy) return;
    setBusy(true);
    try {
      if (subscribed) {
        await cancelLaunchNotification(entry.series);
        setSubscribed(false);
        Alert.alert('Notification cancelled', `You won't be alerted when ${entry.name} drops.`);
      } else {
        const result = await scheduleLaunchNotification({
          seriesNum: entry.series,
          seriesName: entry.name,
          description: entry.description,
          releaseDateIso: entry.release_date,
        });
        if (result.ok) {
          setSubscribed(true);
          Alert.alert(
            "You're in 🤘",
            `We'll ping you the second ${entry.name} goes live.`,
          );
        } else {
          Alert.alert('Could not subscribe', result.reason);
        }
      }
    } finally {
      setBusy(false);
    }
  };

  const showNotifyButton = entry.status === 'scheduled' && !!entry.release_date;

  return (
    <View
      style={comingSoonStyles.tile}
      data-testid={`series-${entry.series}-coming-soon`}
    >
      <View style={comingSoonStyles.row}>
        <View style={styles.seriesHeaderLeft}>
          <Text style={comingSoonStyles.title}>
            {entry.name} — {entry.description}
          </Text>
          <Text style={comingSoonStyles.subtitle}>{subtitle}</Text>
        </View>
        <Ionicons name="lock-closed" size={18} color="#777" />
      </View>

      {showNotifyButton && (
        <TouchableOpacity
          style={[
            comingSoonStyles.notifyBtn,
            subscribed && comingSoonStyles.notifyBtnActive,
            busy && comingSoonStyles.notifyBtnBusy,
          ]}
          onPress={onTapNotify}
          disabled={busy}
          data-testid={`series-${entry.series}-notify-btn`}
        >
          <Ionicons
            name={subscribed ? 'notifications' : 'notifications-outline'}
            size={14}
            color={subscribed ? '#000' : '#FFD700'}
          />
          <Text
            style={[
              comingSoonStyles.notifyBtnText,
              subscribed && comingSoonStyles.notifyBtnTextActive,
            ]}
          >
            {subscribed ? "You'll be notified" : 'Notify me at launch'}
          </Text>
        </TouchableOpacity>
      )}
    </View>
  );
};
ComingSoonTile.displayName = 'ComingSoonTile';

const comingSoonStyles = StyleSheet.create({
  tile: {
    backgroundColor: 'rgba(20, 20, 32, 0.85)',
    borderWidth: 1,
    borderColor: 'rgba(255, 215, 0, 0.18)',
    borderStyle: 'dashed',
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 14,
    marginBottom: 12,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  title: {
    fontSize: 15,
    fontWeight: 'bold',
    color: '#bbb',
    letterSpacing: 0.5,
  },
  subtitle: {
    fontSize: 11,
    color: '#FFD700',
    marginTop: 4,
    fontStyle: 'italic',
  },
  notifyBtn: {
    marginTop: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 9,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(255, 215, 0, 0.45)',
    backgroundColor: 'rgba(255, 215, 0, 0.08)',
  },
  notifyBtnActive: {
    backgroundColor: '#FFD700',
    borderColor: '#FFD700',
  },
  notifyBtnBusy: {
    opacity: 0.5,
  },
  notifyBtnText: {
    color: '#FFD700',
    fontSize: 12,
    fontWeight: 'bold',
    letterSpacing: 0.6,
  },
  notifyBtnTextActive: {
    color: '#000',
  },
});

export default function CollectionScreen() {
  const { user, userCards, allCards, seriesCatalog, apiUrl, refreshData } = useApp();
  const [selectedCard, setSelectedCard] = useState<UserCard | null>(null);
  const [showFront, setShowFront] = useState(true);
  const [tradeInEligible, setTradeInEligible] = useState<any[]>([]);
  const [showTradeInResult, setShowTradeInResult] = useState(false);
  const [tradeInResult, setTradeInResult] = useState<any>(null);
  // Trade-in variant scratch state. Set to false the moment a new variant
  // is revealed so the modal hides "AWESOME!" until the user scratches. Set
  // back to true on auto-reveal (or when the won variant has no cover URL).
  const [tradeScratched, setTradeScratched] = useState(true);
  const [isTrading, setIsTrading] = useState(false);
  const cardFlipSound = useSoundPlayer('card_flip');
  const prizeWonSound = useSoundPlayer('prize_won');
  // NOTE: Removed looping `collection_bg` music — was holding an ExoPlayer
  // instance open indefinitely and contributing to OOM on low-RAM Android
  // devices (Samsung testers reported repeat crashes). Can be re-added as
  // an opt-in toggle in Sound Settings later.

  // Series-completion milestone celebration (one-time per series, 200 medals)
  const [milestone, setMilestone] = useState<{ series: number; medals: number } | null>(null);
  const milestoneOpacity = useRef(new Animated.Value(0)).current;
  const milestoneScale = useRef(new Animated.Value(0.6)).current;
  const skullPulse = useRef(new Animated.Value(1)).current;
  // Series numbers we've already attempted to claim this session, regardless of
  // outcome — prevents repeated POSTs while user lingers on Collection tab.
  const milestoneAttemptedRef = useRef<Set<number>>(new Set());

  // Card-detail modal 3D flip animation: 0 = front, 1 = back.
  const detailFlipAnim = useRef(new Animated.Value(0)).current;
  const detailFlipping = useRef(false);
  const flipDetailCard = () => {
    if (detailFlipping.current) return;
    detailFlipping.current = true;
    cardFlipSound.play();
    const target = showFront ? 1 : 0;
    Animated.timing(detailFlipAnim, {
      toValue: target,
      duration: 450,
      useNativeDriver: true,
    }).start(() => {
      detailFlipping.current = false;
    });
    // Flip state mid-rotation so the back-face label updates with the visual flip.
    setTimeout(() => setShowFront(!showFront), 225);
  };
  const detailFrontRotate = detailFlipAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '180deg'],
  });
  const detailBackRotate = detailFlipAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['180deg', '360deg'],
  });
  const detailFrontOpacity = detailFlipAnim.interpolate({
    inputRange: [0, 0.49, 0.5, 1],
    outputRange: [1, 1, 0, 0],
  });
  const detailBackOpacity = detailFlipAnim.interpolate({
    inputRange: [0, 0.49, 0.5, 1],
    outputRange: [0, 0, 1, 1],
  });

  // Collection background music disabled to reduce memory footprint.
  // (Was: useFocusEffect starting/stopping `collectionMusic` looper here.)
  // Default all series to collapsed on mount. The Collection screen used to
  // render all 486 cards inline simultaneously on first paint, which froze
  // low-RAM Android devices (Galaxy A15 5G / 4GB RAM tester report).
  // NOTE: Initial state is an empty object (NOT derived from `seriesNumbers`)
  // because `seriesNumbers` is declared further down in this component. In
  // Hermes production the TDZ makes that reference `undefined`, crashing the
  // screen with "Cannot read property 'reduce' of undefined". Instead we
  // treat any unset key as collapsed via `?? true` at the read site.
  const [collapsedSeries, setCollapsedSeries] = useState<{ [key: number]: boolean }>({});

  const BACKGROUND_IMAGE = 'https://customer-assets.emergentagent.com/job_earn-cards/artifacts/zgy2com2_enhanced-1771247671181.jpg';

  useEffect(() => {
    if (user) {
      fetchTradeInEligible();
    }
  }, [user, userCards]);

  // Series-completion milestone detection. Runs whenever userCards or allCards
  // changes. For each fully-collected series the backend hasn't already paid
  // out for, hit the milestone endpoint. Server is the source of truth — it
  // decides whether to award and is idempotent.
  useEffect(() => {
    if (!user || allCards.length === 0 || userCards.length === 0) return;
    if (milestone) return; // don't fire while another celebration is open

    const ownedIds = new Set(userCards.map(uc => uc.card.id));
    const alreadyClaimed = new Set(user.series_milestone_claimed || []);

    // Derive series list from cards we already have — no hardcoded cap.
    const allSeriesNums = Array.from(
      new Set(
        allCards
          .map(c => c.series ?? (c as any).series_reward)
          .filter((s): s is number => typeof s === 'number' && s > 0),
      ),
    ).sort((a, b) => a - b);

    for (const series of allSeriesNums) {
      if (alreadyClaimed.has(series)) continue;
      if (milestoneAttemptedRef.current.has(series)) continue;

      const seriesCards = allCards.filter(
        c => c.series === series || (c as any).series_reward === series,
      );
      if (seriesCards.length === 0) continue;

      const ownsAll = seriesCards.every(c => ownedIds.has(c.id));
      if (!ownsAll) continue;

      // Eligible: claim + animate.
      milestoneAttemptedRef.current.add(series);
      void claimMilestone(series);
      break; // one celebration at a time; the next focus pass picks up the next series
    }
  }, [user, userCards, allCards, milestone]);

  const claimMilestone = async (series: number) => {
    if (!user) return;
    try {
      const res = await fetch(
        `${apiUrl}/api/users/${user.id}/series-milestone/${series}`,
        { method: 'POST' },
      );
      const data = await res.json();
      if (data?.claimed && data?.medals_awarded > 0) {
        showMilestone(series, data.medals_awarded);
        // Refresh global user/medal state in the background
        refreshData();
      }
    } catch (err) {
      console.error('Series milestone claim failed:', err);
    }
  };

  const showMilestone = (series: number, medals: number) => {
    setMilestone({ series, medals });
    milestoneOpacity.setValue(0);
    milestoneScale.setValue(0.6);
    Animated.parallel([
      Animated.timing(milestoneOpacity, { toValue: 1, duration: 260, useNativeDriver: true }),
      Animated.spring(milestoneScale, { toValue: 1, friction: 5, tension: 80, useNativeDriver: true }),
    ]).start();
    // Skull pulse loop while overlay is visible
    Animated.loop(
      Animated.sequence([
        Animated.timing(skullPulse, { toValue: 1.18, duration: 600, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        Animated.timing(skullPulse, { toValue: 1.0, duration: 600, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      ]),
    ).start();
    try { prizeWonSound.play(); } catch (_e) { /* ignore */ }
  };

  const dismissMilestone = () => {
    Animated.timing(milestoneOpacity, {
      toValue: 0,
      duration: 240,
      useNativeDriver: true,
    }).start(() => {
      skullPulse.stopAnimation();
      skullPulse.setValue(1);
      setMilestone(null);
    });
  };

  const shareMilestone = async () => {
    if (!milestone) return;
    try {
      await Share.share({
        message:
          `I just completed Series ${milestone.series} of THRASH KAN KIDZ! ` +
          `Every base card. Every variant. THRASH TILL DEATH! ` +
          `Get the game and try to beat me: https://thrashkankidz.com`,
      });
    } catch (err) {
      console.error('Share failed:', err);
    }
  };

  const shareCard = async (card: Card) => {
    const variantBit = card.variant_name ? ` (${card.variant_name} Variant)` : '';
    const seriesBit = card.series ? ` from Series ${card.series}` : '';
    try {
      await Share.share({
        message:
          `I just pulled ${card.name}${variantBit}${seriesBit} on THRASH KAN KIDZ! 🤘\n\n` +
          `${card.description}\n\n` +
          `Collect 'em all: https://thrashkankidz.com`,
        url: card.front_image_url,
      });
    } catch (err) {
      console.error('Card share failed:', err);
    }
  };

  const fetchTradeInEligible = async () => {
    if (!user) return;
    try {
      const response = await fetch(`${apiUrl}/api/users/${user.id}/trade-in-eligible`);
      const data = await response.json();
      setTradeInEligible(data.eligible_cards || []);
    } catch (error) {
      console.error('Error fetching trade-in eligible cards:', error);
    }
  };

  const handleTradeIn = async (cardId: string) => {
    if (!user || isTrading) return;
    
    setIsTrading(true);
    try {
      const response = await fetch(`${apiUrl}/api/users/${user.id}/trade-in/${cardId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      const data = await response.json();
      
      if (data.success) {
        setTradeInResult(data);
        // Reset scratch gating: if the won variant ships with a cover URL,
        // require the user to scratch before the AWESOME button appears.
        // Variants without a cover (defensive fallback) auto-resolve.
        const needsScratch = !!(data?.won_variant?.is_variant && data?.won_variant?.scratch_cover_url);
        setTradeScratched(!needsScratch);
        setShowTradeInResult(true);
        refreshData();
        fetchTradeInEligible();
      } else {
        Alert.alert('Trade-In Failed', data.detail || 'Could not complete trade-in');
        // Stale state guard: a "Need 5 duplicates" error means the backend's
        // current quantity is < 5 (likely from a prior trade). Drop this card
        // from the visible list and resync from the backend so the user
        // doesn't keep tapping a stale row.
        setTradeInEligible(prev => prev.filter(item => item.card.id !== cardId));
        refreshData();
        fetchTradeInEligible();
      }
    } catch (error) {
      console.error('Trade-in error:', error);
      Alert.alert('Error', 'Failed to complete trade-in');
    } finally {
      setIsTrading(false);
    }
  };

  if (!user) {
    return (
      <GrungeBackground>
        <SafeAreaView style={styles.container}>
          <View style={styles.centerContainer}>
            <Text style={styles.lockIcon}>🔒</Text>
            <Text style={styles.lockedText}>Please login to view your collection</Text>
          </View>
        </SafeAreaView>
      </GrungeBackground>
    );
  }

  const ownedCardIds = new Set(userCards.map(uc => uc.card.id));
  const ownedCardQuantities: { [key: string]: number } = {};
  userCards.forEach(uc => {
    ownedCardQuantities[uc.card.id] = uc.quantity;
  });

  const toggleSeries = (series: number) => {
    // Unset keys default to collapsed (true), so the first tap on a new series
    // header should expand (false). Using `?? true` keeps toggle symmetric.
    setCollapsedSeries(prev => ({ ...prev, [series]: !(prev[series] ?? true) }));
  };

  // Group cards by series — derived from allCards so adding Series 7+
  // requires only a backend change, no frontend rebuild.
  const seriesNumbers: number[] = Array.from(
    new Set(
      allCards
        .map(c => c.series ?? (c as any).series_reward)
        .filter((s): s is number => typeof s === 'number' && s > 0),
    ),
  ).sort((a, b) => a - b);
  const getSeriesCards = (series: number) => {
    const base = allCards
      .filter(c => c.series === series && !c.base_card_id && c.rarity !== 'rare' && c.rarity !== 'epic')
      .sort((a, b) => {
        if (a.band !== b.band) return (a.band || '').localeCompare(b.band || '');
        return (a.card_type || '').localeCompare(b.card_type || '');
      });
    const variants = allCards
      .filter(c => c.series === series && c.base_card_id)
      .sort((a, b) => {
        const aOwned = ownedCardIds.has(a.id) ? 0 : 1;
        const bOwned = ownedCardIds.has(b.id) ? 0 : 1;
        if (aOwned !== bOwned) return aOwned - bOwned;
        if (a.name !== b.name) return (a.name || '').localeCompare(b.name || '');
        return (a.variant_name || '').localeCompare(b.variant_name || '');
      });
    // Reward cards for this series (series_reward matches, rarity is rare/epic)
    const rewards = allCards
      .filter(c => (c as any).series_reward === series && (c.rarity === 'rare' || c.rarity === 'epic'));
    return [...base, ...rewards, ...variants];
  };

  const getSeriesStats = (series: number) => {
    const baseTotal = allCards.filter(c => c.series === series && c.rarity === 'common' && !c.base_card_id).length;
    const variantTotal = allCards.filter(c => c.series === series && c.base_card_id).length;
    const ownedBase = userCards.filter(uc => uc.card.series === series && uc.card.rarity === 'common' && !uc.card.base_card_id).length;
    const ownedVars = userCards.filter(uc => uc.card.series === series && uc.card.base_card_id).length;
    return { baseTotal, variantTotal, ownedBase, ownedVars };
  };

  // Per-band stats within a series — used by the new progress bars
  const getBandsInSeries = (series: number): string[] => {
    const bands = new Set<string>();
    allCards.forEach(c => {
      if (c.series === series && c.band && c.rarity !== 'rare' && c.rarity !== 'epic') {
        bands.add(c.band);
      }
    });
    return Array.from(bands).sort();
  };

  const getBandStats = (series: number, band: string) => {
    const baseCards = allCards.filter(c => c.series === series && c.band === band && c.rarity === 'common' && !c.base_card_id);
    const variantCards = allCards.filter(c => c.series === series && c.band === band && c.base_card_id);
    const ownedBase = baseCards.filter(c => ownedCardIds.has(c.id)).length;
    const ownedVars = variantCards.filter(c => ownedCardIds.has(c.id)).length;
    const totalCards = baseCards.length + variantCards.length;
    const totalOwned = ownedBase + ownedVars;
    const pct = totalCards > 0 ? Math.round((totalOwned / totalCards) * 100) : 0;
    const isComplete = totalCards > 0 && totalOwned === totalCards;
    return {
      baseTotal: baseCards.length,
      variantTotal: variantCards.length,
      ownedBase,
      ownedVars,
      pct,
      isComplete,
    };
  };

  const specialRewardCards = userCards
    .map(uc => uc.card)
    .filter((card, index, arr) => {
      const c: any = card;
      const isSpecialReward =
        c.is_daily_reward ||
        c.reward_type ||
        c.special_type ||
        c.card_category === 'reward' ||
        (!c.series && !c.series_reward && (c.rarity === 'rare' || c.rarity === 'epic'));

      return isSpecialReward && arr.findIndex(other => other.id === card.id) === index;
    })
    .sort((a, b) => (a.name || '').localeCompare(b.name || ''));

  const totalOwned = userCards.length;

  const cardFlipPlay = cardFlipSound.play;

  const renderCard = (card: Card) => {
    const isOwned = ownedCardIds.has(card.id);
    const quantity = ownedCardQuantities[card.id] || 0;
    const userCard = userCards.find(uc => uc.card.id === card.id);
    return (
      <SimpleCard
        key={card.id}
        card={card}
        isOwned={isOwned}
        quantity={quantity}
        cardFlipPlay={cardFlipPlay}
        onPress={() => {
          if (isOwned && userCard) {
            setSelectedCard(userCard);
            setShowFront(true);
            detailFlipAnim.setValue(0);
          }
        }}
      />
    );
  };

  const [tradeInExpanded, setTradeInExpanded] = useState(false);

  return (
    <GrungeBackground>
      <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <ExpoImage source={headerSource('myCollection')} style={styles.headerImage} contentFit="contain" />
        <Text style={styles.subtitle}>
          {totalOwned} Cards Collected
        </Text>
      </View>

      {tradeInEligible.length > 0 && (
        <TouchableOpacity 
          style={styles.tradeInToggle}
          onPress={() => setTradeInExpanded(!tradeInExpanded)}
          data-testid="trade-in-toggle"
        >
          <View style={styles.tradeInToggleLeft}>
            <Ionicons name="swap-vertical" size={18} color="#FFD700" />
            <Text style={styles.tradeInToggleText}>Trade-In ({tradeInEligible.length} eligible)</Text>
          </View>
          <Ionicons name={tradeInExpanded ? 'chevron-up' : 'chevron-down'} size={20} color="#FFD700" />
        </TouchableOpacity>
      )}

      {tradeInExpanded && tradeInEligible.length > 0 && (
        <View style={styles.tradeInSection}>
          <ScrollView style={styles.tradeInScroll} nestedScrollEnabled showsVerticalScrollIndicator={true}>
            {tradeInEligible.map((item) => (
              <View key={item.card.id} style={styles.tradeInCard}>
                <ExpoImage
                  source={{ uri: cardThumb(item.card, 160) }}
                  style={styles.tradeInImage}
                  contentFit="cover"
                />
                <View style={styles.tradeInInfo}>
                  <Text style={styles.tradeInName}>{item.card.name}</Text>
                  <Text style={styles.tradeInQuantity}>
                    {item.quantity} dupes | {item.variants_owned}/{item.variants_total} variants
                  </Text>
                </View>
                <TouchableOpacity
                  style={[styles.tradeInButton, isTrading && styles.tradeInButtonDisabled]}
                  onPress={() => handleTradeIn(item.card.id)}
                  disabled={isTrading}
                >
                  <Text style={styles.tradeInButtonText}>
                    {isTrading ? '...' : 'TRADE'}
                  </Text>
                </TouchableOpacity>
              </View>
            ))}
          </ScrollView>
        </View>
      )}

      <ScrollView style={styles.flashListContainer} showsVerticalScrollIndicator={false} contentContainerStyle={styles.flashListContent}>
        {specialRewardCards.length > 0 && (
          <View style={styles.seriesSection} data-testid="special-reward-cards-section">
            <View style={styles.seriesSectionHeader}>
              <View style={styles.seriesHeaderLeft}>
                <Text style={styles.seriesHeaderTitle}>Special / Reward Cards</Text>
                <Text style={styles.seriesHeaderStats}>
                  {specialRewardCards.length} collected
                </Text>
              </View>
              <Ionicons name="star" size={22} color="#FFD700" />
            </View>
            <View style={styles.seriesCardGrid}>
              {specialRewardCards.map(card => renderCard(card))}
            </View>
          </View>
        )}

        {seriesNumbers.map(series => {
          const cards = getSeriesCards(series);
          const stats = getSeriesStats(series);
          const isCollapsed = collapsedSeries[series] ?? true;
          const bands = getBandsInSeries(series);
          if (cards.length === 0) return null;
          return (
            <View key={series} style={styles.seriesSection} data-testid={`series-${series}-section`}>
              <TouchableOpacity 
                style={styles.seriesSectionHeader} 
                onPress={() => toggleSeries(series)}
                data-testid={`series-${series}-toggle`}
              >
                <View style={styles.seriesHeaderLeft}>
                  <Text style={styles.seriesHeaderTitle}>Series {series}</Text>
                  <Text style={styles.seriesHeaderStats}>
                    {stats.ownedBase}/{stats.baseTotal} base{stats.ownedVars > 0 ? ` + ${stats.ownedVars} variants` : ''}
                  </Text>
                </View>
                <Ionicons 
                  name={isCollapsed ? 'chevron-down' : 'chevron-up'} 
                  size={22} 
                  color="#FFD700" 
                />
              </TouchableOpacity>
              {!isCollapsed && bands.length > 0 && (
                <View style={styles.bandProgressList} data-testid={`series-${series}-bands`}>
                  {bands.map(band => {
                    const bs = getBandStats(series, band);
                    return (
                      <View
                        key={band}
                        style={styles.bandProgressRow}
                        data-testid={`band-progress-${series}-${band.replace(/\s+/g, '-').toLowerCase()}`}
                      >
                        <View style={styles.bandProgressTopRow}>
                          <Text
                            style={[styles.bandProgressName, bs.isComplete && styles.bandProgressNameComplete]}
                            numberOfLines={1}
                          >
                            {bs.isComplete ? '✓ ' : ''}{band}
                          </Text>
                          <Text style={[styles.bandProgressCounts, bs.isComplete && styles.bandProgressNameComplete]}>
                            {bs.ownedBase}/{bs.baseTotal}
                            {bs.variantTotal > 0 ? ` + ${bs.ownedVars}/${bs.variantTotal} var` : ''}
                          </Text>
                        </View>
                        <View style={styles.bandProgressBarTrack}>
                          <View
                            style={[
                              styles.bandProgressBarFill,
                              { width: `${bs.pct}%` },
                              bs.isComplete && styles.bandProgressBarFillComplete,
                            ]}
                          />
                        </View>
                      </View>
                    );
                  })}
                </View>
              )}
              {!isCollapsed && (
                <View style={styles.seriesCardGrid}>
                  {cards.map(card => renderCard(card))}
                </View>
              )}
            </View>
          );
        })}

        {/* Upcoming series tiles ("Coming Soon" / "Drops on …") rendered
            from the catalog endpoint. We explicitly check the `status` field
            (new in this backend) — if the API hasn't been redeployed yet and
            doesn't return `status`, this is a no-op. That keeps the screen
            looking right against an older backend instead of flagging every
            released series as "Coming Soon" because `released` was `undefined`. */}
        {seriesCatalog
          .filter(s => s.status === 'coming_soon' || s.status === 'scheduled')
          .map(s => (
            <ComingSoonTile key={`upcoming-${s.series}`} entry={s} />
          ))}
      </ScrollView>

      {/* Trade-In Result Modal */}
      <Modal
        visible={showTradeInResult}
        animationType="fade"
        transparent={true}
        onRequestClose={() => setShowTradeInResult(false)}
      >
        <View style={styles.tradeResultOverlay}>
          <View style={styles.tradeResultModal}>
            <MascotStamp
              mood={tradeInResult?.all_variants_complete ? 'series_complete' : 'variant_pull'}
              position="tr"
              size={64}
            />
            <Text style={styles.tradeResultTitle}>🎉 Trade Complete!</Text>
            {tradeInResult && (
              <>
                <Text style={styles.tradeResultText}>
                  You received a {tradeInResult.won_variant?.variant_name} variant!
                </Text>
                {tradeInResult.won_variant?.scratch_cover_url ? (
                  <View style={styles.tradeResultImage}>
                    <ScratchCard
                      key={`trade-scratch-${tradeInResult.won_variant?.id}`}
                      width={200}
                      height={300}
                      imageUri={cardThumb(tradeInResult.won_variant, 540)}
                      coverUri={
                        scratchCoverThumb(tradeInResult.won_variant, 540) ||
                        tradeInResult.won_variant?.scratch_cover_url
                      }
                      brushRadius={28}
                      onComplete={() => setTradeScratched(true)}
                    />
                  </View>
                ) : (
                  <ExpoImage
                    source={{ uri: tradeInResult.won_variant?.front_image_url }}
                    style={styles.tradeResultImage}
                    contentFit="contain"
                  />
                )}
                {!tradeScratched && (
                  <Text style={styles.scratchHint}>Scratch to reveal!</Text>
                )}
                <View style={{ width: 240, marginTop: 4, marginBottom: 8 }}>
                  <OozeProgressBar
                    value={tradeInResult.variants_owned}
                    max={tradeInResult.variants_total}
                    tone="blacklight"
                    label={`${tradeInResult.variants_owned}/${tradeInResult.variants_total} VARIANTS COLLECTED`}
                  />
                </View>
                {tradeInResult.all_variants_complete && (
                  <View style={styles.bonusContainer}>
                    <Text style={styles.bonusText}>ALL VARIANTS COMPLETE! +200 COINS!</Text>
                  </View>
                )}
              </>
            )}
            {tradeScratched && (
              <View style={{ marginTop: 8 }}>
                <MetalButton
                  label={tradeInResult?.all_variants_complete ? 'HORNS UP!' : 'AWESOME!'}
                  onPress={() => setShowTradeInResult(false)}
                  tone={tradeInResult?.all_variants_complete ? 'gold' : 'hellfire'}
                  size="lg"
                  testID="trade-in-result-ok"
                />
              </View>
            )}
          </View>
        </View>
      </Modal>

      {/* Card Detail Modal */}
      <Modal
        visible={selectedCard !== null}
        animationType="fade"
        transparent={true}
        onRequestClose={() => setSelectedCard(null)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <TouchableOpacity
              style={styles.modalCloseButton}
              onPress={() => setSelectedCard(null)}
            >
              <Ionicons name="close" size={24} color="#fff" />
            </TouchableOpacity>

            {selectedCard && (
              <ScrollView contentContainerStyle={styles.modalScrollContent}>
                <TouchableOpacity activeOpacity={0.9} onPress={flipDetailCard} data-testid="detail-flip-card">
                  <View style={styles.modalFlipWrap}>
                    <Animated.View
                      style={[
                        styles.modalFlipFace,
                        {
                          opacity: detailFrontOpacity,
                          transform: [{ rotateY: detailFrontRotate }],
                        },
                      ]}
                    >
                      <ExpoImage
                        source={{ uri: selectedCard.card.front_image_url }}
                        style={styles.modalCardImage}
                        contentFit="contain"
                        cachePolicy="memory-disk"
                        transition={150}
                      />
                    </Animated.View>
                    <Animated.View
                      style={[
                        styles.modalFlipFace,
                        styles.modalFlipFaceBack,
                        {
                          opacity: detailBackOpacity,
                          transform: [{ rotateY: detailBackRotate }],
                        },
                      ]}
                    >
                      <ExpoImage
                        source={{ uri: selectedCard.card.back_image_url || selectedCard.card.front_image_url }}
                        style={styles.modalCardImage}
                        contentFit="contain"
                        cachePolicy="memory-disk"
                        transition={150}
                      />
                    </Animated.View>
                  </View>
                </TouchableOpacity>
                
                <Text style={styles.tapHint}>Tap card to flip {showFront ? '(Front)' : '(Back)'}</Text>

                <View style={styles.modalCardInfo}>
                  <Text style={styles.modalCardName}>{selectedCard.card.name}</Text>
                  {selectedCard.card.variant_name && (
                    <Text style={styles.modalVariantName}>{selectedCard.card.variant_name} Variant</Text>
                  )}
                  <Text style={styles.modalCardRarity}>
                    {selectedCard.card.rarity?.toUpperCase()} • Series {selectedCard.card.series}
                  </Text>
                  <Text style={styles.modalCardDescription}>
                    {selectedCard.card.description}
                  </Text>
                  <Text style={styles.modalQuantity}>
                    Owned: x{selectedCard.quantity}
                  </Text>
                  <TouchableOpacity
                    style={styles.cardShareButton}
                    onPress={() => shareCard(selectedCard.card)}
                    data-testid="card-share-btn"
                  >
                    <Ionicons name="share-social" size={16} color="#0f0f1a" />
                    <Text style={styles.cardShareButtonText}>SHARE THIS CARD</Text>
                  </TouchableOpacity>
                </View>
              </ScrollView>
            )}
          </View>
        </View>
      </Modal>

      {/* Series Completion Milestone — full-screen celebration with share */}
      {milestone && (
        <Animated.View
          style={[styles.milestoneOverlay, { opacity: milestoneOpacity }]}
          pointerEvents="auto"
          data-testid="series-milestone-overlay"
        >
          <Animated.View
            style={[styles.milestoneCard, { transform: [{ scale: milestoneScale }] }]}
          >
            <Animated.View style={{ transform: [{ scale: skullPulse }] }}>
              <Text style={styles.milestoneSkull}>💀</Text>
            </Animated.View>
            <Text style={styles.milestoneFlames}>🔥 🤘 🔥</Text>
            <Text style={styles.milestoneEyebrow}>SERIES COMPLETE!</Text>
            <Text style={styles.milestoneTitle}>SERIES {milestone.series}</Text>
            <Text style={styles.milestoneSubtitle}>100% COLLECTED</Text>
            <View style={styles.milestoneRewardBox}>
              <Text style={styles.milestoneRewardLabel}>BONUS REWARD</Text>
              <Text style={styles.milestoneRewardValue}>+{milestone.medals} MEDALS</Text>
            </View>
            <Text style={styles.milestoneTagline}>
              Every base. Every variant. Every reward. Thrash till death.
            </Text>
            <View style={styles.milestoneActions}>
              <TouchableOpacity
                style={styles.milestoneShareBtn}
                onPress={shareMilestone}
                data-testid="series-milestone-share-btn"
              >
                <Ionicons name="share-social" size={18} color="#0f0f1a" />
                <Text style={styles.milestoneShareTxt}>BRAG TO YOUR CREW</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.milestoneCloseBtn}
                onPress={dismissMilestone}
                data-testid="series-milestone-close-btn"
              >
                <Text style={styles.milestoneCloseTxt}>HORNS UP!</Text>
              </TouchableOpacity>
            </View>
          </Animated.View>
        </Animated.View>
      )}
      </SafeAreaView>
    </GrungeBackground>
  );
}

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
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  lockIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  lockedText: {
    color: '#888',
    fontSize: 16,
    textAlign: 'center',
  },
  header: {
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 12,
  },
  headerImage: {
    width: 200,
    height: 80,
    alignSelf: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFD700',
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 14,
    color: '#aaa',
    textAlign: 'center',
    marginTop: 4,
  },
  seriesProgress: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    marginTop: 8,
    gap: 8,
  },
  seriesProgressText: {
    fontSize: 12,
    color: '#4CAF50',
    fontWeight: 'bold',
  },
  variantProgressText: {
    fontSize: 12,
    color: '#9C27B0',
    fontWeight: 'bold',
  },
  seriesSection: {
    marginBottom: 12,
    borderRadius: 12,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#333',
  },
  seriesSectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: 'rgba(26, 26, 46, 0.95)',
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  seriesHeaderLeft: {
    flex: 1,
  },
  seriesHeaderTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#FFD700',
  },
  seriesHeaderStats: {
    fontSize: 11,
    color: '#4CAF50',
    marginTop: 2,
  },
  seriesCardGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    paddingHorizontal: 4,
    paddingVertical: 4,
  },
  bandProgressList: {
    backgroundColor: 'rgba(0, 0, 0, 0.45)',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 215, 0, 0.18)',
    gap: 8,
  },
  bandProgressRow: {
    paddingVertical: 4,
  },
  bandProgressTopRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  bandProgressName: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
    flex: 1,
    marginRight: 8,
  },
  bandProgressNameComplete: {
    color: '#FFD700',
  },
  bandProgressCounts: {
    color: '#bbb',
    fontSize: 11,
    fontVariant: ['tabular-nums'],
  },
  bandProgressBarTrack: {
    height: 6,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 3,
    overflow: 'hidden',
  },
  bandProgressBarFill: {
    height: '100%',
    backgroundColor: '#4CAF50',
    borderRadius: 3,
  },
  bandProgressBarFillComplete: {
    backgroundColor: '#FFD700',
  },
  flashListContainer: {
    flex: 1,
  },
  flashListContent: {
    paddingHorizontal: 12,
    paddingBottom: 100,
  },
  cardContainer: {
    width: CARD_WIDTH,
    height: CARD_HEIGHT,
    margin: 4,
    borderRadius: 8,
    overflow: 'hidden',
    backgroundColor: '#333',
  },
  variantCardBorder: {
    borderWidth: 2,
    borderColor: '#9C27B0',
  },
  // Wrapper around reward cards so the pulsing halo (rewardGlowHalo) can
  // sit absolutely behind the card without disturbing the grid layout.
  rewardGlowWrap: {
    position: 'relative',
  },
  // The pulsing gold "aura" rendered behind reward cards. Slightly larger
  // than the card via negative inset so the gold ring peeks out on every
  // edge as it pulses. Animated through opacity/scale only (native driver).
  rewardGlowHalo: {
    position: 'absolute',
    top: -6,
    left: -6,
    right: -6,
    bottom: -6,
    borderRadius: 14,
    backgroundColor: '#FFD700',
    // Falls back gracefully on Android — the colored fill is the glow.
    shadowColor: '#FFD700',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 1,
    shadowRadius: 12,
    elevation: 0,
    zIndex: -1,
  },
  rewardCardBorder: {
    borderWidth: 3,
    borderColor: '#FFD700',
    shadowColor: '#FFD700',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.5,
    shadowRadius: 6,
    elevation: 6,
  },
  rewardBadge: {
    position: 'absolute',
    top: 4,
    left: 4,
    backgroundColor: '#FFD700',
    paddingHorizontal: 4,
    paddingVertical: 2,
    borderRadius: 4,
  },
  rewardBadgeText: {
    color: '#000',
    fontSize: 7,
    fontWeight: 'bold',
  },
  cardImage: {
    width: '100%',
    height: '100%',
  },
  quantityBadge: {
    position: 'absolute',
    top: 4,
    right: 4,
    backgroundColor: 'rgba(0,0,0,0.8)',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 10,
  },
  quantityText: {
    color: '#FFD700',
    fontSize: 10,
    fontWeight: 'bold',
  },
  variantBadge: {
    position: 'absolute',
    top: 4,
    left: 4,
    backgroundColor: '#9C27B0',
    paddingHorizontal: 4,
    paddingVertical: 2,
    borderRadius: 4,
  },
  variantBadgeText: {
    color: '#fff',
    fontSize: 8,
    fontWeight: 'bold',
  },
  // Daily Reward badge — small moon icon overlay on cards earned via Daily Challenges.
  // Sits top-right (variant badge is top-left, quantity badge is bottom-right).
  dailyRewardBadge: {
    position: 'absolute',
    top: 4,
    right: 4,
    backgroundColor: 'rgba(58, 26, 74, 0.95)',
    borderWidth: 1,
    borderColor: '#e5b4ff',
    paddingHorizontal: 4,
    paddingVertical: 1,
    borderRadius: 4,
  },
  dailyRewardBadgeText: {
    fontSize: 11,
    lineHeight: 12,
  },
  cardNameBadge: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: 'rgba(0,0,0,0.8)',
    paddingVertical: 4,
    paddingHorizontal: 4,
  },
  cardNameText: {
    color: '#fff',
    fontSize: 9,
    textAlign: 'center',
    fontWeight: '600',
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  emptyStateIcon: {
    fontSize: 64,
    marginBottom: 16,
  },
  emptyStateTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 8,
  },
  emptyStateSubtitle: {
    fontSize: 14,
    color: '#888',
    textAlign: 'center',
  },
  tradeInToggle: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 215, 0, 0.1)',
    marginHorizontal: 12,
    marginBottom: 8,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#FFD700',
  },
  tradeInToggleLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  tradeInToggleText: {
    color: '#FFD700',
    fontSize: 14,
    fontWeight: 'bold',
  },
  tradeInSection: {
    marginHorizontal: 12,
    marginBottom: 8,
    maxHeight: 180,
    backgroundColor: 'rgba(26, 26, 46, 0.95)',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#9C27B0',
  },
  tradeInScroll: {
    padding: 10,
  },
  tradeInCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.3)',
    padding: 8,
    borderRadius: 8,
    marginTop: 8,
  },
  tradeInImage: {
    width: 40,
    height: 60,
    borderRadius: 4,
    backgroundColor: '#333',
  },
  tradeInInfo: {
    flex: 1,
    marginLeft: 12,
  },
  tradeInName: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 14,
  },
  tradeInQuantity: {
    color: '#aaa',
    fontSize: 11,
  },
  tradeInButton: {
    backgroundColor: '#9C27B0',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 6,
  },
  tradeInButtonDisabled: {
    opacity: 0.5,
  },
  tradeInButtonText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 12,
  },
  mysteryCard: {
    opacity: 0.7,
  },
  mysteryOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 8,
  },
  mysteryText: {
    fontSize: 48,
    fontWeight: 'bold',
    color: '#FFD700',
    textShadowColor: '#000',
    textShadowOffset: { width: 2, height: 2 },
    textShadowRadius: 4,
  },
  tradeResultOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.9)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  tradeResultModal: {
    backgroundColor: '#2a2a4a',
    padding: 24,
    borderRadius: 16,
    alignItems: 'center',
    marginHorizontal: 20,
    borderWidth: 2,
    borderColor: '#9C27B0',
  },
  tradeResultTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFD700',
    marginBottom: 12,
  },
  tradeResultText: {
    fontSize: 16,
    color: '#fff',
    textAlign: 'center',
    marginBottom: 16,
  },
  tradeResultImage: {
    width: 200,
    height: 300,
    borderRadius: 8,
    marginBottom: 16,
    backgroundColor: '#333',
  },
  scratchHint: {
    color: '#FFD700',
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 0.5,
    textAlign: 'center',
    marginBottom: 12,
  },
  tradeResultButton: {
    backgroundColor: '#9C27B0',
    paddingHorizontal: 32,
    paddingVertical: 12,
    borderRadius: 8,
  },
  tradeResultButtonText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 16,
  },
  bonusContainer: {
    backgroundColor: 'rgba(255, 215, 0, 0.2)',
    borderWidth: 1,
    borderColor: '#FFD700',
    borderRadius: 10,
    padding: 12,
    marginTop: 10,
  },
  bonusText: {
    color: '#FFD700',
    fontWeight: '800',
    fontSize: 16,
    textAlign: 'center',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.95)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    width: '90%',
    maxHeight: '90%',
    backgroundColor: '#1a1a2e',
    borderRadius: 16,
    padding: 16,
  },
  modalCloseButton: {
    position: 'absolute',
    top: 12,
    right: 12,
    zIndex: 10,
    backgroundColor: 'rgba(255,255,255,0.2)',
    borderRadius: 20,
    padding: 8,
  },
  modalScrollContent: {
    alignItems: 'center',
    paddingTop: 40,
  },
  modalCardImage: {
    width: width * 0.7,
    height: width * 1.05,
    borderRadius: 12,
    backgroundColor: '#333',
  },
  tapHint: {
    color: '#888',
    fontSize: 12,
    marginTop: 8,
    marginBottom: 16,
  },
  modalCardInfo: {
    alignItems: 'center',
    paddingHorizontal: 16,
  },
  modalCardName: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#FFD700',
    textAlign: 'center',
  },
  modalVariantName: {
    fontSize: 14,
    color: '#9C27B0',
    fontWeight: 'bold',
    marginTop: 4,
  },
  modalCardRarity: {
    fontSize: 14,
    color: '#4CAF50',
    marginTop: 4,
  },
  modalCardDescription: {
    fontSize: 14,
    color: '#ccc',
    textAlign: 'center',
    marginTop: 12,
    lineHeight: 20,
  },
  modalQuantity: {
    fontSize: 14,
    color: '#FFD700',
    marginTop: 12,
    fontWeight: 'bold',
  },
  // Series Completion Milestone overlay
  milestoneOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.82)',
    zIndex: 10000,
    paddingHorizontal: 24,
  },
  milestoneCard: {
    backgroundColor: '#150505',
    borderWidth: 3,
    borderColor: '#FFD700',
    paddingHorizontal: 28,
    paddingTop: 24,
    paddingBottom: 22,
    borderRadius: 18,
    alignItems: 'center',
    width: '100%',
    maxWidth: 360,
    shadowColor: '#FFD700',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 1,
    shadowRadius: 28,
    elevation: 14,
  },
  milestoneSkull: {
    fontSize: 64,
    marginBottom: 2,
  },
  milestoneFlames: {
    fontSize: 22,
    marginBottom: 10,
    letterSpacing: 4,
  },
  milestoneEyebrow: {
    color: '#ff3b3b',
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 4,
    marginBottom: 4,
  },
  milestoneTitle: {
    color: '#FFD700',
    fontSize: 38,
    fontWeight: '900',
    letterSpacing: 3,
    marginBottom: 2,
  },
  milestoneSubtitle: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '700',
    letterSpacing: 3,
    marginBottom: 16,
  },
  milestoneRewardBox: {
    borderWidth: 2,
    borderColor: '#FFD700',
    borderStyle: 'dashed',
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 22,
    marginBottom: 14,
    alignItems: 'center',
    backgroundColor: 'rgba(255, 215, 0, 0.06)',
  },
  milestoneRewardLabel: {
    color: '#FFD700',
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 3,
    marginBottom: 2,
  },
  milestoneRewardValue: {
    color: '#fff',
    fontSize: 24,
    fontWeight: '900',
    letterSpacing: 1,
  },
  milestoneTagline: {
    color: '#bbb',
    fontSize: 11,
    fontStyle: 'italic',
    textAlign: 'center',
    marginBottom: 18,
    paddingHorizontal: 6,
  },
  milestoneActions: {
    flexDirection: 'row',
    gap: 10,
    width: '100%',
  },
  milestoneShareBtn: {
    flex: 1,
    flexDirection: 'row',
    backgroundColor: '#FFD700',
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
  },
  milestoneShareTxt: {
    color: '#0f0f1a',
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 1,
  },
  milestoneCloseBtn: {
    flex: 1,
    backgroundColor: 'transparent',
    borderWidth: 2,
    borderColor: '#FFD700',
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  milestoneCloseTxt: {
    color: '#FFD700',
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 1,
  },
  // Share-this-card button inside Card Detail modal
  modalFlipWrap: {
    // RESTORED to v127 dimensions per user report — the v128 explicit
    // `width * 0.7 / height * 1.05` change was meant to fix a layout
    // collapse but broke working renders for users on v127. Reverting
    // until we can repro the original 0×0 case with hard evidence.
    width: '100%',
    aspectRatio: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  modalFlipFace: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backfaceVisibility: 'hidden',
  },
  modalFlipFaceBack: {},
  gridFlipFace: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backfaceVisibility: 'hidden',
  },
  cardShareButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FFD700',
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 10,
    marginTop: 16,
    gap: 8,
    alignSelf: 'stretch',
  },
  cardShareButtonText: {
    color: '#0f0f1a',
    fontSize: 13,
    fontWeight: '900',
    letterSpacing: 1.2,
  },
});




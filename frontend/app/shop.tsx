import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
  Animated,
  Easing,
  Modal,
  Dimensions,
  Alert,
} from 'react-native';
import PackEruption from '../components/PackEruption';
import { Image as ExpoImage } from 'expo-image';
import { headerSource } from '../src/assets/headerCatalog';
import { SafeAreaView } from 'react-native-safe-area-context';
import { GrungeBackground } from '../src/components/GrungeBackground';
import { FONTS } from '../src/theme';
import { cardThumb, scratchCoverThumb } from '../src/utils/cardImage';
import { boostState, boostDaysLeft } from '../src/utils/vipBoost';
import { Ionicons } from '@expo/vector-icons';
import { useApp } from '../src/context/AppContext';
import { useFocusEffect, useRouter } from 'expo-router';
import BuyCoinsModal from '../src/components/BuyCoinsModal';
import PackRevealWrapper from '../src/components/PackRevealWrapper';
import MetalButton from '../src/components/MetalButton';
import MascotStamp from '../src/components/MascotStamp';
import RonchTrashTalk, { maybeShowRonchTrashTalk } from '../src/components/RonchTrashTalk';
import { useSoundPlayer } from '../src/utils/sounds';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as StoreReview from 'expo-store-review';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

const REVIEW_LAST_PROMPT_KEY = 'tkk_last_review_prompt';
const REVIEW_COOLDOWN_MS = 30 * 24 * 60 * 60 * 1000;

async function maybeRequestStoreReview(result: SpinResult | null) {
  if (!result) return;

  const newRareOrEpic = (result.won_cards || []).some((pull: any) => {
    const rarity = String(pull?.card?.rarity || '').toLowerCase();
    return !pull?.is_duplicate && (rarity === 'rare' || rarity === 'epic');
  });

  const completedSeries = Boolean(
    result?.series_completion?.series_completed
  );

  if (!newRareOrEpic && !completedSeries) return;

  try {
    const lastPromptRaw = await AsyncStorage.getItem(REVIEW_LAST_PROMPT_KEY);
    const lastPrompt = lastPromptRaw ? Number(lastPromptRaw) : 0;

    if (
      Number.isFinite(lastPrompt) &&
      Date.now() - lastPrompt < REVIEW_COOLDOWN_MS
    ) {
      return;
    }

    const available = await StoreReview.isAvailableAsync();
    const hasAction = await StoreReview.hasAction();

    if (!available || !hasAction) return;

    await StoreReview.requestReview();

    // Record the request even if Google silently suppresses the dialog
    // because its internal quota has been reached.
    await AsyncStorage.setItem(
      REVIEW_LAST_PROMPT_KEY,
      String(Date.now())
    );
  } catch (error) {
    console.warn('[review] Could not request Play review:', error);
  }
}

interface SpinResult {
  won_card: any;
  won_cards?: { card: any; is_duplicate: boolean }[];
  rarity: string;
  is_duplicate: boolean;
  remaining_coins: number;
  pack_size?: number;
  series_completion?: any;
}

interface SpinPoolData {
  current_series: number;
  series_name: string;
  series_description: string;
  series_cards: any[];
  owned_count: number;
  total_count: number;
  rare_reward: any;
  spin_cost: number;
  unlocked_series?: number[];
  completed_series?: number[];
}
export default function ShopScreen() {
  const { user, apiUrl, refreshData, userCards } = useApp();
  const router = useRouter();
  const [spinning, setSpinning] = useState(false);
  const [spinResult, setSpinResult] = useState<SpinResult | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [packSequenceDone, setPackSequenceDone] = useState(false);
  const [showSeriesComplete, setShowSeriesComplete] = useState(false);
  const [showBuyCoins, setShowBuyCoins] = useState(false);
  const [spinPool, setSpinPool] = useState<SpinPoolData | null>(null);
  const [spinConfig, setSpinConfig] = useState({ spin_cost: 75 });
  const [selectedSeries, setSelectedSeries] = useState<number | null>(null);
  const [packState, setPackState] = useState<
  'idle' | 'shaking' | 'ripped' | 'revealed'
>('idle');
  const [ronchLine, setRonchLine] = useState<string | null>(null);

  const packRef = useRef<View | null>(null);
  const [packOrigin, setPackOrigin] = useState<{
    x: number;
    y: number;
    width: number;
    height: number;
  } | null>(null);

  // Daily wheel & medals (medals/free_packs displayed here are read from
  // AppContext via the daily-wheel endpoint on focus; the wheel modal + Card
  // Picker themselves live on the Home screen now).
  const [wheelStreak, setWheelStreak] = useState(0);
  const [medals, setMedals] = useState(0);
  const [freePacks, setFreePacks] = useState(0);
  const [noDupesPacks, setNoDupesPacks] = useState(0);

  // First-Variant celebration
  // Captured at the moment "OPEN PACK!" is tapped: the set of variant_names the
  // user already owned BEFORE this pack. Compared on each card reveal so the
  // banner fires exactly once per variant_name the user has never pulled before.
  const preOpenVariantsRef = useRef<Set<string>>(new Set());
  const firedCelebrationsRef = useRef<Set<string>>(new Set());
  const [celebrationVariant, setCelebrationVariant] = useState<string | null>(null);
  const celebrationOpacity = useRef(new Animated.Value(0)).current;
  const celebrationScale = useRef(new Animated.Value(0.5)).current;

  const fireCelebration = (variantName: string) => {
    setCelebrationVariant(variantName);
    celebrationOpacity.setValue(0);
    celebrationScale.setValue(0.5);
    Animated.parallel([
      Animated.timing(celebrationOpacity, { toValue: 1, duration: 220, useNativeDriver: true }),
      Animated.spring(celebrationScale, { toValue: 1, friction: 5, tension: 90, useNativeDriver: true }),
    ]).start();
    try { prizeWonSound.play(); } catch (_e) { /* ignore */ }
    setTimeout(() => {
      Animated.timing(celebrationOpacity, { toValue: 0, duration: 280, useNativeDriver: true }).start(() => {
        setCelebrationVariant(null);
      });
    }, 2400);
  };

  const maybeCelebrateForCard = (card: any) => {
    const vname: string | undefined = card?.variant_name;
    if (!vname) return;
    if (preOpenVariantsRef.current.has(vname)) return;
    if (firedCelebrationsRef.current.has(vname)) return;
    firedCelebrationsRef.current.add(vname);
    fireCelebration(vname);
  };

  // Sound effects
  const drumRollSound = useSoundPlayer('drum_roll');
  const bagTearSound = useSoundPlayer('bag_tear');
  const cardFlipSound = useSoundPlayer('card_flip');
  const dupeSound = useSoundPlayer('duplicate');
  const prizeWonSound = useSoundPlayer('prize_won');
  const buttonTapSound = useSoundPlayer('button_tap');
  
  // Animation values
  const shakeAnim = useRef(new Animated.Value(0)).current;
  const packScaleAnim = useRef(new Animated.Value(1)).current;
  const packOpacityAnim = useRef(new Animated.Value(1)).current;
  const rightDealAnim = useRef(new Animated.Value(0)).current;
  const middleDealAnim = useRef(new Animated.Value(0)).current;
  const leftDealAnim = useRef(new Animated.Value(0)).current;
  const cardScaleAnim = useRef(new Animated.Value(0.5)).current;
  const glowAnim = useRef(new Animated.Value(0)).current;
  const packFlashAnim = useRef(new Animated.Value(0)).current;
  const collectAnim = useRef(new Animated.Value(0)).current;

  const BACKGROUND_IMAGE = 'https://customer-assets.emergentagent.com/job_earn-cards/artifacts/zgy2com2_enhanced-1771247671181.jpg';
  const CARD_BACK_IMAGE = 'https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/jlg546ha_file_00000000369c71f580be8b548f7c5be7.png';
  
  // Pack cover images per series
  const PACK_COVERS: { [key: number]: string } = {
    1: Image.resolveAssetSource(require('../assets/images/packs/series1_pack_closed.png')).uri,
    2: Image.resolveAssetSource(require('../assets/images/packs/series2_pack_closed.png')).uri,
    3: Image.resolveAssetSource(require('../assets/images/packs/series3_pack_closed.png')).uri,
    4: Image.resolveAssetSource(require('../assets/images/packs/series4_pack_closed.png')).uri,
    5: Image.resolveAssetSource(require('../assets/images/packs/series5_pack_closed.png')).uri,
    6: Image.resolveAssetSource(require('../assets/images/packs/series6_pack_closed.png')).uri,
    7: Image.resolveAssetSource(require('../assets/images/packs/series7_pack_closed.png')).uri,
    8: Image.resolveAssetSource(require('../assets/images/packs/series8_pack_closed.png')).uri,
9: Image.resolveAssetSource(require('../assets/images/packs/series9_pack_closed.png')).uri,
  };

  const PACK_RIPPED: { [key: number]: string } = {
    1: Image.resolveAssetSource(require('../assets/images/packs/series1_pack_rip3.png')).uri,
    2: Image.resolveAssetSource(require('../assets/images/packs/series2_pack_rip3.png')).uri,
    3: Image.resolveAssetSource(require('../assets/images/packs/series3_pack_rip3.png')).uri,
    4: Image.resolveAssetSource(require('../assets/images/packs/series4_pack_rip3.png')).uri,
    5: Image.resolveAssetSource(require('../assets/images/packs/series5_pack_rip3.png')).uri,
    6: Image.resolveAssetSource(require('../assets/images/packs/series6_pack_rip3.png')).uri,
    7: Image.resolveAssetSource(require('../assets/images/packs/series7_pack_rip3.png')).uri,
    8: Image.resolveAssetSource(require('../assets/images/packs/series8_pack_rip3.png')).uri,
9: Image.resolveAssetSource(require('../assets/images/packs/series9_pack_rip3.png')).uri,
  };

  const packCoverImage = useMemo(() => {
    const series = spinPool?.current_series || 1;
    return PACK_COVERS[series] || PACK_COVERS[1];
  }, [spinPool?.current_series]);

  const packExplosionImage = useMemo(() => {
    const series = spinPool?.current_series || 1;
    return PACK_RIPPED[series] || PACK_RIPPED[1];
  }, [spinPool?.current_series]);


  useEffect(() => {
    fetchSpinData();
    refreshShopBalances();
  }, [user]);

  // Re-fetch balances every time the Shop tab gains focus so prizes won in
  // the Home-screen mini-games (Daily Wheel / Card Picker) reflect here
  // immediately on tab switch.
  useFocusEffect(
    React.useCallback(() => {
      refreshShopBalances();
    }, [user?.id])
  );

  // Pulls the user's current medals / free-pack count so the Shop header can
  // show them. Replaces the old `checkDailyWheel` (which also auto-popped
  // the modal — that responsibility moved to the Home screen). Called once
  // when the screen mounts; AppContext also re-syncs via refreshData()
  // whenever the user returns from a mini-game on Home.
  const refreshShopBalances = async () => {
  if (!user) return;

  try {
    const wheelRes = await fetch(
      `${apiUrl}/api/users/${user.id}/daily-wheel`
    );
    const wheelData = await wheelRes.json();

    const triviaRes = await fetch(
      `${apiUrl}/api/users/${user.id}/trivia/status`
    );
    const triviaData = await triviaRes.json();

    setMedals(wheelData.medals || 0);
    setFreePacks(wheelData.free_packs || 0);
    setWheelStreak(wheelData.wheel_streak || 0);
    setNoDupesPacks(triviaData.no_dupes_packs || 0);
  } catch (err) {
    console.error('Error fetching shop balances:', err);
  }
};

  const handleReroll = async () => {
    if (!spinResult?.won_cards || !user) return;
    try {
      const series = selectedSeries || 1;
      const old_card_ids = spinResult.won_cards.map((c: any) => c.card.id);
      const res = await fetch(`${apiUrl}/api/users/${user.id}/reroll`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ series, old_card_ids }),
      });
      if (!res.ok) {
        const err = await res.json();
        Alert.alert('Error', err.detail || 'Failed to reroll');
        return;
      }
      const data = await res.json();
      setSpinResult({ ...spinResult, won_cards: data.won_cards, won_card: data.won_cards[0]?.card });
      setMedals(data.remaining_medals);
      // Play axe sound for fresh reveal
      try { cardFlipSound.play(); } catch (_e) { /* ignore */ }
      refreshData();
    } catch (err) {
      Alert.alert('Error', 'Failed to reroll');
    }
  };

  const fetchSpinData = async (series?: number) => {
    if (!user) return;
    try {
      const seriesParam = series ? `?series=${series}` : '';
      const [configRes, poolRes] = await Promise.all([
        fetch(`${apiUrl}/api/spin/config`),
        fetch(`${apiUrl}/api/users/${user.id}/spin-pool${seriesParam}`)
      ]);
      const config = await configRes.json();
      const pool = await poolRes.json();
      setSpinConfig(config);
      setSpinPool(pool);
    } catch (error) {
      console.error('Error fetching spin data:', error);
    }
  };

  const handleSeriesChange = (series: number) => {
    setSelectedSeries(series);
    resetAnimations();
    fetchSpinData(series);
  };

  const resetAnimations = () => {
    shakeAnim.setValue(0);
    packScaleAnim.setValue(1);
    packOpacityAnim.setValue(1);
    rightDealAnim.setValue(0);
    middleDealAnim.setValue(0);
    leftDealAnim.setValue(0);
    cardScaleAnim.setValue(0.5);
    glowAnim.setValue(0);
    setPackState('idle');
  };

  const handleOpenPack = async (
  opts?: {
    type?: 'coins' | 'free' | 'no_dupes';
  }
) => {
  if (!user || spinning || !spinPool) return;

  const packType = opts?.type ?? 'coins';

const useFreePack = packType === 'free';
const useNoDupes = packType === 'no_dupes';

  if (!useFreePack && user.coins < spinConfig.spin_cost) {
    setShowBuyCoins(true);
    return;
  }

  if (useFreePack && freePacks <= 0) {
    Alert.alert(
      'No Free Packs',
      "You don't have any free packs to redeem."
    );
    return;
  }
  if (useNoDupes && noDupesPacks <= 0) {Alert.alert(
    'No No-Dupes Packs',
    "You don't have any No-Dupes Packs."
  );
  return;
}

  const measuredOrigin = await new Promise<{
    x: number;
    y: number;
    width: number;
    height: number;
  } | null>((resolve) => {
    if (!packRef.current) {
      resolve(null);
      return;
    }

    packRef.current.measureInWindow((x, y, width, height) => {
      resolve({ x, y, width, height });
    });
  });

  setPackOrigin(measuredOrigin);
  setSpinning(true);
  setSpinResult(null);
  setShowResult(false);
  setPackSequenceDone(false);
  resetAnimations();

  // Start the visible pack motion immediately while the API request runs.
  setPackState('shaking');

  preOpenVariantsRef.current = new Set(
    userCards
      .map((uc: any) => uc?.card?.variant_name)
      .filter(
        (v: any): v is string =>
          typeof v === 'string' && v.length > 0
      )
  );

  firedCelebrationsRef.current = new Set();

  try {
    let response: Response;

    if (useFreePack) {
  response = await fetch(
    `${apiUrl}/api/users/${user.id}/redeem-free-pack`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        series: spinPool.current_series || 1,
      }),
    }
  );
} else if (useNoDupes) {
  response = await fetch(
    `${apiUrl}/api/users/${user.id}/open-no-dupes-pack`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        series: spinPool.current_series || 1,
      }),
    }
  );
} else {
  const seriesParam = spinPool.current_series
    ? `?series=${spinPool.current_series}`
    : '';

  response = await fetch(
    `${apiUrl}/api/users/${user.id}/spin${seriesParam}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    }
  );
}


const responseText = await response.text();

console.log('PACK STATUS:', response.status);
console.log('PACK RESPONSE:', responseText);

let result: any;

try {
  result = JSON.parse(responseText);
} catch {
  throw new Error(
    `Pack endpoint returned ${response.status}: ${responseText.slice(0, 300)}`
  );
}


    if (!result.success) {
      setSpinning(false);
      resetAnimations();
      Alert.alert(
        'Pack Error',
        result.detail || 'Failed to open pack'
      );
      return;
    }

    if (useFreePack) {
      if (typeof result.remaining_free_packs === 'number') {
        setFreePacks(result.remaining_free_packs);
      } else {
        setFreePacks((amount) => Math.max(0, amount - 1));
      }
    }

    try {
      const urls: string[] = (result.won_cards || [])
        .map((pull: any) => pull?.card?.front_image_url)
        .filter(
          (url: any): url is string =>
            typeof url === 'string' && url.length > 0
        );

      if (urls.length > 0) {
        void ExpoImage.prefetch(urls).catch(() => {
          // Let images continue loading without delaying the pack opening.
        });
      }
    } catch (_error) {
      // Images will load normally if prefetch fails.
    }

    setSpinResult(result);
    setPackState('ripped');
  } catch (error: any) {
  console.error('Pack opening error:', error);
    setSpinning(false);
    resetAnimations();

    Alert.alert(
      'Pack Error',
      error?.message || 'Failed to open pack. Please try again.'  );
  }
};

  const closeResult = () => {
    if (spinResult?.series_completion?.series_completed) {
      setShowResult(false);
      setShowSeriesComplete(true);
    } else {
  const resultForReview = spinResult;

  setShowResult(false);

  setTimeout(() => {
    setSpinResult(null);
    resetAnimations();
    void maybeRequestStoreReview(resultForReview);
  }, 250);
}
    // Ronch's chance to shit-talk — fires every Nth pack open. The helper
    // returns null when it's not Ronch's turn so we just no-op then.
    maybeShowRonchTrashTalk()
      .then((line) => {
        if (line) setRonchLine(line);
      })
      .catch(() => { /* swallow — never block close */ });
  };

  const closeSeriesComplete = () => {
    const resultForReview = spinResult;

    setShowSeriesComplete(false);
    setSpinResult(null);
    resetAnimations();

    void maybeRequestStoreReview(resultForReview);
  };

  // Animation interpolations
  const shakeTranslate = shakeAnim.interpolate({
    inputRange: [-1, 0, 1],
    outputRange: [-8, 0, 8],
  });

 


 const leftCardX = leftDealAnim.interpolate({
  inputRange: [0, 1],
  outputRange: [0, -22],
});

const centerCardY = middleDealAnim.interpolate({
  inputRange: [0, 1],
  outputRange: [130, 0],
});

const rightCardX = rightDealAnim.interpolate({
  inputRange: [0, 1],
  outputRange: [0, 22],
});


  const collectScale = collectAnim.interpolate({
    inputRange: [0, 0.65, 1],
    outputRange: [1, 0.85, 0.08],
  });

  const collectY = collectAnim.interpolate({
    inputRange: [0, 0.35, 1],
    outputRange: [0, 40, 560],
  });

  const collectOpacity = collectAnim.interpolate({
    inputRange: [0, 0.75, 1],
    outputRange: [1, 1, 0],
  });
  if (!user) {
    return (
  <GrungeBackground>
    <SafeAreaView style={styles.container}>
      ...
    </SafeAreaView>
  </GrungeBackground>
);
  }

  const progress = spinPool ? (spinPool.owned_count / spinPool.total_count) * 100 : 0;

  return (
    <GrungeBackground>
<SafeAreaView style={styles.container}>

      
<BuyCoinsModal
    visible={showBuyCoins}
    onClose={() => setShowBuyCoins(false)}
  />{/* Buy Coins Modal */}

<RonchTrashTalk
  line={ronchLine}
  onDismiss={() => setRonchLine(null)}
/>

      {/* Result Modal */}
<Modal
  visible={showResult} transparent
  animationType="fade"
  onRequestClose={closeResult}
>
      <View style={styles.resultOverlay}>
          <View style={styles.resultContainer}>
            {/* Ronch corner stamp — mood depends on the rarity of the
                currently-revealed card. Epic / rare pulls get a wide-eyed
                Ronch, dupes get an angry Ronch, anything else is happy. */}
            <MascotStamp
              mood={spinResult?.won_cards?.some((p) => p.is_duplicate) ? 'duplicate' : 'variant_pull'}
              position="tr"
              size={64}
            />
            <Text style={styles.resultTitle}>Pack Opened!</Text>

            {spinResult?.won_cards && (
              <Animated.View
  style={[
    styles.packCardsRow,
    {
      transform: [
        { translateY: collectY },
        { scale: collectScale },
      ],
      opacity: collectOpacity,
    },
  ]}
>
                {spinResult.won_cards.map((pull, idx) => {
  const isLeft = idx === 0;
  const isCenter = idx === 1;
  const isRight = idx === 2;

  const dealAnim = isLeft ? leftDealAnim : isCenter ? middleDealAnim : rightDealAnim;

  const dealX = dealAnim.interpolate({
    inputRange: [0, 1],
    outputRange: isLeft ? [70, 0] : isRight ? [-70, 0] : [0, 0],
  });

  const dealY = dealAnim.interpolate({
    inputRange: [0, 1],
    outputRange: isCenter ? [420, -18] : [420, 0],
  });

  return (
    <Animated.View
      key={`pack-fan-${idx}-${pull.card.id}`}
      style={[
        styles.packCardItem,
        isLeft && styles.packCardLeft,
        isCenter && styles.packCardCenter,
        isRight && styles.packCardRight,
        {
          transform: [
            { translateX: dealX },
            { translateY: dealY },
            { scale: 1 },
            { rotate: isLeft ? '-22deg' : isRight ? '22deg' : '0deg' },
          ],
          opacity: 1,
        },
      ]}
    >
      <View
        style={[
          styles.packCardImageWrap,
          pull.is_duplicate && styles.packCardDupe,
        ]}
      >
        <PackRevealWrapper
          animationKey={`pack-fan-${idx}-${pull.card.id}`}
          rarity="common"
          width={102}
          height={146}
        >
          <ExpoImage
            source={{ uri: pull.card.front_image_url }}
            style={styles.packCardImage}
            contentFit="contain"
            cachePolicy="memory-disk"
            transition={150}
          />
        </PackRevealWrapper>
      </View>

      <View
        style={[
          styles.packCardNameWrap,
          isLeft && styles.packCardNameLeft,
          isCenter && styles.packCardNameCenter,
          isRight && styles.packCardNameRight,
        ]}
      >
        <Text style={styles.packCardName} numberOfLines={2}>
          {pull.card.name}
        </Text>
      </View>

      {pull.is_duplicate && (
        <Text style={styles.packCardDupeLabel}>DUPE</Text>
      )}
    </Animated.View>
  );
})}
              </Animated.View>
            )}

            <View style={styles.finalActionsRow}>
              <MetalButton
                label={spinResult?.series_completion?.series_completed ? 'CONTINUE...' : 'COLLECT ALL'}
                onPress={() => {
                  Animated.timing(collectAnim, {
                    toValue: 1,
                    duration: 520,
                    easing: Easing.in(Easing.back(1.4)),
                    useNativeDriver: true,
                  }).start(() => {
                    collectAnim.setValue(0);
                    closeResult();
                  });
                }}
                tone={spinResult?.series_completion?.series_completed ? 'gold' : 'hellfire'}
                size="md"
              />

              {medals >= 1 && spinResult?.won_cards && (
                <TouchableOpacity
                  style={styles.rerollButton}
                  onPress={handleReroll}
                  data-testid="reroll-btn"
                >
                  <Ionicons name="refresh" size={16} color="#000" />
                  <Text style={styles.rerollText}>REROLL (1 Medal)</Text>
                </TouchableOpacity>
              )}
            </View>
          </View>
        </View>
      </Modal>

      {/* Series Complete Modal */}
      <Modal visible={showSeriesComplete} transparent animationType="fade" onRequestClose={closeSeriesComplete}>
        <View style={styles.resultOverlay}>
          <View style={[styles.resultContainer, styles.seriesCompleteContainer]}>
            <Text style={styles.seriesCompleteTitle}>🏆 SERIES COMPLETE! 🏆</Text>
            <Text style={styles.seriesCompleteName}>
              {spinResult?.series_completion?.series_name}
            </Text>
            
            {spinResult?.series_completion?.rare_reward && (
              <>
                <Text style={styles.rareRewardTitle}>
                  {spinResult.series_completion.rare_reward.rarity === 'epic' ? 'Epic' : 'Rare'} Card Unlocked!
                </Text>
                <Image
                  source={{ uri: spinResult.series_completion.rare_reward.front_image_url }}
                  style={styles.rareRewardImage}
                  resizeMode="contain"
                />
                <Text style={styles.rareRewardName}>
                  {spinResult.series_completion.rare_reward.name}
                </Text>
              </>
            )}
            
            {spinResult?.series_completion?.next_series_unlocked && (
              <Text style={styles.nextSeriesText}>
                Series {spinResult.series_completion.next_series_unlocked} Unlocked!
              </Text>
            )}
            
            <TouchableOpacity style={styles.closeResultButton} onPress={closeSeriesComplete} data-testid="close-series-btn">
              <Text style={styles.closeResultText}>Amazing!</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent}>
        {/* Header */}
        <View style={styles.header}>
          <View>
            <ExpoImage source={headerSource('cardPack')} style={styles.headerImage} contentFit="contain" />
            <Text style={styles.subtitle}>{spinPool?.series_name || 'Loading...'}</Text>
          </View>
          <View style={styles.coinSection}>
            <View style={styles.coinDisplay}>
              <Text style={styles.coinIcon}>coins</Text>
              <Text style={styles.coinText}>{user.coins}</Text>
            </View>
            {medals > 0 && (
              <View style={styles.medalDisplay}>
                <Ionicons name="medal" size={16} color="#FF9800" />
                <Text style={styles.medalText}>{medals}</Text>
              </View>
            )}
            {freePacks > 0 && (
              // Free pack badge. Tappable — confirms then redeems one free pack
              // from the currently-selected series, reusing the normal pack-
              // opening animation so the experience is indistinguishable from
              // a paid pull (just no coin cost).
              <TouchableOpacity
                style={styles.freePackDisplay}
                onPress={() => {
                  if (spinning) return;
                  Alert.alert(
                    'Open Free Pack',
                    `Spend 1 free pack to open a ${spinPool?.series_name || 'pack'}?`,
                    [
                      { text: 'Cancel', style: 'cancel' },
                      {
                        text: 'OPEN',
                        onPress: () => handleOpenPack({ type: 'free' }),                    },
                    ]
                  );
                }}
                testID="free-pack-redeem-btn"
              >
                <Ionicons name="gift" size={16} color="#39ff14" />
                <Text style={styles.freePackText}>{freePacks}</Text>
              </TouchableOpacity>
            )}
            <TouchableOpacity 
              style={styles.buyCoinsButton}
              onPress={() => setShowBuyCoins(true)}
              data-testid="buy-coins-btn"
            >
              <Ionicons name="add-circle" size={16} color="#000" />
              <Text style={styles.buyCoinsText}>Buy</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/*
          Daily-login coin-boost status card.
          – `expiring` (≤7 days left): amber nudge to refresh by buying a pack.
          – `inactive` (no boost / expired): green pitch explaining the perk.
          – `active`   (>7 days left): subtle reassurance + countdown.
          Tapping the prompt opens the Buy Coins modal so the user is one
          tap away from refreshing the boost.
        */}
        {(() => {
          const state = boostState(user.coin_boost_expires_at);
          const days = boostDaysLeft(user.coin_boost_expires_at);
          if (state === 'active') {
            return (
              <View style={styles.boostCardActive} testID="shop-boost-active">
                <Ionicons name="star" size={14} color="#0a1a02" />
                <Text style={styles.boostActiveText}>
                  VIP Boost active · {days} days left · 25 coins/day on login
                </Text>
              </View>
            );
          }
          if (state === 'expiring') {
            return (
              <TouchableOpacity
                style={styles.boostCardExpiring}
                onPress={() => setShowBuyCoins(true)}
                testID="shop-boost-expiring"
              >
                <Ionicons name="alert-circle" size={18} color="#ffd24a" />
                <View style={{ flex: 1 }}>
                  <Text style={styles.boostExpiringTitle}>
                    Boost expires in {days} {days === 1 ? 'day' : 'days'}
                  </Text>
                  <Text style={styles.boostExpiringSub}>
                    Grab any coin pack to refresh another 30 days of 25/day login bonus.
                  </Text>
                </View>
                <Ionicons name="chevron-forward" size={18} color="#ffd24a" />
              </TouchableOpacity>
            );
          }
          // inactive
          return (
            
            <TouchableOpacity
              style={styles.boostCardInactive}
              onPress={() => setShowBuyCoins(true)}
              testID="shop-boost-inactive"
            >
              <Ionicons name="flash" size={18} color="#39ff14" />
              <View style={{ flex: 1 }}>
                <Text style={styles.boostInactiveTitle}>
                  Unlock the VIP Daily Boost
                </Text>
                <Text style={styles.boostInactiveSub}>
                  Buy any coin pack → 25 coins/day on login for 30 days + VIP tag in Mosh Pit.
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={18} color="#39ff14" />
            </TouchableOpacity>
          );
        })()}
        
        {spinPool && spinPool.unlocked_series && spinPool.unlocked_series.length > 1 && (
          <View style={styles.seriesToggles} data-testid="series-toggle">
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.seriesToggleScroll}>
              {spinPool.unlocked_series.sort((a: number, b: number) => a - b).map((s: number) => (
                <TouchableOpacity
                  key={s}
                  style={[
                    styles.seriesCoverBtn,
                    spinPool.current_series === s && styles.seriesCoverBtnActive,
                  ]}
                  onPress={() => handleSeriesChange(s)}
                  data-testid={`series-toggle-${s}`}
                >
                  <ExpoImage
                    source={{ uri: PACK_COVERS[s] || PACK_COVERS[1] }}
                    style={styles.seriesCoverImage}
                    contentFit="cover"
                    cachePolicy="memory-disk"
                    transition={150}
                  />
                  <View style={[
                    styles.seriesCoverLabel,
                    spinPool.current_series === s && styles.seriesCoverLabelActive,
                  ]}>
                    <Text style={[
                      styles.seriesCoverText,
                      spinPool.current_series === s && styles.seriesCoverTextActive,
                    ]}>S{s}</Text>
                    {spinPool.completed_series?.includes(s) && (
                      <Ionicons name="checkmark-circle" size={12} color="#4CAF50" />
                    )}
                  </View>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>
        )}

        {/* Series Progress */}
        {spinPool && (
          <View style={styles.seriesProgress}>
            <View style={styles.progressHeader}>
              <Text style={styles.progressTitle}>{spinPool.series_name}</Text>
              <Text style={styles.progressCount}>{spinPool.owned_count}/{spinPool.total_count}</Text>
            </View>
            <View style={styles.progressBarBg}>
              <View style={[styles.progressBarFill, { width: `${progress}%` }]} />
            </View>
            {spinPool.rare_reward && (
              <View style={styles.rewardPreview}>
                <Text style={styles.rewardLabel}>Complete series to unlock a mystery card!</Text>
                <Text style={styles.rewardName}>???</Text>
              </View>
            )}
          </View>
        )}

        {/* Card Pack Section */}
        <View style={styles.packSection}>
          <View style={styles.packContainer}>
            {/* Card Pack Box - Now using the cover image */}
            {!spinning && !spinResult && packState !== 'revealed' && (
              <Animated.View
                ref={packRef}
                style={[
                styles.cardPack,
                {
                  transform: [
                    { translateX: shakeTranslate },
                    { scale: packScaleAnim },
                  ],
                  opacity: packOpacityAnim,
shadowColor: '#ffffff',
shadowOpacity: 0.9,
shadowRadius: 30,
shadowOffset: { width: 0, height: 0 },
                }
              ]}>
                <View style={styles.packImageWrap}>
  <Image
  source={{ uri: packCoverImage }}
  style={styles.packImage}
  resizeMode="cover"
/>
{packState === 'ripped' && (
  <Image
    source={{ uri: packCoverImage }}
    style={[
      styles.packImage,
      {
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        opacity: 0.35,
        backgroundColor: 'red',
      },
    ]}
    resizeMode="cover"
  />
)}
  
</View>
              </Animated.View>
            )}

          </View>

          {/* Open Pack Button */}
          <TouchableOpacity
            style={[
              styles.openPackButton,
              (spinning || packState !== 'idle') && styles.openPackButtonDisabled,
              user.coins < spinConfig.spin_cost && styles.openPackButtonDisabled
            ]}
            onPress={() => handleOpenPack()}
            disabled={spinning || packState !== 'idle' || user.coins < spinConfig.spin_cost}
            data-testid="open-pack-btn"
          >
            {spinning ? (
              <Text style={styles.openPackButtonText}>Opening...</Text>
            ) : packState !== 'idle' ? (
              <Text style={styles.openPackButtonText}>
                OPENING...
              </Text>
            ) : (
              <>
                <Text style={styles.openPackButtonText}>OPEN PACK!</Text>
                <Text style={styles.packCostText}>{spinConfig.spin_cost} 💰</Text>
              </>
            )}
          </TouchableOpacity>
          <TouchableOpacity
  style={[
    styles.openPackButton,
    {
      marginTop: 12,
      backgroundColor: '#1f7a1f',
    },
    (spinning || packState !== 'idle') && styles.openPackButtonDisabled,
  ]}
  onPress={() => handleOpenPack({ type: 'no_dupes' })}
  disabled={spinning || packState !== 'idle'}
>
  <Text style={styles.openPackButtonText}>
    OPEN NO-DUPES PACK
  </Text>
</TouchableOpacity>

          {user.coins < spinConfig.spin_cost && packState === 'idle' && (
            <Text style={styles.notEnoughCoins}>
              Not enough coins! Tap "Buy" to get more.
            </Text>
          )}
        </View>

        {/* Cards Grid - Show all series cards */}
        {spinPool && (
          <View style={styles.cardsSection}>
            <Text style={styles.cardsSectionTitle}>
              {spinPool.series_name} Cards ({spinPool.owned_count}/{spinPool.total_count})
            </Text>
            <View style={styles.cardsGrid}>
              {spinPool.series_cards.map((card, idx) => (
                <View 
                  key={`${card.id}-${idx}`} 
                  style={[
                    styles.cardItem,
                    card.owned && styles.cardItemOwned
                  ]}
                >
                  <Image
                    source={{ uri: cardThumb(card, 160) }}
                    style={[
                      styles.cardImage,
                      !card.owned && styles.cardImageLocked
                    ]}
                    resizeMode="cover"
                    blurRadius={card.owned ? 0 : 10}
                  />
                  {!card.owned && (
                    <View style={styles.cardLockOverlay}>
                      <Ionicons name="help" size={24} color="#FFD700" />
                    </View>
                  )}
                  <Text style={styles.cardName} numberOfLines={1}>{card.name}</Text>
                  <Text style={styles.cardBand}>{card.band}-{card.card_type}</Text>
                </View>
              ))}
            </View>
          </View>
        )}
      </ScrollView>

      {/* First-Variant Celebration Overlay — fires once per variant_name the user
          had never owned before opening this pack. Auto-dismisses after ~2.4s. */}
      {celebrationVariant && (
        <Animated.View
          pointerEvents="none"
          style={[styles.celebrationOverlay, { opacity: celebrationOpacity }]}
          data-testid="first-variant-celebration"
        >
          <Animated.View
            style={[
              styles.celebrationCard,
              { transform: [{ scale: celebrationScale }] },
            ]}
          >
            <Text style={styles.celebrationFire}>🔥</Text>
            <Text style={styles.celebrationLabel}>FIRST VARIANT!</Text>
            <Text style={styles.celebrationVariantName}>{celebrationVariant.toUpperCase()}</Text>
            <Text style={styles.celebrationTagline}>added to your collection</Text>
          </Animated.View>
        </Animated.View>
      )}
      </SafeAreaView>
    
    <PackEruption
      visible={spinning}
      packImage={packCoverImage}
      packExplosionImage={packExplosionImage}
      origin={packOrigin}
      {...({ cards: spinResult?.won_cards || [] } as any)}
      onAnimationComplete={() => {
        setPackState('revealed');
        setSpinning(false);

        leftDealAnim.setValue(1);
        middleDealAnim.setValue(1);
        rightDealAnim.setValue(1);

        setTimeout(() => {
          setShowResult(true);
        }, 100);
      }}
    />
  </GrungeBackground>
  );
}

const styles = StyleSheet.create({packImageWrap: {
  width: '100%',
  height: '100%',
  position: 'relative',
  overflow: 'hidden',
  borderRadius: 16,
},

rippedPackOverlay: {
  position: 'absolute',
  top: 0,
  left: 0,
  right: 0,
  height: 52,
  backgroundColor: 'rgba(0,0,0,0.72)',
  borderBottomWidth: 3,
  borderBottomColor: '#9aff5a',
  justifyContent: 'center',
  alignItems: 'center',
},

ripShadow: {
  position: 'absolute',
  bottom: -10,
  left: 20,
  right: 20,
  height: 18,
  backgroundColor: 'rgba(154,255,90,0.25)',
  borderRadius: 999,
},

ripText: {
  color: '#9aff5a',
  fontWeight: '900',
  fontSize: 13,
  letterSpacing: 1.5,
},
ripMouth: {
  flexDirection: 'row',
  alignItems: 'flex-start',
  justifyContent: 'center',
  gap: 10,
},

ripTooth: {
  width: 18,
  height: 16,
  backgroundColor: '#0b0b0b',
  borderBottomLeftRadius: 8,
  borderBottomRightRadius: 8,
},
  container: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  finalActionsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  sharePullBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1.5,
    borderColor: '#39ff14',
    backgroundColor: 'rgba(57, 255, 20, 0.1)',
  },
  sharePullText: {
    color: '#39ff14',
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 1,
  },
  // First-Variant celebration overlay
  celebrationOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.55)',
    zIndex: 9999,
  },
  celebrationCard: {
    backgroundColor: '#1a0a0a',
    borderWidth: 3,
    borderColor: '#FFD700',
    paddingHorizontal: 36,
    paddingVertical: 28,
    borderRadius: 16,
    alignItems: 'center',
    shadowColor: '#FFD700',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.9,
    shadowRadius: 24,
  },
  celebrationFire: {
    fontSize: 48,
    marginBottom: 4,
  },
  celebrationLabel: {
    color: '#FFD700',
    fontSize: 14,
    fontWeight: '700',
    letterSpacing: 2,
    marginBottom: 4,
  },
  celebrationVariantName: {
    color: '#fff',
    fontSize: 32,
    fontWeight: '900',
    letterSpacing: 1,
    marginBottom: 4,
    textAlign: 'center',
  },
  celebrationTagline: {
    color: '#bbb',
    fontSize: 12,
    fontStyle: 'italic',
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
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
  },
  loginPrompt: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loginText: {
    color: '#888',
    fontSize: 18,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 100,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
    flexWrap: 'wrap',
    rowGap: 8,
  },
  headerImage: {
    width: 140,
    height: 60,
    alignSelf: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFD700',
  },
  subtitle: {
    fontSize: 14,
    color: '#888',
    marginTop: 2,
  },
  coinSection: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    flexShrink: 1,
    flexWrap: 'wrap',
    justifyContent: 'flex-end',
  },
  coinDisplay: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(26, 26, 46, 0.9)',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 16,
  },
  coinIcon: {
    fontSize: 16,
    marginRight: 4,
  },
  coinText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#FFD700',
  },
  medalDisplay: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(26, 26, 46, 0.9)',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 16,
    gap: 4,
  },
  medalText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#FF9800',
  },
  freePackDisplay: {
    // Tappable "free packs in your inventory" pill. Toxic-green to signal
    // it's a redeem affordance (not just a passive counter).
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(26, 26, 46, 0.9)',
    borderWidth: 1,
    borderColor: '#39ff14',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 16,
    gap: 4,
  },
  freePackText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#39ff14',
  },

  // ---------- VIP Daily Boost status cards (shop) ----------
  // Three visual variants live under one mental model so the user
  // always sees their current boost state at a glance.
  boostCardActive: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    alignSelf: 'flex-start',
    backgroundColor: '#ffd24a',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
    marginTop: 4,
    marginBottom: 12,
  },
  boostActiveText: {
    color: '#0a1a02',
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 0.5,
  },
  boostCardExpiring: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: 'rgba(40, 28, 4, 0.92)',
    borderWidth: 1.5,
    borderColor: '#ffd24a',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginTop: 4,
    marginBottom: 12,
  },
  boostExpiringTitle: {
    color: '#ffd24a',
    fontSize: 13,
    fontWeight: '900',
    letterSpacing: 1,
  },
  boostExpiringSub: {
    color: '#fff5d4',
    fontSize: 11,
    marginTop: 2,
  },
  boostCardInactive: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: 'rgba(8, 22, 4, 0.92)',
    borderWidth: 1.5,
    borderColor: '#39ff14',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginTop: 4,
    marginBottom: 12,
  },
  boostInactiveTitle: {
    color: '#39ff14',
    fontSize: 13,
    fontWeight: '900',
    letterSpacing: 1,
  },
  boostInactiveSub: {
    color: '#d4ffcc',
    fontSize: 11,
    marginTop: 2,
  },

  buyCoinsButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFD700',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 16,
    gap: 2,
  },
  buyCoinsText: {
    color: '#000',
    fontSize: 12,
    fontWeight: 'bold',
  },
  // Series Progress
  seriesToggles: {
    marginHorizontal: 16,
    marginBottom: 8,
  },
  seriesToggleScroll: {
    flexDirection: 'row',
    gap: 8,
    paddingVertical: 4,
  },
  seriesCoverBtn: {
    marginRight: 10,
    borderRadius: 12,
    overflow: 'hidden',
    borderWidth: 2,
    borderColor: 'rgba(255,255,255,0.15)',
    width: 70,
  },
  seriesCoverBtnActive: {
    borderColor: '#FFD700',
    borderWidth: 3,
  },
  seriesCoverImage: {
    width: '100%',
    height: 90,
  },
  seriesCoverLabel: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(0,0,0,0.7)',
    paddingVertical: 4,
    gap: 4,
  },
  seriesCoverLabelActive: {
    backgroundColor: 'rgba(255, 215, 0, 0.2)',
  },
  seriesCoverText: {
    color: 'rgba(255,255,255,0.6)',
    fontSize: 12,
    fontWeight: '700',
  },
  seriesCoverTextActive: {
    color: '#FFD700',
  },
  seriesProgress: {
    backgroundColor: 'rgba(26, 26, 46, 0.9)',
    borderRadius: 16,
    padding: 16,
    marginBottom: 20,
    borderWidth: 2,
    borderColor: '#FFD700',
  },
  progressHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  progressTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FFD700',
  },
  progressCount: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
  },
  progressBarBg: {
    height: 12,
    backgroundColor: '#333',
    borderRadius: 6,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: '#FFD700',
    borderRadius: 6,
  },
  rewardPreview: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#333',
  },
  rewardLabel: {
    color: '#888',
    fontSize: 12,
    marginRight: 8,
  },
  rewardThumb: {
    width: 40,
    height: 50,
    borderRadius: 4,
    marginRight: 8,
  },
  rewardName: {
    color: '#2196F3',
    fontSize: 14,
    fontWeight: 'bold',
    flex: 1,
  },
  // Pack Section
  packSection: {
    alignItems: 'center',
    marginBottom: 24,
  },
  packContainer: {
    width: 200,
    height: 280,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  cardPack: {
    width: 180,
    height: 240,
    borderRadius: 12,
    overflow: 'hidden',
    borderWidth: 3,
    borderColor: '#FFD700',
    shadowColor: '#FFD700',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  packImage: {
    width: '100%',
    height: '100%',
  },
  packBox: {
    flex: 1,
    backgroundColor: '#1a1a2e',
    borderRadius: 12,
    borderWidth: 3,
    borderColor: '#FFD700',
    overflow: 'hidden',
  },
  packTop: {
    backgroundColor: '#FFD700',
    paddingVertical: 8,
    alignItems: 'center',
  },
  packLabel: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#000',
    letterSpacing: 2,
  },
  packLabelSub: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#333',
    letterSpacing: 1,
  },
  packMiddle: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 12,
  },
  packSeriesText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#FFD700',
    marginBottom: 12,
    textAlign: 'center',
  },
  packDecoration: {
    flexDirection: 'row',
    gap: 8,
  },
  packDecoEmoji: {
    fontSize: 28,
  },
  packBottom: {
    backgroundColor: 'rgba(255, 215, 0, 0.2)',
    paddingVertical: 8,
    alignItems: 'center',
  },
  packBottomText: {
    fontSize: 11,
    color: '#FFD700',
    fontWeight: '600',
  },
  tapPrompt: {
    position: 'absolute',
    bottom: -10,
    backgroundColor: '#FFD700',
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 20,
  },
  tapPromptText: {
    color: '#000',
    fontWeight: 'bold',
    fontSize: 12,
  },
  openPackButton: {
    backgroundColor: '#FFD700',
    paddingHorizontal: 40,
    paddingVertical: 14,
    borderRadius: 25,
    alignItems: 'center',
    minWidth: 180,
  },
  openPackButtonDisabled: {
    backgroundColor: '#555',
  },
  openPackButtonText: {
    color: '#000',
    fontSize: 20,
    fontWeight: 'bold',
  },
  packCostText: {
    color: '#333',
    fontSize: 12,
    marginTop: 2,
  },
  notEnoughCoins: {
    color: '#ff6b6b',
    fontSize: 13,
    marginTop: 10,
    textAlign: 'center',
  },
  cardPickerEntry: {
    marginTop: 16,
    flexDirection: 'column',
    alignItems: 'center',
    backgroundColor: 'rgba(255,215,0,0.1)',
    borderWidth: 1.5,
    borderColor: '#FFD700',
    borderRadius: 14,
    paddingVertical: 12,
    paddingHorizontal: 20,
    gap: 2,
  },
  cardPickerEntryText: {
    color: '#FFD700',
    fontSize: 16,
    fontWeight: 'bold',
    marginTop: 4,
  },
  cardPickerEntrySub: {
    color: '#aaa',
    fontSize: 11,
  },
  // Cards Section
  cardsSection: {
    marginTop: 8,
  },
  cardsSectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 12,
  },
  cardsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  cardItem: {
    width: '23%',
    marginBottom: 12,
    alignItems: 'center',
  },
  cardItemOwned: {
    opacity: 1,
  },
  cardImage: {
    width: '100%',
    aspectRatio: 0.7,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: '#333',
  },
  cardImageLocked: {
    borderColor: '#222',
  },
  cardLockOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 24,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.5)',
    borderRadius: 6,
  },
  cardName: {
    color: '#fff',
    fontSize: 9,
    marginTop: 4,
    textAlign: 'center',
  },
  cardBand: {
    color: '#888',
    fontSize: 8,
  },
  // Result Modal
  resultOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.9)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  packFlashOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#ffffff',
    zIndex: 999,
  },
  resultContainer: {
    backgroundColor: '#1a1a2e',
    borderRadius: 20,
    padding: 24,
    alignItems: 'center',
    width: '100%',
    maxWidth: 300,
    borderWidth: 3,
    borderColor: '#4CAF50',
  },
  resultTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#FFD700',
    marginBottom: 16,
  },
  resultCardContainer: {
    marginBottom: 12,
    alignItems: 'center',
  },
  resultCardImage: {
    width: 180,
    height: 260,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: '#FFD700',
    backgroundColor: '#333',
  },
  packCardsRow: {
  width: '100%',
  height: 220,
  marginTop: 8,
  marginBottom: 18,
  position: 'relative',
},
  packCardItem: {
  position: 'absolute',
  alignItems: 'center',
  width: 118,
},
  packCardLeft: {
  left: '50%',
  marginLeft: -128,
  top: 30,
  zIndex: 1,
},
  packCardCenter: {
  left: '50%',
  marginLeft: -59,
  top: 8,
  zIndex: 3,
},
  packCardRight: {
  left: '50%',
  marginLeft: 10,
  top: 30,
  zIndex: 2,
},
  packCardImageWrap: {
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#FFD700',
    overflow: 'hidden',
    backgroundColor: '#333',
  },
  packCardSolo: {
    borderWidth: 3,
    borderRadius: 12,
    marginVertical: 24,
  },
  packCardDupe: {
    borderColor: '#888',
  },
  packCardImage: {
    width: 102,
    height: 146,
  },
  scratchHint: {
    color: '#FFD700',
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.5,
    textAlign: 'center',
    marginTop: 4,
  },
  packCardNameWrap: {
    marginTop: 8,
    width: 118,
    minHeight: 34,
    paddingHorizontal: 5,
    paddingVertical: 4,
    borderRadius: 6,
    backgroundColor: 'rgba(0,0,0,0.88)',
    borderWidth: 1,
    borderColor: 'rgba(154,255,90,0.45)',
    justifyContent: 'center',
  },
  packCardNameLeft: {
    transform: [{ rotate: '22deg' }],
  },
  packCardNameCenter: {
    transform: [{ rotate: '0deg' }],
  },
  packCardNameRight: {
    transform: [{ rotate: '-22deg' }],
  },

  packCardName: {
  color: '#9aff5a',
  fontSize: 11,
  lineHeight: 13,
  fontFamily: FONTS.death,
  fontWeight: '900',
  letterSpacing: 0.1,
  textAlign: 'center',
  width: '100%',
  alignSelf: 'center',
  textShadowColor: 'rgba(57,255,20,0.5)',
  textShadowOffset: { width: 0, height: 0 },
  textShadowRadius: 6,
},
  packCardDupeLabel: {
    color: '#FF9800',
    fontSize: 9,
    fontWeight: 'bold',
    marginTop: 2,
  },
  resultCardName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 4,
  },
  resultBand: {
    fontSize: 12,
    color: '#888',
    marginBottom: 12,
  },
  duplicateBadge: {
    backgroundColor: 'rgba(255, 152, 0, 0.2)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 10,
    marginBottom: 12,
  },
  duplicateText: {
    color: '#FF9800',
    fontSize: 11,
    textAlign: 'center',
  },
  closeResultButton: {
    backgroundColor: '#FFD700',
    paddingHorizontal: 28,
    paddingVertical: 10,
    borderRadius: 20,
  },
  closeResultText: {
    color: '#000',
    fontSize: 15,
    fontWeight: 'bold',
  },
  rerollButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FF9800',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 12,
    marginTop: 8,
    gap: 6,
  },
  rerollText: {
    color: '#000',
    fontSize: 13,
    fontWeight: 'bold',
  },
  // Series Complete Modal
  seriesCompleteContainer: {
    borderColor: '#FFD700',
    backgroundColor: '#1a2a1a',
  },
  seriesCompleteTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFD700',
    marginBottom: 8,
    textAlign: 'center',
  },
  seriesCompleteName: {
    fontSize: 16,
    color: '#888',
    marginBottom: 16,
  },
  rareRewardTitle: {
    fontSize: 16,
    color: '#2196F3',
    fontWeight: 'bold',
    marginBottom: 8,
  },
  rareRewardImage: {
    width: 120,
    height: 160,
    borderRadius: 10,
    borderWidth: 3,
    borderColor: '#2196F3',
    marginBottom: 8,
  },
  rareRewardName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#2196F3',
    marginBottom: 12,
  },
  nextSeriesText: {
    fontSize: 14,
    color: '#4CAF50',
    marginBottom: 12,
  },
});

















































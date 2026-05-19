/**
 * HeroCarousel — auto-rotating promo slides at the top of Home.
 *
 * Slides are defined inline (easy to swap content / add new). Each slide
 * has a title, subtitle, accent color, optional background image, and an
 * onPress destination. Auto-advances every 4s; user can tap a slide for
 * its CTA or swipe (paged ScrollView).
 */
import React, { useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Image,
  TouchableOpacity,
  Dimensions,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';

const SCREEN_W = Dimensions.get('window').width;
const SLIDE_W = SCREEN_W - 32; // 16px horizontal padding on each side

interface Slide {
  id: string;
  title: string;
  subtitle: string;
  cta: string;
  href: string;
  accentColor: string;
  bgImage?: string;
  icon: keyof typeof Ionicons.glyphMap;
}

const SLIDES: Slide[] = [
  {
    id: 's7',
    title: 'GRIND OR DIE',
    subtitle: 'Series 7 packs out now',
    cta: 'RIP PACKS',
    href: '/shop',
    accentColor: '#39ff14',
    icon: 'flame',
  },
  {
    id: 'missions',
    title: 'THRASH MISSIONS',
    subtitle: 'Complete goals, earn coins',
    cta: 'VIEW MISSIONS',
    href: '/goals',
    accentColor: '#ffd24a',
    icon: 'flash',
  },
  {
    id: 'trade',
    title: 'TRADE WITH HOMIES',
    subtitle: 'Swap dupes for missing cards',
    cta: 'GO TO TRADE',
    href: '/trade',
    accentColor: '#ff7a3a',
    icon: 'swap-horizontal',
  },
];

const AUTOPLAY_MS = 4500;

export const HeroCarousel: React.FC = () => {
  const router = useRouter();
  const scrollRef = useRef<ScrollView>(null);
  const [index, setIndex] = useState(0);
  const indexRef = useRef(0);
  const userTouching = useRef(false);

  // Autoplay — advance every 4.5s. Reset to 0 after the last slide.
  useEffect(() => {
    const tick = setInterval(() => {
      if (userTouching.current) return;
      const next = (indexRef.current + 1) % SLIDES.length;
      indexRef.current = next;
      setIndex(next);
      scrollRef.current?.scrollTo({ x: next * SLIDE_W, animated: true });
    }, AUTOPLAY_MS);
    return () => clearInterval(tick);
  }, []);

  const onScroll = (e: any) => {
    const x = e.nativeEvent.contentOffset.x;
    const i = Math.round(x / SLIDE_W);
    if (i !== indexRef.current) {
      indexRef.current = i;
      setIndex(i);
    }
  };

  return (
    <View style={styles.wrap} testID="hero-carousel">
      <ScrollView
        ref={scrollRef}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onMomentumScrollEnd={onScroll}
        onTouchStart={() => { userTouching.current = true; }}
        onTouchEnd={() => { userTouching.current = false; }}
      >
        {SLIDES.map((s) => (
          <TouchableOpacity
            key={s.id}
            style={[styles.slide, { width: SLIDE_W, borderColor: s.accentColor }]}
            activeOpacity={0.85}
            onPress={() => router.push(s.href as any)}
            testID={`hero-slide-${s.id}`}
          >
            <LinearGradient
              colors={[`${s.accentColor}33`, '#0a0d0a']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
              style={styles.slideGradient}
            />
            {s.bgImage && (
              <Image source={{ uri: s.bgImage }} style={styles.slideBg} resizeMode="cover" />
            )}
            <View style={styles.slideContent}>
              <View style={styles.slideIconWrap}>
                <Ionicons name={s.icon} size={32} color={s.accentColor} />
              </View>
              <View style={styles.slideTextBlock}>
                <Text style={[styles.slideTitle, { color: s.accentColor }]}>{s.title}</Text>
                <Text style={styles.slideSubtitle}>{s.subtitle}</Text>
                <View style={[styles.slideCta, { borderColor: s.accentColor }]}>
                  <Text style={[styles.slideCtaText, { color: s.accentColor }]}>{s.cta}</Text>
                  <Ionicons name="chevron-forward" size={14} color={s.accentColor} />
                </View>
              </View>
            </View>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Dot indicators */}
      <View style={styles.dots}>
        {SLIDES.map((_, i) => (
          <View
            key={i}
            style={[styles.dot, i === index && styles.dotActive]}
          />
        ))}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: { marginBottom: 16 },
  slide: {
    height: 110,
    borderRadius: 12,
    borderWidth: 2,
    overflow: 'hidden',
    backgroundColor: '#0a0d0a',
    marginRight: 0,
  },
  slideGradient: { ...StyleSheet.absoluteFillObject },
  slideBg: { ...StyleSheet.absoluteFillObject, opacity: 0.3 },
  slideContent: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  slideIconWrap: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: 'rgba(0,0,0,0.55)',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 14,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.15)',
  },
  slideTextBlock: { flex: 1 },
  slideTitle: {
    fontSize: 18,
    fontWeight: '900',
    letterSpacing: 2,
    textShadowColor: 'rgba(0,0,0,0.8)',
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 2,
  },
  slideSubtitle: {
    color: '#cde',
    fontSize: 12,
    marginTop: 2,
    marginBottom: 6,
  },
  slideCta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
  },
  slideCtaText: { fontSize: 11, fontWeight: '900', letterSpacing: 1 },
  dots: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 6,
    marginTop: 8,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#333',
  },
  dotActive: {
    backgroundColor: '#39ff14',
    width: 16,
  },
});

export default HeroCarousel;

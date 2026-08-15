/**
 * HeroCarousel ? swipeable navigation menu on Home.
 *
 * Each PNG contains its own title, subtitle, CTA and artwork.
 * React only supplies navigation, paging and active dots.
 */

import React, { useEffect, useRef, useState } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  Image,
  TouchableOpacity,
  Dimensions,
} from 'react-native';
import { useRouter } from 'expo-router';
import { HERO_ART } from '../assets/icons';

const SCREEN_W = Dimensions.get('window').width;
const SLIDE_W = SCREEN_W - 32;

interface Slide {
  id: string;
  href: string;
  image: any;
  accentColor: string;
}

const SLIDES: Slide[] = [
  {
    id: 'series9',
    href: '/shop',
    image: HERO_ART.series9,
    accentColor: '#39ff14',
  },
  {
    id: 'missions',
    href: '/goals',
    image: HERO_ART.missions,
    accentColor: '#ffd24a',
  },
  {
    id: 'trade',
    href: '/trade',
    image: HERO_ART.trade,
    accentColor: '#ff7a3a',
  },
  {
    id: 'daily',
    href: '/daily-challenges',
    image: HERO_ART.daily,
    accentColor: '#b74cff',
  },
  {
    id: 'trivia',
    href: '/trivia',
    image: HERO_ART.trivia,
    accentColor: '#39ff14',
  },
  {
    id: 'leaderboard',
    href: '/leaderboard',
    image: HERO_ART.leaderboard,
    accentColor: '#ffd24a',
  },
  {
    id: 'referral',
    href: '/referral',
    image: HERO_ART.referral,
    accentColor: '#39ff14',
  },
  {
    id: 'minigames',
    href: '/mini-games',
    image: HERO_ART.minigames,
    accentColor: '#39ff14',
  },
];

const AUTOPLAY_MS = 4500;

export const HeroCarousel: React.FC = () => {
  const router = useRouter();
  const scrollRef = useRef<ScrollView>(null);
  const [index, setIndex] = useState(0);
  const indexRef = useRef(0);
  const userTouching = useRef(false);

  useEffect(() => {
    const tick = setInterval(() => {
      if (userTouching.current) return;

      const next = (indexRef.current + 1) % SLIDES.length;

      indexRef.current = next;
      setIndex(next);

      scrollRef.current?.scrollTo({
        x: next * SLIDE_W,
        animated: true,
      });
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
        onTouchStart={() => {
          userTouching.current = true;
        }}
        onTouchEnd={() => {
          userTouching.current = false;
        }}
      >
        {SLIDES.map((slide) => (
          <TouchableOpacity
            key={slide.id}
            style={[
              styles.slide,
              {
                width: SLIDE_W,
                borderColor: slide.accentColor,
              },
            ]}
            activeOpacity={0.9}
            onPress={() => router.push(slide.href as any)}
            testID={`hero-slide-${slide.id}`}
          >
            <Image
              source={slide.image}
              style={styles.slideImage}
              resizeMode="contain"
            />
          </TouchableOpacity>
        ))}
      </ScrollView>

      <View style={styles.dots}>
        {SLIDES.map((slide, i) => (
          <View
            key={slide.id}
            style={[
              styles.dot,
              i === index && styles.dotActive,
              i === index && {
                backgroundColor: slide.accentColor,
              },
            ]}
          />
        ))}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  wrap: {
    marginBottom: 16,
  },

  slide: {
    height: 150,
    borderRadius: 12,
    borderWidth: 2,
    overflow: 'hidden',
    backgroundColor: '#050505',
  },

  slideImage: {
    width: '100%',
    height: '100%',
    backgroundColor: '#050505',
  },

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
    width: 16,
  },
});

export default HeroCarousel;

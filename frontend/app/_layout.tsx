import React, { useEffect, useRef } from 'react';
import { Tabs } from 'expo-router';
import { AppProvider, useApp } from '../src/context/AppContext';
import { View, StyleSheet, Text, Platform, Animated, Easing, Image, ImageSourcePropType } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useFonts } from 'expo-font';
import { Image as ExpoImage } from 'expo-image';
import { ErrorBoundary } from '../src/components/ErrorBoundary';
import { UpdateBanner } from '../src/components/UpdateBanner';
import { ICONS } from '../src/assets/icons';

/**
 * Bottom nav — rusted-metal aesthetic with slime drip on the active tab.
 *
 * Each tab renders a `<MetalTab>` that shows:
 *   - A Nano Banana custom icon themed for the death-metal aesthetic
 *   - A glowing "slime drip" anchor (animated vertical drip + halo) on the
 *     active tab only.
 *
 * The tab bar background is a rusted dark gradient (solid colors + 1px top
 * border in oxidized green).
 */
const TAB_ICONS: Record<string, ImageSourcePropType> = {
  index: ICONS.navHome,
  collection: ICONS.navCollection,
  shop: ICONS.navShop,
  goals: ICONS.navGoals,
  trade: ICONS.navTrade,
  leaderboard: ICONS.navLeaderboard,
  profile: ICONS.navProfile,
};

interface MetalTabProps {
  iconSource: ImageSourcePropType;
  focused: boolean;
  badge?: number;
}

const MetalTab = ({ iconSource, focused, badge }: MetalTabProps) => {
  // Drip animation: slow vertical "ooze" cycle, only active for focused tab.
  const drip = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    if (!focused) {
      drip.stopAnimation();
      drip.setValue(0);
      return;
    }
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(drip, {
          toValue: 1,
          duration: 1400,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: true,
        }),
        Animated.timing(drip, {
          toValue: 0,
          duration: 1400,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [focused, drip]);

  const dripTranslate = drip.interpolate({
    inputRange: [0, 1],
    outputRange: [0, 6],
  });
  const dripOpacity = drip.interpolate({
    inputRange: [0, 1],
    outputRange: [0.55, 1],
  });

  return (
    <View style={tabStyles.tabWrap}>
      <View style={[tabStyles.iconPlate, focused && tabStyles.iconPlateActive]}>
        <Image
          source={iconSource}
          style={[
            tabStyles.iconImage,
            focused && tabStyles.iconImageActive,
          ]}
          resizeMode="contain"
        />
        {badge !== undefined && badge > 0 && (
          <View style={tabStyles.badge}>
            <Text style={tabStyles.badgeText}>{badge > 9 ? '9+' : badge}</Text>
          </View>
        )}
      </View>
      {focused && (
        <>
          {/* Slime drip — a tiny bar that oozes downward beneath the icon */}
          <Animated.View
            style={[
              tabStyles.drip,
              {
                opacity: dripOpacity,
                transform: [{ translateY: dripTranslate }],
              },
            ]}
            pointerEvents="none"
          />
          <View style={tabStyles.dripGlow} pointerEvents="none" />
        </>
      )}
    </View>
  );
};

function TabsNavigator() {
  const insets = useSafeAreaInsets();
  const { user, trades } = useApp();
  const bottomPadding = Math.max(insets.bottom, 48);

  const incomingTradeCount = user
    ? trades.filter(t => t.trade.status === 'pending' && t.trade.to_user_id === user.id).length
    : 0;

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: [
          styles.tabBar,
          {
            paddingBottom: bottomPadding,
            height: 64 + bottomPadding,
            marginBottom: Platform.OS === 'android' ? 0 : 0,
          },
        ],
        tabBarActiveTintColor: '#39ff14',
        tabBarInactiveTintColor: '#7a7',
        // Icon-only nav. With 7 tabs on a phone screen there isn't room
        // for labels — they truncate to "Ho.../Ca.../Sh..." which looks
        // worse than no labels. The art is distinct enough to navigate by.
        tabBarShowLabel: false,
        tabBarItemStyle: styles.tabBarItem,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Home',
          tabBarIcon: ({ focused }) => (
            <MetalTab iconSource={TAB_ICONS.index} focused={focused} />
          ),
        }}
      />
      <Tabs.Screen
        name="collection"
        options={{
          title: 'Cards',
          tabBarIcon: ({ focused }) => (
            <MetalTab iconSource={TAB_ICONS.collection} focused={focused} />
          ),
        }}
      />
      <Tabs.Screen
        name="shop"
        options={{
          title: 'Shop',
          tabBarIcon: ({ focused }) => (
            <MetalTab iconSource={TAB_ICONS.shop} focused={focused} />
          ),
        }}
      />
      <Tabs.Screen
        name="goals"
        options={{
          title: 'Goals',
          tabBarIcon: ({ focused }) => (
            <MetalTab iconSource={TAB_ICONS.goals} focused={focused} />
          ),
        }}
      />
      <Tabs.Screen
        name="trade"
        options={{
          title: 'Trade',
          tabBarIcon: ({ focused }) => (
            <MetalTab iconSource={TAB_ICONS.trade} focused={focused} badge={incomingTradeCount} />
          ),
        }}
      />
      <Tabs.Screen
        name="leaderboard"
        options={{
          title: 'Ranks',
          tabBarIcon: ({ focused }) => (
            <MetalTab iconSource={TAB_ICONS.leaderboard} focused={focused} />
          ),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: 'Me',
          tabBarIcon: ({ focused }) => (
            <MetalTab iconSource={TAB_ICONS.profile} focused={focused} />
          ),
        }}
      />
      {/* Hidden screens */}
      <Tabs.Screen name="settings" options={{ title: 'Settings', tabBarButton: () => null }} />
      <Tabs.Screen name="mosh" options={{ title: 'Mosh Pit', tabBarButton: () => null }} />
      <Tabs.Screen name="privacy" options={{ title: 'Privacy Policy', tabBarButton: () => null }} />
      <Tabs.Screen name="payment-success" options={{ title: 'Payment Success', tabBarButton: () => null }} />
    </Tabs>
  );
}

export default function TabLayout() {
  // FONT LOADING — production fix v118.
  //
  // HISTORY of failures:
  //   - v92..v115:   `useFonts({ name: require('.../font.ttf') })` — local
  //                  bundle path. Silently never registered the font on
  //                  Android EAS production builds despite the file being
  //                  in the bundle. fontsLoaded would flip to true but
  //                  TextStyle fontFamily fell back to system. Worked in
  //                  Expo Go, only failed in release.
  //   - v116..v117:  `useFonts({ name: 'https://.../font.otf' })` — remote
  //                  URI from Render backend. Same silent failure on
  //                  Android prod. Headers correct (font/otf, 200 OK),
  //                  the download appears to succeed, registration just
  //                  doesn't take.
  //
  // ROOT CAUSE (after testing): Android's font system in EAS production
  // is unreliable with .OTF files that use the CFF glyph table. It
  // sometimes registers them, sometimes silently no-ops. .TTF files (with
  // glyf/loca tables) work consistently. Both BraverGrave and Critica
  // were shipped as .otf — that was the actual problem the whole time.
  //
  // FIX: We converted both .otf fonts to .ttf via fontTools (CFF → glyf
  // re-rasterization, byte-perfect letterforms, just a different file
  // format). All three custom fonts are now .ttf. We bundle them locally
  // via require() — Android's bundling path is fine for .ttf, only .otf
  // was problematic. The PostScript name registration also works for .ttf
  // where it was inconsistent for .otf.
  //
  // We leave the remote-URI as a fallback ONLY for emergency OTA fixes
  // (the URLs are still valid on the backend) but the primary path is
  // local bundled .ttf.
  // Custom death-metal display fonts (BraverGrave/Critica) were removed
  // in v124 — they kept silently failing on Android in production
  // builds, so we fell back to system bold via `FONTS.death = undefined`.
  // Only MetalMania-Regular remains as a custom face (used for small
  // rank labels / welcome strip — proved reliable on every device).
  const [fontsLoaded, fontError] = useFonts({
    'MetalMania-Regular': require('../assets/fonts/MetalMania-Regular.ttf'),
  });

  // Don't block app render — render either way. SplatTitle will fall back to
  // system bold if the font isn't ready yet. Stops the "won't even open" crash.
  // We still log errors for debugging.
  useEffect(() => {
    if (fontError) {
      console.warn('[font] Custom font failed to load:', fontError);
    }
    if (fontsLoaded) {
      console.log('[font] Metal fonts loaded from CDN');
    }
  }, [fontError, fontsLoaded]);

  // NOTE: an earlier version of this layout (v118 attempt) called
  //   ExpoImage.clearMemoryCache() + clearDiskCache() here on every cold
  //   start as a "safety net" for the WSL-build-corruption issue. That was
  //   a mistake — it ran on EVERY app launch, not just the first one after
  //   reinstall, which meant the app re-downloaded every card image and
  //   badge on every open. On a slow connection this read as "card and
  //   badge images don't load at all." Removed. If a future build needs
  //   a one-shot cache reset, gate it behind AsyncStorage so it actually
  //   runs ONCE per build, not every launch.

  return (
    <ErrorBoundary>
      <AppProvider>
        <UpdateBanner />
        <TabsNavigator />
      </AppProvider>
    </ErrorBoundary>
  );
}

const styles = StyleSheet.create({
  // Rusted-metal bottom bar. Solid color reads cleaner than a gradient
  // for a small bar; the green top border simulates oxidized copper trim.
  //
  // Spacing rationale (we kept iterating on this for weeks):
  //   - The PARENT tabBarStyle is the WRAPPER, not the row container.
  //     React Navigation v7 renders items inside an inner View with
  //     `flex: 1, flexDirection: 'row'` — so `justifyContent` on
  //     tabBarStyle has no effect on item distribution. Setting it
  //     here was a no-op.
  //   - Each item gets `flex: 1` by default, so 7 items ARE evenly
  //     distributed across the row mathematically. What made them
  //     LOOK squished was the old 48×38 iconPlate eating ~94% of the
  //     ~52dp wide per-tab cell on a 400dp Android phone, leaving
  //     no breathing room between plates.
  //   - Fix below: smaller iconPlate (38×34) + zero paddingHorizontal
  //     on the bar so the cells are full width.
  tabBar: {
    backgroundColor: '#1a1410',
    borderTopColor: '#39ff14',
    borderTopWidth: 1,
    paddingTop: 6,
    paddingHorizontal: 0,
    shadowColor: '#000',
    shadowOpacity: 0.4,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: -2 },
    elevation: 8,
  },
  tabBarLabel: {
    fontSize: 9,
    fontWeight: '800',
    marginTop: 2,
    letterSpacing: 0,
  },
  tabBarItem: {
    // flex:1 is also applied by RN's default `styles.bottomItem` —
    // re-declaring it explicitly so it can't get overridden by RN's
    // merge order. Each tab gets exactly screenWidth/7 of horizontal
    // space; the icon centers inside that cell.
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 2,
    paddingHorizontal: 0,
  },
});

const tabStyles = StyleSheet.create({
  tabWrap: {
    alignItems: 'center',
    justifyContent: 'flex-start',
    paddingTop: 4,
  },
  iconPlate: {
    // Plain transparent wrapper — no background, no border. Earlier we kept
    // a rusted-metal rectangle around each icon for the "studded plate" look,
    // but with 7 tabs on a phone-width bar the visible rectangles butted up
    // against each other and made the bar read as a solid wall of buttons
    // instead of clearly-separated tabs. Stripping the background reveals
    // the real spacing between icons.
    width: 38,
    height: 34,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'transparent',
    borderWidth: 0,
    overflow: 'visible',
  },
  iconImage: {
    width: 26,
    height: 26,
    opacity: 0.72,
  },
  iconImageActive: {
    width: 30,
    height: 30,
    opacity: 1,
  },
  iconPlateActive: {
    // Only the active tab gets a subtle green glow — translucent fill + shadow.
    // Earlier the file had a SECOND `iconPlateActive` definition further down
    // that JS silently overrode this one with (object key collision: last
    // wins). The override painted an OPAQUE dark-green rectangle on the
    // active tab which read as a hard square button stuck to its neighbours.
    // The duplicate has been deleted so this style now actually applies.
    backgroundColor: 'rgba(57, 255, 20, 0.12)',
    borderRadius: 10,
    shadowColor: '#39ff14',
    shadowOpacity: 0.8,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 0 },
    elevation: 8,
  },
  drip: {
    position: 'absolute',
    bottom: -8,
    width: 3,
    height: 10,
    borderRadius: 1.5,
    backgroundColor: '#39ff14',
  },
  dripGlow: {
    position: 'absolute',
    bottom: -10,
    width: 14,
    height: 14,
    borderRadius: 7,
    backgroundColor: 'rgba(57, 255, 20, 0.25)',
  },
  badge: {
    position: 'absolute',
    top: -4,
    right: -6,
    backgroundColor: '#FF3B30',
    borderRadius: 9,
    minWidth: 18,
    height: 18,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 4,
    borderWidth: 1,
    borderColor: '#1a1410',
  },
  badgeText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '800',
  },
});

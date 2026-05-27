import React, { useEffect, useRef } from 'react';
import { Tabs } from 'expo-router';
import { AppProvider, useApp } from '../src/context/AppContext';
import { View, StyleSheet, Text, Platform, Animated, Easing, Image, ImageSourcePropType } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useFonts } from 'expo-font';
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
  // Load Metal Mania font at runtime from local TTF asset.
  // Graceful fallback: if it fails to load we still render the app with
  // system font — no splash gate, no crash.
  const [fontsLoaded, fontError] = useFonts({
    // Key MUST match the TTF's internal PostScript name (nameID 6).
    // Inspected with the name table parser — it's `MetalMania-Regular`,
    // NOT `MetalMania`. Using the wrong key causes Android to fall back
    // to system font silently in production builds.
    'MetalMania-Regular': require('../assets/fonts/MetalMania-Regular.ttf'),
  });

  // Don't block app render — render either way. SplatTitle will fall back to
  // system bold if the font isn't ready yet. Stops the "won't even open" crash.
  // We still log errors for debugging.
  useEffect(() => {
    if (fontError) {
      console.warn('[font] MetalMania failed to load:', fontError);
    }
  }, [fontError]);

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
  // `justifyContent: space-evenly` is belt-and-suspenders with flex:1 on
  // tabBarItem — React Navigation's tab bar sometimes ignores per-item
  // flex when labels are hidden, leaving tabs clustered with a gap on
  // the right. Forcing the parent layout to space-evenly guarantees they
  // spread across the full bar width.
  tabBar: {
    backgroundColor: '#1a1410',
    borderTopColor: '#39ff14',
    borderTopWidth: 1,
    paddingTop: 6,
    justifyContent: 'space-evenly',
    // Subtle dark shadow above for separation from screen content
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
    width: 48,
    height: 38,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#241a14',
    borderWidth: 1,
    borderColor: '#3a2a20',
    // Rusted-rivet inset look via inner shadow trick: use border-top lighter
    // and border-bottom darker (RN can't do real insets but this fakes it).
    borderTopColor: '#4a3527',
    borderBottomColor: '#1a0e08',
    overflow: 'hidden',
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
    backgroundColor: '#1a2a14',
    borderColor: '#39ff14',
    shadowColor: '#39ff14',
    shadowOpacity: 0.6,
    shadowRadius: 5,
    shadowOffset: { width: 0, height: 0 },
    elevation: 6,
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

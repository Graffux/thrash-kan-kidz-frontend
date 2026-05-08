import React from 'react';
import { Tabs } from 'expo-router';
import { AppProvider, useApp } from '../src/context/AppContext';
import { View, StyleSheet, Text, Platform } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { ErrorBoundary } from '../src/components/ErrorBoundary';

// Tab icon component using emojis for reliable rendering
const TabIcon = ({ emoji, focused, badge }: { emoji: string; focused: boolean; badge?: number }) => (
  <View>
    <Text style={[styles.tabIcon, focused && styles.tabIconFocused]}>{emoji}</Text>
    {badge !== undefined && badge > 0 && (
      <View style={styles.badge}>
        <Text style={styles.badgeText}>{badge > 9 ? '9+' : badge}</Text>
      </View>
    )}
  </View>
);

function TabsNavigator() {
  const insets = useSafeAreaInsets();
  const { user, trades } = useApp();
  const bottomPadding = Math.max(insets.bottom, 48);
  // Tab sound effects removed: each useSoundPlayer holds a persistent
  // native ExoPlayer instance, and 5 permanent players in the tab bar
  // was contributing to OutOfMemoryError crashes on low-RAM Android
  // devices. Cash register still plays on Shop (inside shop.tsx) where
  // it's more noticeable; tab-tap sounds are minor UX polish not worth
  // the memory cost on low-end devices.

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
              height: 70 + bottomPadding,
              marginBottom: Platform.OS === 'android' ? 0 : 0,
            }
          ],
          tabBarActiveTintColor: '#FFD700',
          tabBarInactiveTintColor: '#888',
          tabBarLabelStyle: styles.tabBarLabel,
          tabBarItemStyle: styles.tabBarItem,
        }}
      >
        <Tabs.Screen
          name="index"
          options={{
            title: 'Home',
            tabBarIcon: ({ focused }) => (
              <TabIcon emoji="🏠" focused={focused} />
            ),
          }}
        />
        <Tabs.Screen
          name="collection"
          options={{
            title: 'Collection',
            tabBarIcon: ({ focused }) => (
              <TabIcon emoji="🃏" focused={focused} />
            ),
          }}
        />
        <Tabs.Screen
          name="shop"
          options={{
            title: 'Shop',
            tabBarIcon: ({ focused }) => (
              <TabIcon emoji="🛒" focused={focused} />
            ),
          }}
        />
        <Tabs.Screen
          name="goals"
          options={{
            title: 'Goals',
            tabBarIcon: ({ focused }) => (
              <TabIcon emoji="🏆" focused={focused} />
            ),
          }}
        />
        <Tabs.Screen
          name="trade"
          options={{
            title: 'Trade',
            tabBarIcon: ({ focused }) => (
              <TabIcon emoji="🔄" focused={focused} badge={incomingTradeCount} />
            ),
          }}
        />
        <Tabs.Screen
          name="profile"
          options={{
            title: 'Profile',
            tabBarIcon: ({ focused }) => (
              <TabIcon emoji="👤" focused={focused} />
            ),
          }}
        />
        {/* Hidden screens - not shown in tab bar */}
        <Tabs.Screen
          name="privacy"
          options={{
            title: 'Privacy Policy',
            tabBarButton: () => null, // Hide from tab bar
          }}
        />
        <Tabs.Screen
          name="payment-success"
          options={{
            title: 'Payment Success',
            tabBarButton: () => null, // Hide from tab bar
          }}
        />
      </Tabs>
  );
}

export default function TabLayout() {
  return (
    <ErrorBoundary>
      <AppProvider>
        <TabsNavigator />
      </AppProvider>
    </ErrorBoundary>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: '#1a1a2e',
    borderTopColor: '#333',
    borderTopWidth: 1,
    paddingTop: 8,
  },
  tabBarLabel: {
    fontSize: 10,
    fontWeight: '600',
    marginTop: 4,
  },
  tabBarItem: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 4,
    minWidth: 60,
  },
  tabIcon: {
    fontSize: 28,
  },
  tabIconFocused: {
    transform: [{ scale: 1.2 }],
  },
  badge: {
    position: 'absolute',
    top: -4,
    right: -10,
    backgroundColor: '#FF3B30',
    borderRadius: 9,
    minWidth: 18,
    height: 18,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 4,
  },
  badgeText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '800',
  },
});

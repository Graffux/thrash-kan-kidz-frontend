import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import Constants from 'expo-constants';
import { Image as ExpoImage } from 'expo-image';
import { cardThumb } from '../utils/cardImage';

// Set global axios timeout for Render cold starts
axios.defaults.timeout = 30000;

// HARDCODED - no env vars, no config, no bullshit
const API_URL = 'https://thrash-kan-kidz-api.onrender.com';

interface User {
  id: string;
  username: string;
  coins: number;
  daily_login_streak: number;
  last_login_date: string | null;
  profile_completed: boolean;
  bio: string;
  avatar_url: string;
  created_at: string;
  friend_code?: string;
  friend_count?: number;
  medals?: number;
  free_packs?: number;
  series_milestone_claimed?: number[];
  featured_card_ids?: string[];
  completed_series?: number[];
  rank?: {
    id: string;
    name: string;
    crest_url: string;
    min_series_cleared: number;
  } | null;
  // Daily-login coin boost (VIP supporter). When `coin_boost_expires_at`
  // is in the future, the user earns 25 coins/day instead of 10 and gets
  // a VIP chip in Mosh Pit + on Home. Cleared automatically once the
  // timestamp passes.
  is_vip_supporter?: boolean;
  coin_boost_expires_at?: string | null;
}

interface Card {
  id: string;
  name: string;
  description: string;
  rarity: string;
  front_image_url: string;
  back_image_url: string;
  coin_cost: number;
  available: boolean;
  created_at: string;
  series?: number;
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

interface Goal {
  id: string;
  title: string;
  description: string;
  goal_type: string;
  target_value: number;
  reward_coins: number;
  reward_card_id: string | null;
}

interface UserGoal {
  user_goal: {
    id: string;
    user_id: string;
    goal_id: string;
    progress: number;
    completed: boolean;
    completed_at: string | null;
  };
  goal: Goal;
}

interface Trade {
  trade: {
    id: string;
    from_user_id: string;
    to_user_id: string;
    offered_card_ids: string[];
    requested_card_ids: string[];
    status: string;
    created_at: string;
  };
  from_user: User;
  to_user: User;
  offered_cards: Card[];
  requested_cards: Card[];
}

// Returned by `/api/series/list`. Includes coming_soon / scheduled series
// so the Collection screen can render greyed-out tiles for them.
export interface SeriesCatalogEntry {
  series: number;
  name: string;
  description: string;
  cards_required: number;
  has_reward: boolean;
  released: boolean;
  status: 'released' | 'scheduled' | 'coming_soon';
  release_date: string | null; // ISO 8601, UTC
}

interface AppContextType {
  user: User | null;
  allCards: Card[];
  seriesCatalog: SeriesCatalogEntry[];
  userCards: UserCard[];
  userGoals: UserGoal[];
  trades: Trade[];
  allUsers: User[];
  loading: boolean;
  apiUrl: string;
  login: (username: string, password: string, isRegister?: boolean) => Promise<void>;
  logout: () => Promise<void>;
  claimDailyLogin: () => Promise<{ streak: number; bonus_coins: number; message: string }>;
  purchaseCard: (cardId: string) => Promise<any>;
  updateProfile: (bio: string) => Promise<void>;
  updateAvatar: (avatarDataUri: string) => Promise<void>;
  updateFeaturedCards: (cardIds: string[]) => Promise<void>;
  createTrade: (toUserId: string, offeredCardIds: string[], requestedCardIds: string[]) => Promise<void>;
  acceptTrade: (tradeId: string) => Promise<void>;
  rejectTrade: (tradeId: string) => Promise<void>;
  cancelTrade: (tradeId: string) => Promise<void>;
  refreshData: () => Promise<void>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [allCards, setAllCards] = useState<Card[]>([]);
  const [seriesCatalog, setSeriesCatalog] = useState<SeriesCatalogEntry[]>([]);
  const [userCards, setUserCards] = useState<UserCard[]>([]);
  const [userGoals, setUserGoals] = useState<UserGoal[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadUser();
    loadCards();
  }, []);

  useEffect(() => {
    if (user) {
      loadUserData();
    }
  }, [user?.id]);

  const loadUser = async () => {
    try {
      const userId = await AsyncStorage.getItem('userId');
      if (userId) {
        // Retry up to 3 times with increasing delays (server may be restarting)
        let lastError;
        for (let attempt = 0; attempt < 3; attempt++) {
          try {
            const response = await axios.get(`${API_URL}/api/users/${userId}`);
            setUser(response.data);
            return;
          } catch (err) {
            lastError = err;
            if (attempt < 2) {
              await new Promise(resolve => setTimeout(resolve, (attempt + 1) * 2000));
            }
          }
        }
        console.log('Failed to restore session after retries:', lastError);
      }
    } catch (error) {
      console.log('No saved user found');
    } finally {
      setLoading(false);
    }
  };

  const loadCards = async () => {
    try {
      // Fire both card list and series catalog in parallel. The catalog
      // includes coming-soon / scheduled series so the Collection screen
      // can render greyed-out tiles for upcoming releases.
      const [cardsRes, catalogRes] = await Promise.all([
        axios.get(`${API_URL}/api/cards`),
        axios.get(`${API_URL}/api/series/list`),
      ]);
      setAllCards(cardsRes.data);
      setSeriesCatalog(catalogRes.data?.series ?? []);
    } catch (error) {
      console.error('Failed to load cards:', error);
    }
  };

  const loadUserData = async () => {
    if (!user) return;
    
    try {
      const [cardsRes, goalsRes, tradesRes, usersRes] = await Promise.all([
        axios.get(`${API_URL}/api/users/${user.id}/cards`),
        axios.get(`${API_URL}/api/users/${user.id}/goals`),
        axios.get(`${API_URL}/api/users/${user.id}/trades`),
        axios.get(`${API_URL}/api/users`)
      ]);
      
      setUserCards(cardsRes.data);
      setUserGoals(goalsRes.data);
      setTrades(tradesRes.data);
      setAllUsers(usersRes.data.filter((u: User) => u.id !== user.id));

      // Prefetch all owned card thumbnails into expo-image's disk cache in
      // the background. We prefetch thumb URLs (~50KB each) rather than the
      // original PNGs (~3MB) so cellular users actually finish the prefetch.
      // First-time load fills the cache; subsequent renders are instant.
      try {
        const urls: string[] = [];
        for (const uc of cardsRes.data as { card?: { id?: string; front_image_url?: string } }[]) {
          if (uc?.card) {
            const url = cardThumb(uc.card, 240);
            if (url) urls.push(url);
          }
        }
        if (urls.length > 0) {
          ExpoImage.prefetch(urls, 'memory-disk').catch(() => {});
        }
      } catch {
        // Defensive — never block app boot on prefetch.
      }
    } catch (error) {
      console.error('Failed to load user data:', error);
    }
  };

  const login = async (username: string, password: string, isRegister: boolean = false) => {
    let lastError;
    for (let attempt = 0; attempt < 5; attempt++) {
      try {
        if (isRegister) {
          const response = await axios.post(`${API_URL}/api/auth/register`, { username, password });
          setUser(response.data);
          await AsyncStorage.setItem('userId', response.data.id);
        } else {
          const response = await axios.post(`${API_URL}/api/auth/login`, { username, password });
          setUser(response.data);
          await AsyncStorage.setItem('userId', response.data.id);
        }
        return;
      } catch (error: any) {
        lastError = error;
        const status = error.response?.status;
        if (status === 401 || status === 403 || status === 400) {
          throw new Error(error.response?.data?.detail || 'Authentication failed');
        }
        if (attempt < 4) {
          await new Promise(resolve => setTimeout(resolve, 5000));
        }
      }
    }
    throw new Error(lastError?.response?.data?.detail || 'Server unavailable, please try again');
  };

  const logout = async () => {
    await AsyncStorage.removeItem('userId');
    setUser(null);
    setUserCards([]);
    setUserGoals([]);
    setTrades([]);
  };

  const claimDailyLogin = async () => {
    if (!user) throw new Error('Not logged in');
    
    const response = await axios.post(`${API_URL}/api/users/${user.id}/daily-login`);
    
    // Refresh user data
    const userRes = await axios.get(`${API_URL}/api/users/${user.id}`);
    setUser(userRes.data);
    
    // Refresh goals
    const goalsRes = await axios.get(`${API_URL}/api/users/${user.id}/goals`);
    setUserGoals(goalsRes.data);
    
    return response.data;
  };

  const purchaseCard = async (cardId: string) => {
    if (!user) throw new Error('Not logged in');
    
    const response = await axios.post(`${API_URL}/api/users/${user.id}/purchase-card`, {
      user_id: user.id,
      card_id: cardId
    });
    
    // Refresh data
    await refreshData();
    
    // Return the response data (includes newly_unlocked_rare_card if any)
    return response.data;
  };

  const updateProfile = async (bio: string) => {
    if (!user) throw new Error('Not logged in');
    
    const response = await axios.put(`${API_URL}/api/users/${user.id}/profile`, { bio });
    setUser(response.data);
    
    // Refresh goals
    const goalsRes = await axios.get(`${API_URL}/api/users/${user.id}/goals`);
    setUserGoals(goalsRes.data);
  };

  const updateAvatar = async (avatarDataUri: string) => {
    if (!user) throw new Error('Not logged in');
    const response = await axios.put(
      `${API_URL}/api/users/${user.id}/profile`,
      { avatar_url: avatarDataUri },
    );
    setUser(response.data);
  };

  const updateFeaturedCards = async (cardIds: string[]) => {
    if (!user) throw new Error('Not logged in');
    const response = await axios.put(
      `${API_URL}/api/users/${user.id}/featured-cards`,
      { card_ids: cardIds },
    );
    setUser(response.data);
  };

  const createTrade = async (toUserId: string, offeredCardIds: string[], requestedCardIds: string[]) => {
    if (!user) throw new Error('Not logged in');
    
    await axios.post(`${API_URL}/api/trades`, {
      from_user_id: user.id,
      to_user_id: toUserId,
      offered_card_ids: offeredCardIds,
      requested_card_ids: requestedCardIds
    });
    
    // Refresh trades
    const tradesRes = await axios.get(`${API_URL}/api/users/${user.id}/trades`);
    setTrades(tradesRes.data);
  };

  const acceptTrade = async (tradeId: string) => {
    if (!user) throw new Error('Not logged in');
    
    await axios.post(`${API_URL}/api/trades/${tradeId}/action`, {
      trade_id: tradeId,
      user_id: user.id,
      action: 'accept'
    });
    
    await refreshData();
  };

  const rejectTrade = async (tradeId: string) => {
    if (!user) throw new Error('Not logged in');
    
    await axios.post(`${API_URL}/api/trades/${tradeId}/action`, {
      trade_id: tradeId,
      user_id: user.id,
      action: 'reject'
    });
    
    // Refresh trades
    const tradesRes = await axios.get(`${API_URL}/api/users/${user.id}/trades`);
    setTrades(tradesRes.data);
  };

  const cancelTrade = async (tradeId: string) => {
    if (!user) throw new Error('Not logged in');
    
    await axios.post(`${API_URL}/api/trades/${tradeId}/action`, {
      trade_id: tradeId,
      user_id: user.id,
      action: 'cancel'
    });
    
    // Refresh trades
    const tradesRes = await axios.get(`${API_URL}/api/users/${user.id}/trades`);
    setTrades(tradesRes.data);
  };

  const refreshData = async () => {
    if (!user) return;
    
    try {
      const [userRes, cardsRes, goalsRes, tradesRes, allCardsRes] = await Promise.all([
        axios.get(`${API_URL}/api/users/${user.id}`),
        axios.get(`${API_URL}/api/users/${user.id}/cards`),
        axios.get(`${API_URL}/api/users/${user.id}/goals`),
        axios.get(`${API_URL}/api/users/${user.id}/trades`),
        axios.get(`${API_URL}/api/cards`)
      ]);
      
      setUser(userRes.data);
      setUserCards(cardsRes.data);
      setUserGoals(goalsRes.data);
      setTrades(tradesRes.data);
      setAllCards(allCardsRes.data);
    } catch (error) {
      console.error('Failed to refresh data:', error);
    }
  };

  return (
    <AppContext.Provider
      value={{
        user,
        allCards,
        seriesCatalog,
        userCards,
        userGoals,
        trades,
        allUsers,
        loading,
        apiUrl: API_URL,
        login,
        logout,
        claimDailyLogin,
        purchaseCard,
        updateProfile,
        updateAvatar,
        updateFeaturedCards,
        createTrade,
        acceptTrade,
        rejectTrade,
        cancelTrade,
        refreshData,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within AppProvider');
  }
  return context;
};

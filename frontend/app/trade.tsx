import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
  Modal,
  Alert,
  ActivityIndicator,
  TextInput,
  Share,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Image as ExpoImage } from 'expo-image';
import { useApp } from '../src/context/AppContext';

const BACKGROUND_IMAGE = 'https://customer-assets.emergentagent.com/job_earn-cards/artifacts/zgy2com2_enhanced-1771247671181.jpg';

export default function TradeScreen() {
  const {
    user,
    userCards,
    trades,
    allUsers,
    apiUrl,
    createTrade,
    acceptTrade,
    rejectTrade,
    cancelTrade,
    refreshData,
  } = useApp();

  const [activeTab, setActiveTab] = useState<'friends' | 'trades'>('friends');
  const [showNewTrade, setShowNewTrade] = useState(false);
  const [selectedUser, setSelectedUser] = useState<any>(null);
  const [offeredCards, setOfferedCards] = useState<string[]>([]);
  const [requestedCards, setRequestedCards] = useState<string[]>([]);
  const [creating, setCreating] = useState(false);
  const [processing, setProcessing] = useState<string | null>(null);
  const [targetUserCards, setTargetUserCards] = useState<any[]>([]);
  const [loadingTargetCards, setLoadingTargetCards] = useState(false);

  // Friends state
  const [friends, setFriends] = useState<any[]>([]);
  const [friendRequests, setFriendRequests] = useState<{ incoming: any[]; outgoing: any[] }>({ incoming: [], outgoing: [] });
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const [loadingFriends, setLoadingFriends] = useState(false);
  const [friendCode, setFriendCode] = useState('');
  const [activeUsers, setActiveUsers] = useState<any[]>([]);
  const [loadingActive, setLoadingActive] = useState(false);

  const loadFriends = useCallback(async () => {
    if (!user) return;
    setLoadingFriends(true);
    try {
      const [friendsRes, requestsRes] = await Promise.all([
        fetch(`${apiUrl}/api/friends/${user.id}`),
        fetch(`${apiUrl}/api/friends/${user.id}/requests`),
      ]);
      const friendsData = await friendsRes.json();
      const requestsData = await requestsRes.json();
      setFriends(friendsData.friends || []);
      setFriendRequests({
        incoming: requestsData.incoming || [],
        outgoing: requestsData.outgoing || [],
      });
    } catch (err) {
      console.error('Error loading friends:', err);
    } finally {
      setLoadingFriends(false);
    }
  }, [user, apiUrl]);

  const loadActiveUsers = useCallback(async () => {
    if (!user) return;
    setLoadingActive(true);
    try {
      const res = await fetch(`${apiUrl}/api/users/recently-active?user_id=${user.id}`);
      const data = await res.json();
      setActiveUsers(data.users || []);
    } catch (err) {
      console.error('Error loading active users:', err);
    } finally {
      setLoadingActive(false);
    }
  }, [user, apiUrl]);

  useEffect(() => {
    loadFriends();
    loadActiveUsers();
  }, [loadFriends, loadActiveUsers]);

  // Heartbeat every 2 minutes
  useEffect(() => {
    if (!user) return;
    const sendHeartbeat = () => {
      fetch(`${apiUrl}/api/users/${user.id}/heartbeat`, { method: 'POST' }).catch(() => {});
    };
    sendHeartbeat();
    const interval = setInterval(sendHeartbeat, 120000);
    return () => clearInterval(interval);
  }, [user, apiUrl]);

  useEffect(() => {
    if (user) {
      setFriendCode(user.friend_code || '');
    }
  }, [user]);

  if (!user) {
    return (
      <SafeAreaView style={styles.container}>
        <Image source={{ uri: BACKGROUND_IMAGE }} style={styles.backgroundImage} resizeMode="cover" />
        <View style={styles.backgroundOverlay} />
        <View style={styles.centerContainer}>
          <Ionicons name="lock-closed" size={48} color="#666" />
          <Text style={styles.lockedText}>Please login to trade cards</Text>
        </View>
      </SafeAreaView>
    );
  }

  const handleSearch = async () => {
    if (!searchQuery.trim() || searchQuery.trim().length < 2) return;
    setSearching(true);
    try {
      const isCode = searchQuery.trim().length === 6 && /^[A-Z0-9]+$/i.test(searchQuery.trim());
      const param = isCode ? `code=${searchQuery.trim().toUpperCase()}` : `query=${searchQuery.trim()}`;
      const res = await fetch(`${apiUrl}/api/users/search?${param}`);
      const data = await res.json();
      const filtered = (data.users || []).filter((u: any) => u.id !== user.id);
      setSearchResults(filtered);
    } catch (err) {
      console.error('Search error:', err);
    } finally {
      setSearching(false);
    }
  };

  const handleSendRequest = async (toUserId: string) => {
    try {
      const res = await fetch(`${apiUrl}/api/friends/request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from_user_id: user.id, to_user_id: toUserId }),
      });
      const data = await res.json();
      if (data.success) {
        Alert.alert('Success', data.message);
        setSearchResults([]);
        setSearchQuery('');
        loadFriends();
      } else {
        Alert.alert('Error', data.detail || 'Failed to send request');
      }
    } catch (err) {
      Alert.alert('Error', 'Failed to send friend request');
    }
  };

  const handleAcceptRequest = async (requestId: string) => {
    try {
      const res = await fetch(`${apiUrl}/api/friends/accept/${requestId}`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        Alert.alert('Success', 'Friend request accepted!');
        loadFriends();
      }
    } catch (err) {
      Alert.alert('Error', 'Failed to accept request');
    }
  };

  const handleRejectRequest = async (requestId: string) => {
    try {
      const res = await fetch(`${apiUrl}/api/friends/reject/${requestId}`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        loadFriends();
      }
    } catch (err) {
      Alert.alert('Error', 'Failed to reject request');
    }
  };

  const handleShareCode = async () => {
    try {
      await Share.share({
        message: `Add me on Thrash Kan Kidz! My friend code is: ${friendCode}`,
      });
    } catch (err) {}
  };

  const isFriend = (userId: string) => friends.some((f: any) => f.id === userId);
  const hasPendingRequest = (userId: string) =>
    friendRequests.outgoing.some((r: any) => r.to_user_id === userId) ||
    friendRequests.incoming.some((r: any) => r.from_user_id === userId);

  // Trade functions
  const pendingTrades = trades.filter(t => t.trade.status === 'pending');
  const incomingTrades = pendingTrades.filter(t => t.trade.to_user_id === user.id);
  const outgoingTrades = pendingTrades.filter(t => t.trade.from_user_id === user.id);
  const completedTrades = trades.filter(
    t => t.trade.status === 'accepted' || t.trade.status === 'rejected' || t.trade.status === 'cancelled'
  );

  const handleCreateTrade = async () => {
    if (!selectedUser) { Alert.alert('Error', 'Please select a friend to trade with'); return; }
    if (offeredCards.length === 0 && requestedCards.length === 0) { Alert.alert('Error', 'Please select cards to trade'); return; }
    setCreating(true);
    try {
      await createTrade(selectedUser.id, offeredCards, requestedCards);
      Alert.alert('Success', 'Trade offer sent!');
      setShowNewTrade(false);
      setSelectedUser(null);
      setOfferedCards([]);
      setRequestedCards([]);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to create trade');
    } finally {
      setCreating(false);
    }
  };

  const handleAcceptTrade = async (tradeId: string) => {
    setProcessing(tradeId);
    try {
      await acceptTrade(tradeId);
      Alert.alert('Success', 'Trade completed!');
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to accept trade');
    } finally { setProcessing(null); }
  };

  const handleRejectTrade = async (tradeId: string) => {
    setProcessing(tradeId);
    try {
      await rejectTrade(tradeId);
      Alert.alert('Done', 'Trade rejected');
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to reject trade');
    } finally { setProcessing(null); }
  };

  const handleCancelTrade = async (tradeId: string) => {
    setProcessing(tradeId);
    try {
      await cancelTrade(tradeId);
      Alert.alert('Done', 'Trade cancelled');
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to cancel trade');
    } finally { setProcessing(null); }
  };

  const toggleOfferedCard = (cardId: string) => {
    setOfferedCards(prev => prev.includes(cardId) ? prev.filter(id => id !== cardId) : [...prev, cardId]);
  };
  const toggleRequestedCard = (cardId: string) => {
    setRequestedCards(prev => prev.includes(cardId) ? prev.filter(id => id !== cardId) : [...prev, cardId]);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return '#FF9800';
      case 'accepted': return '#4CAF50';
      case 'rejected': return '#F44336';
      case 'cancelled': return '#666';
      default: return '#666';
    }
  };

  const renderTradeCard = (trade: any, isIncoming: boolean) => (
    <View key={trade.trade.id} style={styles.tradeCard}>
      <View style={styles.tradeHeader}>
        <View style={styles.tradeUsers}>
          <Text style={styles.tradeUserLabel}>{isIncoming ? 'From' : 'To'}</Text>
          <Text style={styles.tradeUsername}>
            {isIncoming ? trade.from_user?.username : trade.to_user?.username}
          </Text>
        </View>
        <View style={[styles.statusBadge, { backgroundColor: getStatusColor(trade.trade.status) }]}>
          <Text style={styles.statusText}>{trade.trade.status.toUpperCase()}</Text>
        </View>
      </View>
      <View style={styles.tradeCardsContainer}>
        <View style={styles.tradeCardsSection}>
          <Text style={styles.tradeCardsLabel}>Offered:</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            {trade.offered_cards.map((card: any) => (
              <View key={card.id} style={styles.miniCard}>
                <Image source={{ uri: card.front_image_url }} style={styles.miniCardImage} resizeMode="cover" />
              </View>
            ))}
          </ScrollView>
        </View>
        <Ionicons name="swap-horizontal" size={24} color="#666" style={styles.swapIcon} />
        <View style={styles.tradeCardsSection}>
          <Text style={styles.tradeCardsLabel}>Requested:</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            {trade.requested_cards.map((card: any) => (
              <View key={card.id} style={styles.miniCard}>
                <Image source={{ uri: card.front_image_url }} style={styles.miniCardImage} resizeMode="cover" />
              </View>
            ))}
          </ScrollView>
        </View>
      </View>
      {trade.trade.status === 'pending' && (
        <View style={styles.tradeActions}>
          {isIncoming ? (
            <>
              <TouchableOpacity style={[styles.tradeActionButton, styles.acceptButton]} onPress={() => handleAcceptTrade(trade.trade.id)} disabled={processing === trade.trade.id}>
                {processing === trade.trade.id ? <ActivityIndicator size="small" color="#fff" /> : (<><Ionicons name="checkmark" size={18} color="#fff" /><Text style={styles.tradeActionButtonText}>Accept</Text></>)}
              </TouchableOpacity>
              <TouchableOpacity style={[styles.tradeActionButton, styles.rejectButton]} onPress={() => handleRejectTrade(trade.trade.id)} disabled={processing === trade.trade.id}>
                <Ionicons name="close" size={18} color="#fff" /><Text style={styles.tradeActionButtonText}>Reject</Text>
              </TouchableOpacity>
            </>
          ) : (
            <TouchableOpacity style={[styles.tradeActionButton, styles.cancelButton]} onPress={() => handleCancelTrade(trade.trade.id)} disabled={processing === trade.trade.id}>
              {processing === trade.trade.id ? <ActivityIndicator size="small" color="#fff" /> : (<><Ionicons name="trash" size={18} color="#fff" /><Text style={styles.tradeActionButtonText}>Cancel</Text></>)}
            </TouchableOpacity>
          )}
        </View>
      )}
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <Image source={{ uri: BACKGROUND_IMAGE }} style={styles.backgroundImage} resizeMode="cover" />
      <View style={styles.backgroundOverlay} />
      <View style={styles.header}>
        <ExpoImage source={{ uri: 'https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/z4mb78cz_enhanced-1776904246547.png' }} style={styles.headerImage} contentFit="contain" />
      </View>

      {/* Tab Switcher */}
      <View style={styles.tabBar}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'friends' && styles.tabActive]}
          onPress={() => setActiveTab('friends')}
          data-testid="friends-tab"
        >
          <Ionicons name="people" size={18} color={activeTab === 'friends' ? '#FFD700' : '#888'} />
          <Text style={[styles.tabText, activeTab === 'friends' && styles.tabTextActive]}>
            Friends ({friends.length})
          </Text>
          {friendRequests.incoming.length > 0 && (
            <View style={styles.requestBadge}>
              <Text style={styles.requestBadgeText}>{friendRequests.incoming.length}</Text>
            </View>
          )}
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'trades' && styles.tabActive]}
          onPress={() => setActiveTab('trades')}
          data-testid="trades-tab"
        >
          <Ionicons name="swap-horizontal" size={18} color={activeTab === 'trades' ? '#FFD700' : '#888'} />
          <Text style={[styles.tabText, activeTab === 'trades' && styles.tabTextActive]}>
            Trades ({pendingTrades.length})
          </Text>
        </TouchableOpacity>
      </View>

      {activeTab === 'friends' ? (
        <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
          {/* Your Friend Code */}
          <View style={styles.friendCodeSection} data-testid="friend-code-section">
            <Text style={styles.friendCodeLabel}>Your Friend Code</Text>
            <View style={styles.friendCodeRow}>
              <Text style={styles.friendCodeText} data-testid="friend-code-display">{friendCode}</Text>
              <TouchableOpacity style={styles.shareButton} onPress={handleShareCode} data-testid="share-code-btn">
                <Ionicons name="share-social" size={20} color="#000" />
                <Text style={styles.shareButtonText}>Share</Text>
              </TouchableOpacity>
            </View>
          </View>

          {/* Search */}
          <View style={styles.searchSection}>
            <Text style={styles.sectionLabel}>Add Friends</Text>
            <View style={styles.searchRow}>
              <TextInput
                style={styles.searchInput}
                placeholder="Username or friend code"
                placeholderTextColor="#666"
                value={searchQuery}
                onChangeText={setSearchQuery}
                onSubmitEditing={handleSearch}
                autoCapitalize="none"
                data-testid="friend-search-input"
              />
              <TouchableOpacity style={styles.searchButton} onPress={handleSearch} data-testid="friend-search-btn">
                {searching ? <ActivityIndicator size="small" color="#000" /> : <Ionicons name="search" size={20} color="#000" />}
              </TouchableOpacity>
            </View>

            {/* Search Results */}
            {searchResults.map(u => (
              <View key={u.id} style={styles.searchResultItem}>
                <Ionicons name="person-circle" size={36} color="#888" />
                <View style={styles.searchResultInfo}>
                  <Text style={styles.searchResultName}>{u.username}</Text>
                  <Text style={styles.searchResultMeta}>{u.friend_count || 0} friends</Text>
                </View>
                {isFriend(u.id) ? (
                  <View style={styles.friendBadge}><Text style={styles.friendBadgeText}>Friends</Text></View>
                ) : hasPendingRequest(u.id) ? (
                  <View style={styles.pendingBadge}><Text style={styles.pendingBadgeText}>Pending</Text></View>
                ) : (
                  <TouchableOpacity style={styles.addButton} onPress={() => handleSendRequest(u.id)} data-testid={`add-friend-${u.username}`}>
                    <Ionicons name="person-add" size={18} color="#000" />
                  </TouchableOpacity>
                )}
              </View>
            ))}
          </View>

          {/* Recently Active Users */}
          {activeUsers.length > 0 && (
            <View style={styles.activeSection} data-testid="recently-active-section">
              <View style={styles.activeSectionHeader}>
                <View style={styles.activeIndicator} />
                <Text style={styles.sectionLabel}>Players Online ({activeUsers.length})</Text>
              </View>
              {activeUsers.map(u => (
                <View key={u.id} style={styles.activeUserItem}>
                  <View style={styles.activeUserLeft}>
                    <View style={styles.onlineDot} />
                    <Ionicons name="person-circle" size={36} color="#4CAF50" />
                  </View>
                  <View style={styles.searchResultInfo}>
                    <Text style={styles.searchResultName}>{u.username}</Text>
                    <Text style={styles.searchResultMeta}>{u.friend_count || 0} friends</Text>
                  </View>
                  {u.is_friend ? (
                    <View style={styles.friendBadge}><Text style={styles.friendBadgeText}>Friends</Text></View>
                  ) : u.has_pending_request ? (
                    <View style={styles.pendingBadge}><Text style={styles.pendingBadgeText}>Pending</Text></View>
                  ) : (
                    <TouchableOpacity style={styles.addButton} onPress={() => handleSendRequest(u.id)} data-testid={`add-active-${u.username}`}>
                      <Ionicons name="person-add" size={18} color="#000" />
                    </TouchableOpacity>
                  )}
                </View>
              ))}
            </View>
          )}

          {/* Incoming Requests */}
          {friendRequests.incoming.length > 0 && (
            <View style={styles.requestsSection}>
              <Text style={styles.sectionLabel}>Friend Requests ({friendRequests.incoming.length})</Text>
              {friendRequests.incoming.map(req => (
                <View key={req.id} style={styles.requestItem}>
                  <Ionicons name="person-circle" size={36} color="#FFD700" />
                  <Text style={styles.requestName}>{req.from_username}</Text>
                  <View style={styles.requestActions}>
                    <TouchableOpacity style={styles.acceptSmall} onPress={() => handleAcceptRequest(req.id)} data-testid={`accept-request-${req.id}`}>
                      <Ionicons name="checkmark" size={20} color="#fff" />
                    </TouchableOpacity>
                    <TouchableOpacity style={styles.rejectSmall} onPress={() => handleRejectRequest(req.id)} data-testid={`reject-request-${req.id}`}>
                      <Ionicons name="close" size={20} color="#fff" />
                    </TouchableOpacity>
                  </View>
                </View>
              ))}
            </View>
          )}

          {/* Friends List */}
          <View style={styles.friendsListSection}>
            <Text style={styles.sectionLabel}>Your Friends</Text>
            {loadingFriends ? (
              <ActivityIndicator size="small" color="#FFD700" style={{ marginVertical: 20 }} />
            ) : friends.length === 0 ? (
              <View style={styles.emptyFriends}>
                <Ionicons name="people-outline" size={48} color="#444" />
                <Text style={styles.emptyFriendsText}>No friends yet</Text>
                <Text style={styles.emptyFriendsSubtext}>Search by username or share your friend code</Text>
              </View>
            ) : (
              friends.map((friend: any) => (
                <View key={friend.id} style={styles.friendItem} data-testid={`friend-${friend.username}`}>
                  <Ionicons name="person-circle" size={40} color="#4CAF50" />
                  <View style={styles.friendInfo}>
                    <Text style={styles.friendName}>{friend.username}</Text>
                    <Text style={styles.friendMeta}>{friend.friend_count || 0} friends</Text>
                  </View>
                  <TouchableOpacity
                    style={styles.tradeWithButton}
                    onPress={() => {
                      setSelectedUser(friend);
                      setActiveTab('trades');
                      setShowNewTrade(true);
                      setLoadingTargetCards(true);
                      fetch(`${apiUrl}/api/users/${friend.id}/cards`)
                        .then(res => res.json())
                        .then(data => { setTargetUserCards(data.cards || data || []); setLoadingTargetCards(false); })
                        .catch(() => { setTargetUserCards([]); setLoadingTargetCards(false); });
                    }}
                    data-testid={`trade-with-${friend.username}`}
                  >
                    <Ionicons name="swap-horizontal" size={16} color="#000" />
                    <Text style={styles.tradeWithText}>Trade</Text>
                  </TouchableOpacity>
                </View>
              ))
            )}
          </View>
          <View style={styles.spacer} />
        </ScrollView>
      ) : (
        <>
          <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
            {incomingTrades.length > 0 && (
              <>
                <Text style={styles.sectionLabel}>Incoming Offers ({incomingTrades.length})</Text>
                {incomingTrades.map(trade => renderTradeCard(trade, true))}
              </>
            )}
            {outgoingTrades.length > 0 && (
              <>
                <Text style={styles.sectionLabel}>Your Offers ({outgoingTrades.length})</Text>
                {outgoingTrades.map(trade => renderTradeCard(trade, false))}
              </>
            )}
            {pendingTrades.length === 0 && (
              <View style={styles.emptyState}>
                <Ionicons name="swap-horizontal" size={64} color="#666" />
                <Text style={styles.emptyText}>No active trades</Text>
                <Text style={styles.emptySubtext}>
                  {friends.length === 0 ? 'Add friends first to start trading!' : 'Start trading with your friends!'}
                </Text>
              </View>
            )}
            {completedTrades.length > 0 && (
              <>
                <Text style={styles.sectionLabel}>Trade History</Text>
                {completedTrades.slice(0, 5).map(trade => (
                  <View key={trade.trade.id} style={[styles.tradeCard, styles.historyCard]}>
                    <View style={styles.tradeHeader}>
                      <Text style={styles.historyText}>{trade.from_user?.username} - {trade.to_user?.username}</Text>
                      <View style={[styles.statusBadge, { backgroundColor: getStatusColor(trade.trade.status) }]}>
                        <Text style={styles.statusText}>{trade.trade.status.toUpperCase()}</Text>
                      </View>
                    </View>
                  </View>
                ))}
              </>
            )}
            <View style={styles.spacer} />
          </ScrollView>

          {friends.length > 0 && (
            <TouchableOpacity style={styles.newTradeFloating} onPress={() => setShowNewTrade(true)} data-testid="new-trade-btn">
              <Ionicons name="add" size={28} color="#000" />
            </TouchableOpacity>
          )}
        </>
      )}

      {/* New Trade Modal */}
      <Modal visible={showNewTrade} animationType="slide" transparent onRequestClose={() => setShowNewTrade(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>New Trade</Text>
              <TouchableOpacity onPress={() => { setShowNewTrade(false); setSelectedUser(null); setTargetUserCards([]); setOfferedCards([]); setRequestedCards([]); }}>
                <Ionicons name="close" size={24} color="#fff" />
              </TouchableOpacity>
            </View>
            <ScrollView style={styles.modalScroll}>
              <Text style={styles.modalSectionTitle}>Trade With Friend</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.userList}>
                {friends.map((f: any) => (
                  <TouchableOpacity
                    key={f.id}
                    style={[styles.userItem, selectedUser?.id === f.id && styles.userItemSelected]}
                    onPress={() => {
                      setSelectedUser(f);
                      setRequestedCards([]);
                      setLoadingTargetCards(true);
                      fetch(`${apiUrl}/api/users/${f.id}/cards`)
                        .then(res => res.json())
                        .then(data => { setTargetUserCards(data.cards || data || []); setLoadingTargetCards(false); })
                        .catch(() => { setTargetUserCards([]); setLoadingTargetCards(false); });
                    }}
                  >
                    <Ionicons name="person-circle" size={40} color={selectedUser?.id === f.id ? '#FFD700' : '#666'} />
                    <Text style={[styles.userItemName, selectedUser?.id === f.id && styles.userItemNameSelected]}>{f.username}</Text>
                  </TouchableOpacity>
                ))}
                {friends.length === 0 && <Text style={styles.noUsersText}>Add friends first to trade</Text>}
              </ScrollView>

              <Text style={styles.modalSectionTitle}>Your Cards to Offer</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                {userCards.map(uc => (
                  <TouchableOpacity key={uc.card.id} style={[styles.selectableCard, offeredCards.includes(uc.card.id) && styles.selectableCardSelected]} onPress={() => toggleOfferedCard(uc.card.id)}>
                    <Image source={{ uri: uc.card.front_image_url }} style={styles.selectableCardImage} resizeMode="cover" />
                    {offeredCards.includes(uc.card.id) && (<View style={styles.selectedOverlay}><Ionicons name="checkmark-circle" size={24} color="#4CAF50" /></View>)}
                  </TouchableOpacity>
                ))}
              </ScrollView>

              {selectedUser && (
                <>
                  <Text style={styles.modalSectionTitle}>Request from {selectedUser.username}</Text>
                  <Text style={styles.modalHint}>Select cards you want in exchange</Text>
                  {loadingTargetCards ? (
                    <ActivityIndicator size="small" color="#FFD700" style={{ marginVertical: 20 }} />
                  ) : targetUserCards.length > 0 ? (
                    <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                      {targetUserCards.map((uc: any) => {
                        const card = uc.card || uc;
                        return (
                          <TouchableOpacity key={`req_${card.id}`} style={[styles.selectableCard, requestedCards.includes(card.id) && styles.selectableCardSelected]} onPress={() => toggleRequestedCard(card.id)}>
                            <Image source={{ uri: card.front_image_url }} style={styles.selectableCardImage} resizeMode="cover" />
                            {requestedCards.includes(card.id) && (<View style={styles.selectedOverlay}><Ionicons name="checkmark-circle" size={24} color="#4CAF50" /></View>)}
                          </TouchableOpacity>
                        );
                      })}
                    </ScrollView>
                  ) : (
                    <Text style={styles.modalHint}>This friend has no cards yet</Text>
                  )}
                </>
              )}
            </ScrollView>
            <TouchableOpacity
              style={[styles.createTradeButton, (!selectedUser || (offeredCards.length === 0 && requestedCards.length === 0)) && styles.createTradeButtonDisabled]}
              onPress={handleCreateTrade}
              disabled={creating || !selectedUser || (offeredCards.length === 0 && requestedCards.length === 0)}
            >
              {creating ? <ActivityIndicator color="#000" /> : <Text style={styles.createTradeButtonText}>Send Trade Offer</Text>}
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f0f1a' },
  backgroundImage: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, width: '100%', height: '100%' },
  backgroundOverlay: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0, 0, 0, 0.7)' },
  centerContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 32 },
  lockedText: { color: '#aaa', fontSize: 16, marginTop: 16, textAlign: 'center' },
  header: { paddingHorizontal: 16, paddingTop: 12, paddingBottom: 8 },
  headerImage: { width: 200, height: 80, alignSelf: 'center' },
  title: { fontSize: 28, fontWeight: 'bold', color: '#fff' },

  // Tab Bar
  tabBar: { flexDirection: 'row', marginHorizontal: 16, marginBottom: 12, backgroundColor: 'rgba(26, 26, 46, 0.9)', borderRadius: 12, padding: 4 },
  tab: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 10, borderRadius: 10, gap: 6 },
  tabActive: { backgroundColor: 'rgba(255, 215, 0, 0.15)' },
  tabText: { fontSize: 14, color: '#888', fontWeight: '600' },
  tabTextActive: { color: '#FFD700' },
  requestBadge: { backgroundColor: '#F44336', width: 20, height: 20, borderRadius: 10, justifyContent: 'center', alignItems: 'center' },
  requestBadgeText: { color: '#fff', fontSize: 11, fontWeight: 'bold' },

  // Friend Code Section
  friendCodeSection: { backgroundColor: 'rgba(26, 26, 46, 0.9)', borderRadius: 14, padding: 16, marginHorizontal: 16, marginBottom: 12, borderWidth: 1, borderColor: '#333' },
  friendCodeLabel: { fontSize: 12, color: '#888', marginBottom: 8 },
  friendCodeRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  friendCodeText: { fontSize: 28, fontWeight: 'bold', color: '#FFD700', letterSpacing: 4 },
  shareButton: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#FFD700', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20, gap: 4 },
  shareButtonText: { color: '#000', fontSize: 13, fontWeight: 'bold' },

  // Search
  searchSection: { marginHorizontal: 16, marginBottom: 12 },
  sectionLabel: { fontSize: 16, fontWeight: 'bold', color: '#fff', marginBottom: 10 },
  searchRow: { flexDirection: 'row', gap: 8, marginBottom: 8 },
  searchInput: { flex: 1, backgroundColor: 'rgba(255,255,255,0.08)', borderRadius: 12, paddingHorizontal: 14, paddingVertical: 10, color: '#fff', fontSize: 14, borderWidth: 1, borderColor: '#333' },
  searchButton: { backgroundColor: '#FFD700', width: 44, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },

  // Search Results
  searchResultItem: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(26, 26, 46, 0.9)', borderRadius: 12, padding: 12, marginBottom: 8, borderWidth: 1, borderColor: '#333' },
  searchResultInfo: { flex: 1, marginLeft: 10 },
  searchResultName: { color: '#fff', fontSize: 15, fontWeight: '600' },
  searchResultMeta: { color: '#888', fontSize: 12, marginTop: 2 },
  addButton: { backgroundColor: '#FFD700', width: 36, height: 36, borderRadius: 18, justifyContent: 'center', alignItems: 'center' },
  friendBadge: { backgroundColor: '#4CAF50', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  friendBadgeText: { color: '#fff', fontSize: 11, fontWeight: 'bold' },
  pendingBadge: { backgroundColor: '#FF9800', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  pendingBadgeText: { color: '#fff', fontSize: 11, fontWeight: 'bold' },

  // Friend Requests
  requestsSection: { marginHorizontal: 16, marginBottom: 12 },
  // Recently Active
  activeSection: { marginHorizontal: 16, marginBottom: 12 },
  activeSectionHeader: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 10 },
  activeIndicator: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#4CAF50' },
  activeUserItem: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(76, 175, 80, 0.08)', borderRadius: 12, padding: 12, marginBottom: 8, borderWidth: 1, borderColor: 'rgba(76, 175, 80, 0.3)' },
  activeUserLeft: { position: 'relative' },
  onlineDot: { position: 'absolute', top: 0, right: 0, width: 10, height: 10, borderRadius: 5, backgroundColor: '#4CAF50', borderWidth: 2, borderColor: '#1a1a2e', zIndex: 1 },
  requestItem: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(255, 215, 0, 0.08)', borderRadius: 12, padding: 12, marginBottom: 8, borderWidth: 1, borderColor: '#FFD700' },
  requestName: { flex: 1, color: '#fff', fontSize: 15, fontWeight: '600', marginLeft: 10 },
  requestActions: { flexDirection: 'row', gap: 8 },
  acceptSmall: { backgroundColor: '#4CAF50', width: 36, height: 36, borderRadius: 18, justifyContent: 'center', alignItems: 'center' },
  rejectSmall: { backgroundColor: '#F44336', width: 36, height: 36, borderRadius: 18, justifyContent: 'center', alignItems: 'center' },

  // Friends List
  friendsListSection: { marginHorizontal: 16, marginBottom: 12 },
  emptyFriends: { alignItems: 'center', paddingVertical: 32 },
  emptyFriendsText: { color: '#666', fontSize: 16, marginTop: 12 },
  emptyFriendsSubtext: { color: '#444', fontSize: 13, marginTop: 4, textAlign: 'center' },
  friendItem: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(26, 26, 46, 0.9)', borderRadius: 12, padding: 12, marginBottom: 8, borderWidth: 1, borderColor: '#333' },
  friendInfo: { flex: 1, marginLeft: 10 },
  friendName: { color: '#fff', fontSize: 15, fontWeight: '600' },
  friendMeta: { color: '#888', fontSize: 12, marginTop: 2 },
  tradeWithButton: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#FFD700', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 16, gap: 4 },
  tradeWithText: { color: '#000', fontSize: 13, fontWeight: 'bold' },

  // Trades tab
  scrollView: { flex: 1 },
  tradeCard: { backgroundColor: 'rgba(26, 26, 46, 0.9)', borderRadius: 16, padding: 16, marginHorizontal: 16, marginBottom: 12, borderWidth: 1, borderColor: '#333' },
  historyCard: { opacity: 0.6 },
  tradeHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  tradeUsers: { flex: 1 },
  tradeUserLabel: { fontSize: 12, color: '#888' },
  tradeUsername: { fontSize: 16, fontWeight: 'bold', color: '#fff' },
  historyText: { fontSize: 14, color: '#888' },
  statusBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  statusText: { color: '#fff', fontSize: 10, fontWeight: 'bold' },
  tradeCardsContainer: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  tradeCardsSection: { flex: 1 },
  tradeCardsLabel: { fontSize: 12, color: '#888', marginBottom: 8 },
  swapIcon: { marginHorizontal: 8 },
  miniCard: { width: 50, height: 70, borderRadius: 6, overflow: 'hidden', marginRight: 6, backgroundColor: '#333' },
  miniCardImage: { width: '100%', height: '100%' },
  tradeActions: { flexDirection: 'row', gap: 12 },
  tradeActionButton: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', padding: 12, borderRadius: 12, gap: 6 },
  tradeActionButtonText: { color: '#fff', fontWeight: 'bold' },
  acceptButton: { backgroundColor: '#4CAF50' },
  rejectButton: { backgroundColor: '#F44336' },
  cancelButton: { backgroundColor: '#666' },
  emptyState: { alignItems: 'center', paddingVertical: 48, marginHorizontal: 16 },
  emptyText: { color: '#666', fontSize: 18, marginTop: 16 },
  emptySubtext: { color: '#444', fontSize: 14, marginTop: 8, textAlign: 'center' },
  spacer: { height: 80 },

  // FAB
  newTradeFloating: { position: 'absolute', bottom: 90, right: 20, backgroundColor: '#FFD700', width: 56, height: 56, borderRadius: 28, justifyContent: 'center', alignItems: 'center', elevation: 5 },

  // Modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0, 0, 0, 0.9)', justifyContent: 'flex-end' },
  modalContent: { backgroundColor: '#1a1a2e', borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 20, maxHeight: '90%' },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  modalTitle: { fontSize: 24, fontWeight: 'bold', color: '#fff' },
  modalScroll: { maxHeight: 400 },
  modalSectionTitle: { fontSize: 16, fontWeight: 'bold', color: '#fff', marginBottom: 12, marginTop: 16 },
  modalHint: { fontSize: 12, color: '#888', marginBottom: 8 },
  userList: { flexDirection: 'row' },
  userItem: { alignItems: 'center', padding: 12, marginRight: 12, borderRadius: 12, backgroundColor: '#0f0f1a' },
  userItemSelected: { backgroundColor: 'rgba(255, 215, 0, 0.1)', borderWidth: 1, borderColor: '#FFD700' },
  userItemName: { color: '#888', fontSize: 12, marginTop: 4 },
  userItemNameSelected: { color: '#FFD700' },
  noUsersText: { color: '#666', fontSize: 14, padding: 20 },
  selectableCard: { width: 80, height: 110, borderRadius: 8, overflow: 'hidden', marginRight: 10, backgroundColor: '#333' },
  selectableCardSelected: { borderWidth: 2, borderColor: '#4CAF50' },
  selectableCardImage: { width: '100%', height: '100%' },
  selectedOverlay: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(0, 0, 0, 0.5)', justifyContent: 'center', alignItems: 'center' },
  createTradeButton: { backgroundColor: '#FFD700', padding: 16, borderRadius: 12, alignItems: 'center', marginTop: 20 },
  createTradeButtonDisabled: { backgroundColor: '#333' },
  createTradeButtonText: { color: '#000', fontSize: 16, fontWeight: 'bold' },
});

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  ActivityIndicator,
  Platform,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useIAP, ErrorCode } from 'expo-iap';
import { useApp } from '../context/AppContext';

// Google Play product SKUs (must match products created in Play Console)
const GOOGLE_PLAY_SKUS: Record<string, string> = {
  small: 'thrash_kan_kidz_coins_200',
  medium: 'thrash_kan_kidz_coins_500',
  large: 'thrash_kan_kidz_coins_1000',
};

const SKU_LIST = Object.values(GOOGLE_PLAY_SKUS);

interface CoinPackage {
  id: string;
  name: string;
  coins: number;
  price: string | number;
  bonus?: number;
  total_coins?: number;
  bonus_coins?: number;
  first_purchase_bonus?: boolean;
}

interface BuyCoinsModalProps {
  visible: boolean;
  onClose: () => void;
}

function BuyCoinsContent({ visible, onClose }: BuyCoinsModalProps) {
  const { user, apiUrl, refreshData } = useApp();
  const [packages, setPackages] = useState<CoinPackage[]>([]);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isFirstPurchase, setIsFirstPurchase] = useState(false);
  const [bonusPercentage, setBonusPercentage] = useState(0);

  const verifyWithBackend = useCallback(
    async (purchase: any) => {
      if (!user) return false;
      const purchaseToken =
        purchase?.purchaseToken ||
        purchase?.purchaseTokenAndroid ||
        purchase?.transactionReceipt;
      const productId = purchase?.productId || purchase?.id;

      if (!purchaseToken || !productId) {
        setError('Purchase data incomplete');
        return false;
      }

      try {
        const response = await fetch(
          `${apiUrl}/api/users/${user.id}/verify-google-purchase`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              user_id: user.id,
              product_id: productId,
              purchase_token: purchaseToken,
            }),
          }
        );
        const data = await response.json();
        if (response.ok && data.success) {
          Alert.alert(
            'Success!',
            `${data.coins_granted} coins added to your account!`
          );
          refreshData();
          onClose();
          return true;
        }
        setError(data?.detail || 'Purchase verification failed');
        return false;
      } catch (err) {
        setError('Failed to verify purchase with server');
        return false;
      }
    },
    [user, apiUrl, refreshData, onClose]
  );

  const {
    connected,
    products,
    fetchProducts,
    requestPurchase,
    finishTransaction,
  } = useIAP({
    onPurchaseSuccess: async (purchase: any) => {
      try {
        const verified = await verifyWithBackend(purchase);
        // Finish the transaction regardless; consumable so Google removes it
        try {
          await finishTransaction({ purchase, isConsumable: true });
        } catch (finishErr) {
          console.warn('[IAP] finishTransaction error:', finishErr);
        }
        if (!verified) {
          setError('Purchase completed but could not be credited. Contact support.');
        }
      } catch (err) {
        setError('Purchase processing failed');
      } finally {
        setPurchasing(null);
      }
    },
    onPurchaseError: (err: any) => {
      if (err?.code !== ErrorCode?.UserCancelled && err?.code !== 'E_USER_CANCELLED') {
        setError(err?.message || 'Purchase failed. Please try again.');
      }
      setPurchasing(null);
    },
  });

  // Fetch coin packages metadata from backend
  const fetchPackages = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      const response = await fetch(
        `${apiUrl}/api/users/${user.id}/coin-packages`
      );
      const data = await response.json();
      setPackages(data.packages || []);
      setIsFirstPurchase(data.is_first_purchase || false);
      setBonusPercentage(data.first_purchase_bonus_percentage || 0);
    } catch (err) {
      setError('Failed to load coin packages');
    } finally {
      setLoading(false);
    }
  }, [user, apiUrl]);

  // Fetch Google Play products once connected
  useEffect(() => {
    if (visible && connected && Platform.OS === 'android') {
      fetchProducts({ skus: SKU_LIST, type: 'in-app' }).catch((err) => {
        console.warn('[IAP] fetchProducts error:', err);
      });
    }
  }, [visible, connected, fetchProducts]);

  useEffect(() => {
    if (visible) {
      setError(null);
      fetchPackages();
    }
  }, [visible, fetchPackages]);

  const handlePurchase = async (pkg: CoinPackage) => {
    if (!user) return;
    setPurchasing(pkg.id);
    setError(null);

    if (Platform.OS !== 'android') {
      setError('In-app purchases are only available on Android');
      setPurchasing(null);
      return;
    }

    if (!connected) {
      setError('Connecting to Google Play... Please try again in a moment.');
      setPurchasing(null);
      return;
    }

    const sku = GOOGLE_PLAY_SKUS[pkg.id];
    if (!sku) {
      setError('Product not configured');
      setPurchasing(null);
      return;
    }

    const product = products?.find(
      (p: any) => p.id === sku || p.productId === sku
    );
    if (!product) {
      setError(
        'Product not yet available in Google Play. Make sure you are signed into the account that has access to this testing track.'
      );
      setPurchasing(null);
      return;
    }

    try {
      await requestPurchase({
        request: {
          android: { skus: [sku] },
          ios: { sku },
        },
        type: 'in-app',
      });
      // onPurchaseSuccess / onPurchaseError will handle the rest
    } catch (err: any) {
      if (err?.code !== 'E_USER_CANCELLED') {
        setError(err?.message || 'Failed to start purchase');
      }
      setPurchasing(null);
    }
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <View style={styles.content}>
          <View style={styles.header}>
            <Text style={styles.title} testID="buy-coins-title">
              Buy Coins
            </Text>
            <TouchableOpacity
              onPress={onClose}
              style={styles.closeBtn}
              testID="buy-coins-close-btn"
            >
              <Ionicons name="close" size={24} color="#fff" />
            </TouchableOpacity>
          </View>

          {error && (
            <View style={styles.errorContainer}>
              <Text style={styles.errorText} testID="buy-coins-error-text">
                {error}
              </Text>
            </View>
          )}

          {isFirstPurchase && (
            <View style={styles.firstPurchaseBanner}>
              <Ionicons name="star" size={20} color="#FFD700" />
              <Text style={styles.firstPurchaseText}>
                FIRST PURCHASE - {bonusPercentage}% BONUS COINS!
              </Text>
              <Ionicons name="star" size={20} color="#FFD700" />
            </View>
          )}

          {loading ? (
            <ActivityIndicator
              size="large"
              color="#FFD700"
              style={{ marginVertical: 40 }}
            />
          ) : (
            <View style={styles.packagesContainer}>
              {packages.map((pkg: any) => {
                const sku = GOOGLE_PLAY_SKUS[pkg.id];
                const storeProduct = products?.find(
                  (p: any) => p.id === sku || p.productId === sku
                );
                const displayPrice =
                  storeProduct?.displayPrice || `$${pkg.price}`;
                return (
                  <TouchableOpacity
                    key={pkg.id}
                    style={[
                      styles.packageCard,
                      purchasing === pkg.id && styles.packageCardDisabled,
                    ]}
                    onPress={() => handlePurchase(pkg)}
                    disabled={purchasing !== null}
                    testID={`buy-coins-package-${pkg.id}`}
                  >
                    <View style={styles.packageInfo}>
                      <Text style={styles.packageName}>{pkg.name}</Text>
                      <Text style={styles.packageCoins}>
                        {pkg.first_purchase_bonus
                          ? `${pkg.total_coins} coins`
                          : `${pkg.coins} coins`}
                      </Text>
                      {pkg.first_purchase_bonus && pkg.bonus_coins > 0 && (
                        <Text style={styles.packageBonus}>
                          +{pkg.bonus_coins} bonus coins!
                        </Text>
                      )}
                    </View>
                    <View style={styles.packagePriceContainer}>
                      {purchasing === pkg.id ? (
                        <ActivityIndicator size="small" color="#000" />
                      ) : (
                        <Text style={styles.packagePrice}>{displayPrice}</Text>
                      )}
                    </View>
                  </TouchableOpacity>
                );
              })}
            </View>
          )}

          {Platform.OS === 'android' && !connected && (
            <Text style={styles.connectingText}>
              Connecting to Google Play...
            </Text>
          )}
        </View>
      </View>
    </Modal>
  );
}

export default function BuyCoinsModal(props: BuyCoinsModalProps) {
  return <BuyCoinsContent {...props} />;
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.85)',
    justifyContent: 'flex-end',
  },
  content: {
    backgroundColor: '#1a1a2e',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 20,
    maxHeight: '70%',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFD700',
  },
  closeBtn: {
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: 20,
    padding: 6,
  },
  errorContainer: {
    backgroundColor: 'rgba(244, 67, 54, 0.15)',
    padding: 12,
    borderRadius: 8,
    marginBottom: 12,
  },
  errorText: {
    color: '#F44336',
    fontSize: 13,
    textAlign: 'center',
  },
  firstPurchaseBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(255, 215, 0, 0.15)',
    borderWidth: 1,
    borderColor: '#FFD700',
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 16,
    marginBottom: 16,
    gap: 8,
  },
  firstPurchaseText: {
    color: '#FFD700',
    fontSize: 14,
    fontWeight: 'bold',
  },
  packagesContainer: {
    gap: 12,
  },
  packageCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: '#333',
  },
  packageCardDisabled: {
    opacity: 0.5,
  },
  packageInfo: {
    flex: 1,
  },
  packageName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
  },
  packageCoins: {
    fontSize: 14,
    color: '#FFD700',
    marginTop: 2,
  },
  packageBonus: {
    fontSize: 12,
    color: '#4CAF50',
    fontWeight: '600',
    marginTop: 2,
  },
  packagePriceContainer: {
    backgroundColor: '#FFD700',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 12,
    minWidth: 70,
    alignItems: 'center',
  },
  packagePrice: {
    color: '#000',
    fontSize: 16,
    fontWeight: 'bold',
  },
  connectingText: {
    color: '#888',
    fontSize: 12,
    textAlign: 'center',
    marginTop: 12,
  },
});

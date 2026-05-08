import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useApp } from '../src/context/AppContext';

export default function PaymentSuccessScreen() {
  const { session_id } = useLocalSearchParams();
  const router = useRouter();
  const { apiUrl, refreshData } = useApp();
  const [status, setStatus] = useState<'checking' | 'success' | 'failed' | 'pending'>('checking');
  const [coinsAdded, setCoinsAdded] = useState(0);
  const [pollCount, setPollCount] = useState(0);

  const BACKGROUND_IMAGE = 'https://customer-assets.emergentagent.com/job_earn-cards/artifacts/zgy2com2_enhanced-1771247671181.jpg';
  const MAX_POLLS = 10;
  const POLL_INTERVAL = 2000;

  useEffect(() => {
    if (session_id) {
      checkPaymentStatus();
    }
  }, [session_id]);

  const checkPaymentStatus = async () => {
    if (pollCount >= MAX_POLLS) {
      setStatus('pending');
      return;
    }

    try {
      const response = await fetch(`${apiUrl}/api/payments/status/${session_id}`);
      const data = await response.json();

      if (data.payment_status === 'paid') {
        setStatus('success');
        setCoinsAdded(data.coins_credited || 0);
        // Refresh user data to update coin balance
        await refreshData();
        
        // Redirect to shop after 3 seconds
        setTimeout(() => {
          router.replace('/shop');
        }, 3000);
      } else if (data.status === 'expired' || data.payment_status === 'failed') {
        setStatus('failed');
        setTimeout(() => {
          router.replace('/shop');
        }, 3000);
      } else {
        // Still pending, poll again
        setPollCount(prev => prev + 1);
        setTimeout(checkPaymentStatus, POLL_INTERVAL);
      }
    } catch (error) {
      console.error('Error checking payment status:', error);
      setPollCount(prev => prev + 1);
      setTimeout(checkPaymentStatus, POLL_INTERVAL);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <Image
        source={{ uri: BACKGROUND_IMAGE }}
        style={styles.backgroundImage}
        resizeMode="cover"
      />
      <View style={styles.overlay} />
      
      <View style={styles.content}>
        {status === 'checking' && (
          <>
            <ActivityIndicator size="large" color="#FFD700" />
            <Text style={styles.title}>Processing Payment...</Text>
            <Text style={styles.subtitle}>Please wait while we confirm your purchase</Text>
          </>
        )}

        {status === 'success' && (
          <>
            <View style={styles.successIcon}>
              <Ionicons name="checkmark-circle" size={80} color="#4CAF50" />
            </View>
            <Text style={styles.title}>Payment Successful!</Text>
            <Text style={styles.coinsText}>+{coinsAdded} Coins Added</Text>
            <Text style={styles.subtitle}>Redirecting to shop...</Text>
          </>
        )}

        {status === 'failed' && (
          <>
            <View style={styles.failedIcon}>
              <Ionicons name="close-circle" size={80} color="#f44336" />
            </View>
            <Text style={styles.title}>Payment Failed</Text>
            <Text style={styles.subtitle}>Something went wrong. Redirecting...</Text>
          </>
        )}

        {status === 'pending' && (
          <>
            <View style={styles.pendingIcon}>
              <Ionicons name="time" size={80} color="#FFD700" />
            </View>
            <Text style={styles.title}>Payment Processing</Text>
            <Text style={styles.subtitle}>
              Your payment is being processed. Coins will be added shortly.
            </Text>
            <Text style={styles.redirectText} onPress={() => router.replace('/shop')}>
              Go to Shop →
            </Text>
          </>
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f0f1a',
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
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  successIcon: {
    marginBottom: 20,
  },
  failedIcon: {
    marginBottom: 20,
  },
  pendingIcon: {
    marginBottom: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 12,
    textAlign: 'center',
  },
  coinsText: {
    fontSize: 36,
    fontWeight: 'bold',
    color: '#FFD700',
    marginBottom: 16,
  },
  subtitle: {
    fontSize: 16,
    color: '#888',
    textAlign: 'center',
  },
  redirectText: {
    fontSize: 16,
    color: '#FFD700',
    marginTop: 20,
    textDecorationLine: 'underline',
  },
});

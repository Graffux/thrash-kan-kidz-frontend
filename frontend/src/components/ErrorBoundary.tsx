import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Platform } from 'react-native';
import Constants from 'expo-constants';

const APP_VERSION =
  (Constants?.expoConfig?.version || '0.0.0') +
  ' (' +
  ((Platform.OS === 'android'
    ? (Constants?.expoConfig as any)?.android?.versionCode
    : (Constants?.expoConfig as any)?.ios?.buildNumber) || '?') +
  ')';

const BACKEND_URL = (process.env.EXPO_PUBLIC_BACKEND_URL || '').replace(/\/+$/, '');

interface Props {
  children: React.ReactNode;
}

interface State {
  error: Error | null;
}

/**
 * Top-level React error boundary. Catches render-time JS errors that would
 * otherwise show the red screen / crash. Posts crash context to
 * /api/crash-log so we see issues with full screen context immediately,
 * before Play Console can aggregate ANRs/crashes.
 *
 * Class component is required — hooks cannot catch render errors.
 */
export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    this.report(error, info.componentStack);
  }

  async report(error: Error, componentStack?: string) {
    if (!BACKEND_URL) return;
    try {
      await fetch(`${BACKEND_URL}/api/crash-log`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          error: String(error?.message || error),
          stack: error?.stack || null,
          component_stack: componentStack || null,
          screen: 'unknown',
          user_id: null,
          platform: Platform.OS,
          app_version: APP_VERSION,
          device_info: {
            os_version: Platform.Version,
          },
        }),
      });
    } catch (_e) {
      // Swallow — we never want crash reporting to itself crash.
    }
  }

  reset = () => {
    this.setState({ error: null });
  };

  render() {
    if (this.state.error) {
      return (
        <View style={styles.wrap} data-testid="error-boundary-fallback">
          <Text style={styles.skull}>💀</Text>
          <Text style={styles.title}>SOMETHING THRASHED TOO HARD</Text>
          <Text style={styles.subtitle}>
            The app hit an error. We've already logged it — your collection is safe.
          </Text>
          <Text style={styles.errorText} numberOfLines={4}>
            {String(this.state.error?.message || this.state.error)}
          </Text>
          <TouchableOpacity
            style={styles.btn}
            onPress={this.reset}
            data-testid="error-boundary-reset-btn"
          >
            <Text style={styles.btnText}>HORNS UP &amp; RETRY</Text>
          </TouchableOpacity>
        </View>
      );
    }
    return this.props.children;
  }
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    backgroundColor: '#0f0f1a',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  skull: { fontSize: 64, marginBottom: 12 },
  title: {
    color: '#FFD700',
    fontSize: 18,
    fontWeight: '900',
    letterSpacing: 2,
    textAlign: 'center',
    marginBottom: 12,
  },
  subtitle: {
    color: '#bbb',
    fontSize: 13,
    textAlign: 'center',
    marginBottom: 18,
  },
  errorText: {
    color: '#ff6b6b',
    fontSize: 11,
    fontStyle: 'italic',
    textAlign: 'center',
    marginBottom: 28,
    paddingHorizontal: 12,
  },
  btn: {
    backgroundColor: '#FFD700',
    paddingHorizontal: 28,
    paddingVertical: 12,
    borderRadius: 10,
  },
  btnText: {
    color: '#0f0f1a',
    fontSize: 13,
    fontWeight: '900',
    letterSpacing: 1.5,
  },
});

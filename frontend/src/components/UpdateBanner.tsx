/**
 * UpdateBanner — full-screen modal when the user's app is out of date, OR
 * a thin tappable banner if there's an optional OTA update ready to install.
 *
 * Two paths run in parallel on launch:
 *   1) Native version check via `/api/app-version`
 *        - If versionCode < min_version_code → BLOCKING modal
 *        - If versionCode < latest_version_code → DISMISSIBLE banner
 *   2) OTA check via expo-updates
 *        - If a newer JS bundle is available → fetch, then prompt to reload
 *
 * Why both:
 *   - Native version check covers builds that need Play Store updates
 *     (icon swaps, new permissions, native packages)
 *   - OTA covers JS-only changes (UI tweaks, prompt copy, bug fixes) and
 *     ships them instantly without a Play release
 */
import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  Linking,
  Platform,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import Constants from 'expo-constants';
import * as Updates from 'expo-updates';
import axios from 'axios';
import { useApp } from '../context/AppContext';

interface VersionInfo {
  latest_version_code: number;
  latest_version_name: string;
  min_version_code: number;
  update_url: string;
  release_notes: string;
}

type Mode = 'idle' | 'soft-banner' | 'hard-block' | 'ota-ready';

export const UpdateBanner: React.FC = () => {
  const { apiUrl } = useApp();
  const [mode, setMode] = useState<Mode>('idle');
  const [info, setInfo] = useState<VersionInfo | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const [otaReloading, setOtaReloading] = useState(false);

  // Helper: read this build's versionCode. Falls back to 0 in dev.
  const currentVersionCode: number =
    (Constants.expoConfig?.android?.versionCode as number | undefined) ?? 0;

  useEffect(() => {
    let cancelled = false;

    // ── 1) Native version check ───────────────────────────────────────
    (async () => {
      try {
        const res = await axios.get(`${apiUrl}/api/app-version`, { timeout: 8000 });
        if (cancelled) return;
        const v: VersionInfo = res.data;
        setInfo(v);
        if (currentVersionCode > 0) {
          if (currentVersionCode < v.min_version_code) {
            setMode('hard-block');
          } else if (currentVersionCode < v.latest_version_code) {
            setMode('soft-banner');
          }
        }
      } catch {
        // Silently ignore — better to not show the banner than show stale info.
      }
    })();

    // ── 2) OTA check (only in production builds — `Updates.isEnabled` is
    //         false in Expo Go / dev client, so this no-ops safely).
    (async () => {
      if (!Updates.isEnabled) return;
      try {
        const check = await Updates.checkForUpdateAsync();
        if (cancelled || !check.isAvailable) return;
        await Updates.fetchUpdateAsync();
        if (!cancelled) setMode((prev) => (prev === 'idle' ? 'ota-ready' : prev));
      } catch {
        // OTA failures are non-fatal.
      }
    })();

    return () => { cancelled = true; };
  }, [apiUrl, currentVersionCode]);

  const openStore = () => {
    if (info?.update_url) Linking.openURL(info.update_url).catch(() => {});
  };

  const applyOta = async () => {
    setOtaReloading(true);
    try {
      await Updates.reloadAsync();
    } catch {
      setOtaReloading(false);
    }
  };

  // ── HARD BLOCK — non-dismissible modal ──────────────────────────────
  if (mode === 'hard-block' && info) {
    return (
      <Modal visible transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard} testID="update-hard-block">
            <Ionicons name="warning" size={48} color="#ff6b6b" style={{ alignSelf: 'center' }} />
            <Text style={styles.modalTitle}>UPDATE REQUIRED</Text>
            <Text style={styles.modalSubtitle}>
              You're running an old version. Update to keep thrashing.
            </Text>
            <Text style={styles.releaseNotes}>{info.release_notes}</Text>
            <TouchableOpacity
              style={styles.primaryBtn}
              onPress={openStore}
              testID="update-hard-block-btn"
            >
              <Ionicons name="cloud-download" size={18} color="#000" />
              <Text style={styles.primaryBtnText}>OPEN PLAY STORE</Text>
            </TouchableOpacity>
            <Text style={styles.footerText}>
              v{Constants.expoConfig?.version || '?'} → v{info.latest_version_name}
            </Text>
          </View>
        </View>
      </Modal>
    );
  }

  // ── OTA UPDATE READY ────────────────────────────────────────────────
  if (mode === 'ota-ready' && !dismissed) {
    return (
      <View style={styles.banner} testID="update-ota-banner">
        <Ionicons name="sparkles" size={16} color="#000" />
        <Text style={styles.bannerText}>New stuff ready — restart to apply</Text>
        <TouchableOpacity
          style={styles.bannerBtn}
          onPress={applyOta}
          disabled={otaReloading}
          testID="update-ota-apply"
        >
          {otaReloading ? (
            <ActivityIndicator size="small" color="#000" />
          ) : (
            <Text style={styles.bannerBtnText}>RESTART</Text>
          )}
        </TouchableOpacity>
        <TouchableOpacity onPress={() => setDismissed(true)} testID="update-ota-dismiss">
          <Ionicons name="close" size={16} color="#000" />
        </TouchableOpacity>
      </View>
    );
  }

  // ── SOFT BANNER — dismissible "update available" ────────────────────
  if (mode === 'soft-banner' && info && !dismissed) {
    return (
      <TouchableOpacity
        style={styles.banner}
        onPress={openStore}
        activeOpacity={0.85}
        testID="update-soft-banner"
      >
        <Ionicons name="cloud-download" size={16} color="#000" />
        <Text style={styles.bannerText}>
          Update v{info.latest_version_name} — tap to install
        </Text>
        <TouchableOpacity
          onPress={(e) => { e.stopPropagation?.(); setDismissed(true); }}
          testID="update-soft-dismiss"
        >
          <Ionicons name="close" size={16} color="#000" />
        </TouchableOpacity>
      </TouchableOpacity>
    );
  }

  return null;
};

const styles = StyleSheet.create({
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.95)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  modalCard: {
    width: '100%',
    maxWidth: 380,
    backgroundColor: '#0d1410',
    borderRadius: 16,
    padding: 24,
    borderWidth: 2,
    borderColor: '#ff6b6b',
    gap: 10,
  },
  modalTitle: {
    color: '#ff6b6b',
    fontSize: 22,
    fontWeight: '900',
    textAlign: 'center',
    letterSpacing: 2,
    marginTop: 8,
  },
  modalSubtitle: {
    color: '#cde',
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 8,
  },
  releaseNotes: {
    color: '#9aff5a',
    fontSize: 13,
    lineHeight: 20,
    backgroundColor: 'rgba(57,255,20,0.06)',
    padding: 12,
    borderRadius: 8,
    marginBottom: 4,
  },
  primaryBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#39ff14',
    paddingVertical: 14,
    borderRadius: 10,
    marginTop: 8,
  },
  primaryBtnText: {
    color: '#000',
    fontSize: 14,
    fontWeight: '900',
    letterSpacing: 2,
  },
  footerText: {
    color: '#456',
    fontSize: 11,
    textAlign: 'center',
    marginTop: 4,
  },
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#39ff14',
    paddingVertical: 8,
    paddingHorizontal: 12,
    // Sit just below status bar; on Android the SafeAreaView in tabs handles offset.
    marginTop: Platform.OS === 'android' ? 0 : 0,
  },
  bannerText: {
    flex: 1,
    color: '#000',
    fontSize: 12,
    fontWeight: '800',
  },
  bannerBtn: {
    backgroundColor: '#000',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 4,
  },
  bannerBtnText: {
    color: '#39ff14',
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 1,
  },
});

export default UpdateBanner;

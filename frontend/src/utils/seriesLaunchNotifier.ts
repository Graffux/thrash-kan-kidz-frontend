/**
 * Local notification helper for "Notify me when a series launches".
 *
 * Why local-only?
 *   We already know the release datetime client-side (via `/api/series/list`),
 *   so a scheduled local notification is enough — no FCM, no server push, no
 *   backend cost. expo-notifications fires the notification at the OS level
 *   even if the app is closed.
 *
 * Storage:
 *   The OS notification id is persisted in AsyncStorage keyed by series so
 *   we can:
 *     1. Show the user "✓ You'll be notified" instead of the request button
 *        on subsequent visits.
 *     2. Cancel/replace the notification if the admin reschedules the series.
 */
import * as Notifications from 'expo-notifications';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

const STORAGE_PREFIX = 'series_launch_notif_v1:';

// Show banner + sound even if the app is in the foreground (default behaviour
// is to suppress). Set once at module import.
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

const storageKey = (seriesNum: number) => `${STORAGE_PREFIX}${seriesNum}`;

export async function getScheduledNotificationId(
  seriesNum: number,
): Promise<string | null> {
  return AsyncStorage.getItem(storageKey(seriesNum));
}

export async function cancelLaunchNotification(seriesNum: number): Promise<void> {
  const existing = await getScheduledNotificationId(seriesNum);
  if (existing) {
    try {
      await Notifications.cancelScheduledNotificationAsync(existing);
    } catch {
      // already fired or canceled — ignore
    }
    await AsyncStorage.removeItem(storageKey(seriesNum));
  }
}

/**
 * Schedules a local notification for the series launch.
 *
 * Returns:
 *   { ok: true } on success
 *   { ok: false, reason } on user-actionable failure (e.g. permission denied)
 *
 * Idempotent: if a notification is already queued for this series we cancel
 * it first so the user always gets exactly one ping at the latest known
 * release date.
 */
export async function scheduleLaunchNotification(args: {
  seriesNum: number;
  seriesName: string;
  description: string;
  releaseDateIso: string;
}): Promise<{ ok: true } | { ok: false; reason: string }> {
  const release = new Date(args.releaseDateIso);
  const ms = release.getTime() - Date.now();
  if (Number.isNaN(release.getTime())) {
    return { ok: false, reason: 'Invalid release date' };
  }
  if (ms <= 0) {
    return { ok: false, reason: 'Release already passed' };
  }

  // Permission check / request. expo-notifications surfaces both the iOS
  // alert prompt and the Android 13+ POST_NOTIFICATIONS permission through
  // this single call.
  const settings = await Notifications.getPermissionsAsync();
  if (!settings.granted) {
    const req = await Notifications.requestPermissionsAsync();
    if (!req.granted) {
      return { ok: false, reason: 'Notifications permission denied' };
    }
  }

  // Android requires a channel for the notification to show.
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('series-launch', {
      name: 'Series Launches',
      importance: Notifications.AndroidImportance.HIGH,
      sound: 'default',
    });
  }

  // Replace any prior scheduled notification for this series so reschedules
  // don't double-up.
  await cancelLaunchNotification(args.seriesNum);

  const id = await Notifications.scheduleNotificationAsync({
    content: {
      title: `🤘 ${args.seriesName} is LIVE`,
      body: `${args.description} just dropped — open the app and start collecting!`,
      sound: 'default',
    },
    // Date trigger: fires at the absolute moment, regardless of when the
    // user last opened the app.
    trigger: {
      type: Notifications.SchedulableTriggerInputTypes.DATE,
      date: release,
      channelId: 'series-launch',
    },
  });

  await AsyncStorage.setItem(storageKey(args.seriesNum), id);
  return { ok: true };
}

import { useAudioPlayer } from 'expo-audio';
import { useEffect, useRef, useSyncExternalStore } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Sound assets
const SOUNDS = {
  pack_open: require('../../assets/sounds/pack_open.wav'),
  card_reveal: require('../../assets/sounds/card_reveal.wav'),
  wheel_spin: require('../../assets/sounds/wheel_spin.wav'),
  prize_won: require('../../assets/sounds/prize_won.wav'),
  duplicate: require('../../assets/sounds/duplicate.wav'),
  button_tap: require('../../assets/sounds/button_tap.wav'),
  login_riff: require('../../assets/sounds/login_riff.mp3'),
  card_flip: require('../../assets/sounds/card_flip.mp3'),
  drum_roll: require('../../assets/sounds/drum_roll.mp3'),
  bag_tear: require('../../assets/sounds/bag_tear.mp3'),
  axe_impact: require('../../assets/sounds/axe_impact.mp3'),
  cash_register: require('../../assets/sounds/cash_register.mp3'),
  clinking_coins: require('../../assets/sounds/clinking_coins.mp3'),
  tab_home: require('../../assets/sounds/tab_home.mp3'),
  tab_collection: require('../../assets/sounds/tab_collection.mp3'),
  tab_trade: require('../../assets/sounds/tab_trade.mp3'),
  tab_goals: require('../../assets/sounds/tab_goals.mp3'),
  collection_bg: require('../../assets/sounds/collection_bg.mp3'),
};

export type SoundName = keyof typeof SOUNDS;

// Any sound classified as background music — toggled by the music switch.
// Everything else is a SFX.
const MUSIC_SOUNDS: SoundName[] = ['collection_bg'];

// ============================================================================
// Mute state store (persisted in AsyncStorage, reactive via useSoundSettings)
// ============================================================================

const SFX_KEY = 'tkk_sfx_enabled';
const MUSIC_KEY = 'tkk_music_enabled';

type Settings = { sfxEnabled: boolean; musicEnabled: boolean };
let settings: Settings = { sfxEnabled: true, musicEnabled: true };
const listeners = new Set<() => void>();
let hydrated = false;

function notifyListeners() {
  listeners.forEach((l) => l());
}

async function hydrate() {
  if (hydrated) return;
  hydrated = true;
  try {
    const [sfx, music] = await Promise.all([
      AsyncStorage.getItem(SFX_KEY),
      AsyncStorage.getItem(MUSIC_KEY),
    ]);
    settings = {
      sfxEnabled: sfx === null ? true : sfx === 'true',
      musicEnabled: music === null ? true : music === 'true',
    };
    notifyListeners();
  } catch (_e) {
    // keep defaults
  }
}
// Kick off hydration immediately on module load
hydrate();

export async function setSfxEnabled(enabled: boolean) {
  settings = { ...settings, sfxEnabled: enabled };
  await AsyncStorage.setItem(SFX_KEY, enabled ? 'true' : 'false');
  notifyListeners();
}

export async function setMusicEnabled(enabled: boolean) {
  settings = { ...settings, musicEnabled: enabled };
  await AsyncStorage.setItem(MUSIC_KEY, enabled ? 'true' : 'false');
  notifyListeners();
}

export function useSoundSettings(): Settings {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => settings,
    () => settings
  );
}

function isMuted(name: SoundName): boolean {
  return MUSIC_SOUNDS.includes(name)
    ? !settings.musicEnabled
    : !settings.sfxEnabled;
}

// ============================================================================
// Players
// ============================================================================

/**
 * One-shot sound player. Respects the SFX mute toggle.
 *
 * Why the seek-then-play chain: expo-audio's `seekTo()` is async. If you
 * call `play()` synchronously after it, the play often fires while the
 * player position is still at the *end* of the previous playback, so it
 * "ends immediately" = silence. Symptom: every Nth rapid replay drops out.
 * Awaiting the seek before play guarantees a clean re-trigger every time.
 */
export function useSoundPlayer(name: SoundName) {
  const player = useAudioPlayer(SOUNDS[name]);
  return {
    play: () => {
      if (isMuted(name)) return;
      try {
        const seekResult = player.seekTo(0) as unknown as
          | Promise<void>
          | undefined;
        if (seekResult && typeof seekResult.then === 'function') {
          seekResult.then(() => player.play()).catch(() => {});
        } else {
          player.play();
        }
      } catch (_e) {
        // ignore
      }
    },
  };
}

/**
 * Looping background music. Respects the music mute toggle.
 * Also reacts to the toggle mid-playback: turning music off while
 * Collection is open will pause immediately.
 */
export function useLoopingPlayer(name: SoundName) {
  const player = useAudioPlayer(SOUNDS[name]);
  const startedRef = useRef(false);
  const wantsPlayingRef = useRef(false);
  const current = useSoundSettings();

  // React to the music toggle while we're supposed to be playing
  useEffect(() => {
    if (!wantsPlayingRef.current) return;
    try {
      if (isMuted(name)) {
        player.pause();
      } else {
        player.play();
      }
    } catch (_e) {
      // ignore
    }
  }, [current.musicEnabled, name, player]);

  // Auto-stop on unmount
  useEffect(() => {
    return () => {
      try {
        player.pause();
      } catch (_e) {
        // ignore
      }
    };
  }, [player]);

  return {
    start: () => {
      wantsPlayingRef.current = true;
      if (isMuted(name)) return;
      try {
        if (!startedRef.current) {
          player.loop = true;
          player.volume = 0.5;
          startedRef.current = true;
        }
        player.seekTo(0);
        player.play();
      } catch (_e) {
        // ignore
      }
    },
    stop: () => {
      wantsPlayingRef.current = false;
      try {
        player.pause();
        player.seekTo(0);
      } catch (_e) {
        // ignore
      }
    },
  };
}

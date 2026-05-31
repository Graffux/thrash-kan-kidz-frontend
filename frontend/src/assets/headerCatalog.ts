/**
 * Single source of truth for the slime-drip raster headers.
 *
 * Every header is BUNDLED LOCALLY via `require()` — no remote URLs. This
 * is intentional: we hit repeated reports of remote-hosted header images
 * failing to render on Android (likely an interaction between expo-image
 * v3 + new architecture + flaky CDN behavior). Bundling guarantees the
 * pixels are on-device the moment the app installs.
 *
 * Each entry is a require() result (numeric module id), suitable for
 * passing directly to `<Image source={...}>` or `<ExpoImage source={...}>`.
 * NO string URI form — that's what was breaking.
 *
 * To change a header: re-export the PNG under `frontend/src/assets/headers/`
 * with the same filename and rebuild. No code edits needed.
 */
import type { ImageSourcePropType } from 'react-native';

export type ScreenHeaderKey =
  | 'home'              // "Thrash Kan Kidz" wordmark on top of the home screen
  | 'yourStats'         // "YOUR STATS" banner above the 4-up stat grid on home
  | 'moshpit'           // "MOSHPIT" banner on the Mosh Pit feed
  | 'leaderboard'       // "Leader Board" banner on the leaderboard screen
  | 'cardPack'          // "CARD PACK" banner on the Shop screen
  | 'myCollection'      // "MY COLLECTION" banner on the Collection screen
  | 'goals'             // "GOALS" banner on the Goals screen
  | 'tradeCenter';      // "TRADE CENTER" banner on the Trade screen

/* eslint-disable @typescript-eslint/no-require-imports */
export const HEADER_SOURCES: Record<ScreenHeaderKey, ImageSourcePropType> = {
  home:         require('./headers/tkk_home.png'),
  yourStats:    require('./headers/header_yourstats.png'),
  moshpit:      require('./headers/moshpit.png'),
  leaderboard:  require('./headers/leaderboard_logo.png'),
  cardPack:     require('./headers/header_cardpack.png'),
  myCollection: require('./headers/header_mycollection.png'),
  goals:        require('./headers/header_goals.png'),
  tradeCenter:  require('./headers/header_tradecenter.png'),
};
/* eslint-enable @typescript-eslint/no-require-imports */

/** Convenience accessor — `headerSource('cardPack')` */
export const headerSource = (key: ScreenHeaderKey): ImageSourcePropType =>
  HEADER_SOURCES[key];

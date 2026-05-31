/**
 * Single source of truth for the slime-drip raster headers used at the
 * top of each main screen. Centralised here so:
 *
 *   1. You can re-render any header (or all of them) and only touch
 *      ONE file in the codebase.
 *   2. The headers can never get swapped between screens again — every
 *      filename is bound to a screen key by name.
 *
 * URLs point at customer-assets.emergentagent.com so we can swap them
 * via a backend redeploy without an EAS build. If you ever want to
 * bundle one locally (instant load, no network), drop it under
 * `frontend/src/assets/headers/` and replace the entry with a
 * `require()` call — `ExpoImage`/`Image` accept either form.
 */

export type ScreenHeaderKey =
  | 'home'              // "Thrash Kan Kidz" wordmark on top of the home screen
  | 'yourStats'         // "YOUR STATS" banner above the 4-up stat grid on home
  | 'moshpit'           // "MOSHPIT" banner on the Mosh Pit feed
  | 'leaderboard'       // "Leader Board" banner on the leaderboard screen
  | 'cardPack'          // "CARD PACK" banner on the Shop screen
  | 'myCollection'      // "MY COLLECTION" banner on the Collection screen
  | 'goals'             // "GOALS" banner on the Goals screen
  | 'tradeCenter';      // "TRADE CENTER" banner on the Trade screen

export const HEADER_URLS: Record<ScreenHeaderKey, string> = {
  home:
    'https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/0lciuet8_enhanced-1776318342337.png',
  yourStats:
    'https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/xy3yb7n4_enhanced-1776904351419.png',
  moshpit:
    'https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/pqq58yoz_enhanced-1780183718094.png',
  leaderboard:
    'https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/oevsb75c_Screenshot_20260530_162245_ChatGPT.png',
  cardPack:
    'https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/zljumrlp_enhanced-1776903996438.png',
  myCollection:
    'https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/btr32loy_enhanced-1776904123985.png',
  goals:
    'https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/u4jh2a58_enhanced-1776904246547.png',
  tradeCenter:
    'https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/a7zxlvom_enhanced-1776903865079.png',
};

/** Convenience accessor — `headerUri('home')` instead of importing the dict everywhere. */
export const headerUri = (key: ScreenHeaderKey): string => HEADER_URLS[key];

/**
 * Ronch — the official Thrash Kan Kidz mascot asset registry.
 *
 * Centralizes all mascot artwork URLs in one place so we don't sprinkle
 * CDN strings across the codebase. When you add new artwork (clean
 * cutouts, additional expressions, animated GIFs, etc.), drop it here
 * and import the constant — never hardcode URLs in components.
 *
 * Expression mapping (for in-game event reactions):
 *   - HAPPY    → variant pulls, series completion
 *   - ANGRY    → duplicate pulls, errors
 *   - WIDE_EYED → epic/rare reward unlocks, "OMG" moments
 *   - TILTED    → idle / default / generic stamp
 */
export const MASCOT_NAME = 'Ronch';
export const MASCOT_TAGLINE = 'TRASHED. THRASHED. FOREVER THRASHED.';

// Full art / signature pose — used on splash + onboarding hero
export const MASCOT_SIGNATURE = 'https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/g1st4ssy_enhanced-1778699015354.jpg';

// Logo + character composite — used on splash hero
export const MASCOT_LOGO_HERO = 'https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/46t0w978_Screenshot_20260512_222521_ChatGPT.png';

// Expression headshots — point all to the character sheet for now;
// swap to clean cropped headshots once they're uploaded.
export const MASCOT_HAPPY = MASCOT_SIGNATURE;
export const MASCOT_ANGRY = MASCOT_SIGNATURE;
export const MASCOT_WIDE_EYED = MASCOT_SIGNATURE;
export const MASCOT_TILTED = MASCOT_SIGNATURE;

export const MASCOT_FOR_EVENT = (
  event: 'variant_pull' | 'series_complete' | 'duplicate' | 'rare_reveal' | 'idle'
): string => {
  switch (event) {
    case 'variant_pull':
    case 'series_complete':
      return MASCOT_HAPPY;
    case 'duplicate':
      return MASCOT_ANGRY;
    case 'rare_reveal':
      return MASCOT_WIDE_EYED;
    case 'idle':
    default:
      return MASCOT_TILTED;
  }
};

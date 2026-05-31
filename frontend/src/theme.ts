/**
 * Central design tokens for the Thrash Kan Kidz visual identity.
 *
 * Use these instead of inline color strings — gives us a single place to
 * iterate on the palette and ensures consistency across screens.
 *
 * Palette: toxic slime green + purple anarchy accents + rust warmth.
 */
export const THEME = {
  // Greens
  slime: '#39ff14',
  slimeBright: '#9aff5a',
  slimePale: '#c4ff8c',
  slimeDeep: '#0a8a02',
  // Purples
  anarchy: '#9c66cc',
  anarchyDeep: '#5a1e8a',
  anarchyGlow: '#c490e8',
  // Rust / warm
  rust: '#8c3c12',
  rustDeep: '#5a1e08',
  bone: '#f4e8c8',
  // Misc
  blood: '#ff3030',
  gold: '#ffd24a',
  // Backgrounds
  bgDark: '#0a0d0a',
  bgPanel: 'rgba(20, 25, 20, 0.85)',
  // Rarity-tinted glows for Featured Cards
  glowCommon: 'rgba(255, 255, 255, 0.15)',
  glowUncommon: 'rgba(57, 255, 20, 0.5)',
  glowRare: 'rgba(156, 102, 204, 0.6)',
  glowEpic: 'rgba(255, 210, 74, 0.7)',
  glowVariant: 'rgba(196, 144, 232, 0.65)',
};

export const FONTS = {
  /**
   * Death-metal display font slot. Was BraverGrave (.otf/.ttf) but
   * Android dropped it inconsistently in production, so as of v124
   * we ship `undefined` here and let everything fall back to system
   * bold — which is exactly what users were already seeing on broken
   * builds. Raster headers (see `src/assets/headerCatalog.ts`) cover
   * the look-and-feel for every major screen title.
   */
  death: undefined as string | undefined,
  /** Removed alongside `death` — kept as a key for type-stability. */
  critica: undefined as string | undefined,
  /**
   * Legacy "metal" font — still used for smaller accents (rank labels,
   * the small "Welcome" greeting) where Braver Grave would be too aggressive.
   * Keeping it loaded so existing references continue to render.
   */
  metal: 'MetalMania-Regular',
  /** System fallback for body copy / inputs (better legibility) */
  body: undefined as string | undefined,
};

/** Get the glow color for a card rarity. */
export const rarityGlow = (rarity?: string): string => {
  switch ((rarity || '').toLowerCase()) {
    case 'epic': return THEME.glowEpic;
    case 'rare': return THEME.glowRare;
    case 'variant': return THEME.glowVariant;
    case 'uncommon': return THEME.glowUncommon;
    default: return THEME.glowCommon;
  }
};

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
   * Primary death-metal display font for the BIG headers/titles
   * (section titles, big usernames, pack names). Jagged, dripping,
   * legitimately death-metal — sourced from Braver Grave (.otf).
   *
   * MUST match the font's internal PostScript name (nameID 6).
   * Android production builds silently fall back to the system font
   * if the key doesn't match exactly.
   */
  death: 'BraverGrave',
  /**
   * Alternate horror-style display font (Critica). Use sparingly for
   * variant titles or special accents where a more chiseled look is wanted.
   */
  critica: 'Critica',
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

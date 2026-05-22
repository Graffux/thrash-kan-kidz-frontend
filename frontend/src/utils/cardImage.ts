/**
 * Helpers for fetching card images at the right size.
 *
 * The backend `/api/cards/{id}/thumb?w={px}` endpoint serves JPEG thumbnails
 * (60-100 KB) instead of the 3-5 MB originals. Use thumbnails everywhere a
 * card is rendered smaller than ~600px — grids, picker modals, leaderboard
 * rows, profile featured slots, etc. Only fall through to the original full
 * URL for pack-reveal / zoomed-card screens where detail matters.
 */

// Hardcoded to match the single source of truth in AppContext.tsx so the
// thumb URL is generated even when this helper is called outside React
// (e.g. inside a non-hook function). Update both places if the API host
// ever moves.
const API_BASE = 'https://thrash-kan-kidz-api.onrender.com';

export interface CardImageSource {
  id?: string;
  front_image_url?: string;
}

/**
 * Build a thumbnail URL for a card. Falls back to the full image URL if the
 * card has no id (e.g. legacy/synthetic data) so existing code keeps working.
 *
 * @param card Object that has at least `{ id, front_image_url }`
 * @param width Target rendered width in CSS pixels. Pass screenWidth/columns.
 */
export function cardThumb(card: CardImageSource | undefined | null, width = 360): string {
  if (!card) return '';
  if (!card.id) return card.front_image_url || '';
  // Snap to common widths so the LRU on the backend stays effective.
  // Otherwise width=359 vs 360 would create separate cache entries.
  const w = width <= 160 ? 160 : width <= 240 ? 240 : width <= 360 ? 360 : 540;
  return `${API_BASE}/api/cards/${card.id}/thumb?w=${w}`;
}

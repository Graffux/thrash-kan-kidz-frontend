/**
 * Tiny helpers for the daily-login coin boost (a.k.a. "VIP Supporter").
 *
 * Backend awards the boost on ANY coin pack purchase and writes
 * `coin_boost_expires_at` (ISO string) to the user document.
 * While the timestamp is in the future:
 *   - daily login bonus is 25 coins (vs 10 base)
 *   - the user shows up with a "VIP" chip in Mosh Pit
 *
 * We compute days-remaining on the client so the home chip and shop
 * renewal prompt feel live without polling the server.
 */

/** Days left in the active boost window. 0 → expired or never bought. */
export const boostDaysLeft = (expiresAtIso?: string | null): number => {
  if (!expiresAtIso) return 0;
  const expiry = new Date(expiresAtIso).getTime();
  if (Number.isNaN(expiry)) return 0;
  const ms = expiry - Date.now();
  if (ms <= 0) return 0;
  return Math.max(1, Math.ceil(ms / (1000 * 60 * 60 * 24)));
};

/** True while the user is currently inside the 30-day window. */
export const isBoostActive = (expiresAtIso?: string | null): boolean =>
  boostDaysLeft(expiresAtIso) > 0;

/**
 * Returns one of:
 *   - "expiring" → boost active but ≤ 7 days left (show renewal nudge)
 *   - "active"   → boost active, plenty of time left
 *   - "inactive" → no boost / expired (shop can show a discovery prompt)
 */
export const boostState = (
  expiresAtIso?: string | null,
): 'active' | 'expiring' | 'inactive' => {
  const days = boostDaysLeft(expiresAtIso);
  if (days === 0) return 'inactive';
  if (days <= 7) return 'expiring';
  return 'active';
};

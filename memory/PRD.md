# Thrash Kan Kidz — Product Requirements

## Original problem statement
A mobile card-collecting game featuring thrash/death metal parody cards
(Garbage Pail Kids style). Built with React Native (Expo SDK 54) +
FastAPI + MongoDB.

## Status
- **Live on Google Play Production**.
- Current live build on devices: **v1.20.0 / versionCode 111**.
- Next build prepared in repo: **v1.20.0 / versionCode 114**.
- **567 cards seeded**, Series 1–7 fully released.
- Backend hosted on Render (`https://thrash-kan-kidz-api.onrender.com`).
- MongoDB Atlas (`thrash_kan_kidz` DB).
- Custom domain `thrashkankidz.com` via Cloudflare Pages.

## Architecture
```
/app
├── backend
│   ├── server.py                       # Monolithic core (~4040 lines, still to split)
│   ├── routers/
│   │   ├── cards.py                    # /api/cards/{id}/thumb (Pillow resize)
│   │   ├── mosh.py                     # Feed + comment likes
│   │   └── leaderboard.py
│   ├── data/{cards_data,goals_data,ranks,badges}.py
│   └── tests/
└── frontend
    ├── app.json                        # v1.20.0, versionCode 113, READ_MEDIA_IMAGES blocked
    ├── assets/fonts/                   # Local TTF/OTF loaded via useFonts (NO expo-font plugin)
    │   ├── MetalMania-Regular.ttf      # FONTS.metal — small accents only
    │   ├── BraverGrave.otf             # FONTS.death — primary jagged death-metal display
    │   └── Critica.otf                 # FONTS.critica — available, not yet placed
    ├── app/
    │   ├── _layout.tsx                 # useFonts + bottom-tab spacing
    │   ├── index.tsx                   # Home (Welcome + big username use FONTS)
    │   ├── shop.tsx                    # Pack opening + Free Pack badge/redeem
    │   ├── mosh.tsx                    # Feed (MIME fix on share)
    │   └── profile.tsx                 # Username uses FONTS.death
    └── src/
        ├── theme.ts                    # FONTS.{death,critica,metal,body}
        ├── components/
        │   ├── CardPickerModal.tsx     # Mini-game (free-pack prize redeem)
        │   ├── MoshComments.tsx        # Comment 💀 reactions
        │   ├── GrungeBackground.tsx    # Ronch peek (asset needs eyes)
        │   ├── SplatTitle.tsx          # Section titles → FONTS.death
        │   └── FeaturedCards.tsx
        └── utils/cardImage.ts          # cardThumb(card, w) helper
```

## Last session changes (2026-05-28)

### Code changes (in `/app`, pushed to GitHub iff user clicks Save to GitHub)
- **Death metal font integration** — Braver Grave (`.otf`) + Critica (`.otf`)
  loaded via local `useFonts` (PostScript names verified with `fontTools`).
  `FONTS.death` (Braver Grave) now applied to:
   - `SplatTitle` (all section headers)
   - Home screen big username (28 px)
   - Profile page username (30 px)
   - Shop pack card name (18 px)
  `FONTS.metal` (Metal Mania) retained for small accents (Welcome, rank crest).
- **Mosh Pit image upload fixes** — when sharing a pull from the pack-reveal
  modal OR attaching a card from the in-Mosh picker, we now base64 the
  backend thumbnail (`cardThumb(card, 540)`, ~80 KB) instead of the original
  3–5 MB CDN image, which was tripping the backend's 1 MB cap.
- **Free Pack visibility** — added a tappable toxic-green pill in the shop
  header showing `freePacks` count. Tapping triggers a confirm + opens a free
  pack from the currently-selected series, reusing the existing pack-reveal
  animation. Backend already had `/redeem-free-pack`; the UI just wasn't
  exposing it, making prizes from the card-picker mini-game appear lost.
  `handleOpenPack({useFreePack:true})` calls `/redeem-free-pack`; otherwise
  the regular `/spin` flow runs unchanged.
- **Admin streak endpoint** — `POST /api/admin/set-streak/{user_id}` now
  also calls `check_and_update_goals(user_id, "daily_login", streak)` so the
  Goals tab reflects restored streaks.
- **`app.json` versionCode bumped 111 → 113.**

## Session 2026-05-30 (batch fixes for build v121)

### Code changes
- **Card art corrections** — `card_martin_wankyier` and `card_daring_travis`
  front_image_url pointed to swapped/wrong artwork (old job_d9b7563a URLs).
  Updated `CARD_IMAGE_URLS["martin_wankyier"]` and `["daring_travis"]` in
  `backend/data/cards_data.py` to the correct customer-asset URLs supplied
  by the user. Backend `sync_card_assets` startup hook auto-pushed both
  rows to MongoDB on reload (confirmed via curl).
- **New "Thrash Kan Kidz" header** — replaced the SVG `DrippingLogo` with
  a raster Image component pointing to the new slime-drip metal logo
  artwork at `frontend/src/assets/headers/tkk_logo.jpg` (900×900, 145 KB
  JPG). All existing call-sites continue to work (auth screen + home).
- **New Leaderboard header + privacy** — `frontend/app/leaderboard.tsx`
  now renders `headers/leaderboard_logo.jpg` (900×709, 145 KB JPG)
  instead of the plain text title. Removed `COINS` from the public
  metric tabs and stripped the `coins` field from the `Row` interface +
  `metricLabel`. Backend still accepts `metric=coins` for older clients;
  the UI just no longer surfaces it.
- **versionCode 120 → 121** in `app.json`.

### Asset notes
- Source PNG for the leaderboard header had a corrupt `eXIf` chunk that
  failed PIL parsing. We stripped the chunk, then re-encoded as JPEG to
  avoid future AAPT2 build failures on Android.

## Session 2026-05-30 (continued — VIP boost + Series 8 banner) — versionCode 122

### Daily Login Bonus Multiplier (P0, monetization)
- **`User.coin_boost_expires_at`** added (Optional[datetime]). Activated
  by ANY coin pack purchase, lasts 30 days. Each new purchase RESETS the
  expiry to now+30d (does NOT stack — per Q2b spec).
- **`_is_vip_active(user)`** helper module-level in `server.py` —
  computes VIP status from `coin_boost_expires_at`. Handles both
  datetime and ISO string formats.
- **`_activate_coin_boost(user_id)`** helper — wired into ALL THREE
  fulfillment paths:
  - `/api/users/{user_id}/verify-purchase` (Google Play live path)
  - `/api/checkout/status/{session_id}` (Stripe success poll)
  - `/api/webhook/stripe` (Stripe webhook)
- **Daily login claim** — `bonus_coins` now 25 when boost active else 10.
  Response includes `vip_boost_active` and `vip_boost_expires_at`.
  ⚠️ NOTE: pre-existing code had `bonus_coins = 50`. User specified
  10 (base) / 25 (boost) literally so we honored that. If user prefers
  to preserve the old economy and just multiply, change the constants
  in `claim_daily_login`.

### VIP Supporter tag (P0, social proof)
- **`/api/users/{user_id}`** and **`/api/users/username/{username}`**
  now return `is_vip_supporter` boolean (computed, not stored).
- **`/api/mosh/feed`**, **`/api/mosh/posts/{id}`**,
  **`/api/mosh/posts/{id}/comments`** now decorate each post/comment
  author with `is_vip_supporter`. Single batched `db.users.find` per
  feed render, no per-row queries.
- **Frontend chip**: amber star pill rendered next to author name on
  Home, Mosh feed posts, and Mosh comments when `is_vip_supporter`.

### Series 8: Slam Edition announcement (P0, hype)
- **Home banner** — amber-bordered card under the welcome strip,
  always visible.
- **Mosh Pit pinned system post** — backend `/api/mosh/feed` injects a
  synthetic `system_series8_announcement` post at index 0. Frontend
  renders it as a no-interaction broadcast card (no react/comment/
  delete buttons) with an "OFFICIAL" megaphone badge.

### versionCode 121 → 122
- Ships VIP boost + announcements on top of the previous batch (cards,
  headers, leaderboard).

### Verified end-to-end
- Direct MongoDB tests pass: VIP flag flips correctly on set, unset,
  and past-expiry.
- `/api/mosh/feed` returns the pinned announcement at index 0.
- `/api/users/username/Graffux` returns `is_vip_supporter=True` when a
  future `coin_boost_expires_at` is set (boost set on Graffux for the
  user's in-app verification — expires ~2026-06-29).

## Session 2026-05-30 (continued — Founding Thrasher badge)

### New Founders' badge (tester rewards)
- **`founding_thrasher`** added to `data/badges.py` with the user-supplied
  spiked-shield artwork.
- New condition type **`COND_GRANTED`** — non-auto-earnable, evaluated
  against `users.granted_badges[]`. Future-proofs admin/contest awards
  beyond just founders.
- **`_evaluate_badge` updated** to handle `COND_GRANTED` (returns True
  iff `badge.id in user.granted_badges`).
- **Database backfill**: ran `$addToSet` on all 57 current users so every
  tester sees the badge immediately. Idempotent on re-run.

### Verified
- `/api/badges` lists `founding_thrasher` (18 total badges).
- `/api/users/{Graffux}/badges` → `founding_thrasher.earned = True`.

## Session 2026-05-30 (continued — Daily Boost UX)

### Home countdown chip
- VIP chip on home expanded from `VIP` → `VIP · 28d` (or whatever the
  current `boostDaysLeft(user.coin_boost_expires_at)` returns).
- Same chip auto-disappears the moment `coin_boost_expires_at` passes —
  no extra plumbing, falls out of the date math.

### Shop status card (new)
- One inline state card lives between the shop header and the series
  toggle. Three visual variants:
  - `active`  (>7d left) → amber chip "VIP Boost active · Nd left · 25 coins/day"
  - `expiring` (≤7d left) → amber bordered tappable card "Boost expires in N days — buy any pack to refresh" → opens BuyCoinsModal.
  - `inactive` (no boost / expired) → green bordered tappable card "Unlock the VIP Daily Boost — buy any coin pack" → opens BuyCoinsModal.

### Shared util
- New `frontend/src/utils/vipBoost.ts` exports `boostDaysLeft`,
  `isBoostActive`, `boostState`. Re-used by Home + Shop. No new API
  surface, all derived from `user.coin_boost_expires_at`.

### Frontend User type
- `is_vip_supporter?` and `coin_boost_expires_at?` added to
  `AppContext.User` so the rest of the app can read both directly.

### versionCode stays 122
- All boost UX ships in the same EAS build as the VIP/Series-8/header
  batch — no extra build needed.

## Session 2026-05-30 (continued — Leaderboard crash fix + header rasters → v123)

### Critical fix: Leaderboard "Property 'Image' doesn't exist"
- `app/leaderboard.tsx` used `<Image>` in the redesigned header but I
  forgot to add it to the `react-native` import block in the previous
  session. Crash reproduced from user screenshot. Added `Image` to the
  import statement. **Trivially testable in v123 build.**

### New raster headers (the user is giving up on custom fonts)
- `assets/headers/tkk_home.jpg` (137 KB, 900×471) — the trash-can /
  rusted-metal / slime-dripping "Thrash Kan Kidz" wordmark.
- `assets/headers/moshpit.jpg` (165 KB, 900×647) — matching
  "MOSHPIT" wordmark.
- `DrippingLogo` now sources `tkk_home.jpg` (was `tkk_logo.jpg`).
  Default dimensions bumped 260×110 → 280×146 to suit the new artwork's
  aspect ratio (~1.91:1).
- Mosh Pit screen top-bar replaces the text `<Text>MOSH PIT</Text>`
  title with the raster image (200×70).
- Both PNGs source were sanitized (eXIf/iCCP/iTXt chunks stripped)
  before re-encoding to JPEG-on-black to dodge AAPT2 PNG-validation
  failures we hit on previous builds.

### versionCode 122 → 123
- Forces a fresh build so the crash fix actually ships.

### Open issue (FYI)
- User reported "all other headers were gone" in v121 — i.e. shop,
  trade, profile etc that still rely on the Critica / BraverGrave TTF
  fonts. We did NOT touch those in this round (user only asked for
  Home + Mosh Pit). If those screens still look broken in v123, the
  remediation is to commission matching raster headers for each.

### Production database fixes (already live)
- Graffux daily_login_streak set to **52** (was 51 from auto-tick).
- Dripping daily_login_streak set to **41** (was 1; restored via admin endpoint;
  `last_login_date` = yesterday so next login increments to 42).
- Both users' `daily_login` goal progress updated directly in MongoDB
  (`goal_daily_login_30` → completed; `goal_daily_login_60` → 52/60 + 41/60).

## Open issues
- **Save to GitHub failing for FRONTEND repo** — user reported clicking 3+
  times pushed to `thrash-kan-kidz-backend` (the "Last used" repo) but
  `thrash-kan-kidz-frontend` was never updated. User now knows to select
  the frontend repo from the dropdown and merge via PR (branch + merge,
  NOT force-push, to keep `main` aligned with the live build).
- **Ronch peek asset** — `frontend/assets/decor/ronch_peek.png` does NOT
  contain Ronch's eyes (image shows top of head + dreadlocks + hands only).
  Needs a new image-generated asset with eyes/forehead prominently visible.
- **Card picker reward "not distributed" perception** — root cause was the
  missing free-pack UI in shop; fix landed this session. Reward DID land
  in DB, user just couldn't see it.

## Prioritized backlog

### P0 — pending user action
- User clicks **Save to GitHub** for BOTH `thrash-kan-kidz-frontend` AND
  `thrash-kan-kidz-backend`, merges via PR, then triggers ONE consolidated
  EAS build for `versionCode 121`. All batched fixes (.ttf fonts, tab
  spacing, ronch cleanup, audio WAVs, scratch-cover endpoint, free pack
  UI, rank badge swap, Martin/Travis art, new home + leaderboard
  headers, coins removed from leaderboard) ship together.

### P1 (after build lands)
- Generate new `ronch_peek.png` asset with eyes visible (image generation
  via Gemini Nano Banana / GPT Image 1 — emergent LLM key works for both).
- Decide where to use `FONTS.critica` (alternate horror display) — possibly
  swap for the brand title on splash, or for Crypt-Card titles.
- Audit composite-score leaderboard rendering after backend redeploy.

### P2
- **Crypt Cards** — hidden rare cards (monetization upgrade).
- **Coin-Purchase Bonus Cards** — guaranteed drops based on IAP tier.

### P3
- Refactor monolithic `server.py` into `/app/backend/routers/` (users,
  trades, shop, spin, payments, goals).
- iOS App Store release.

## API surface (recent additions)
- `GET  /api/cards/{id}/thumb?w={px}` — Pillow-resized JPEG thumbnail.
- `POST /api/mosh/comments/{id}/react` — toggle 💀 reaction on a comment.
- `POST /api/admin/set-streak/{user_id}` — restore streak + sync goal progress.
- `POST /api/users/{id}/redeem-free-pack` — redeem one free pack into series.

## Test credentials
See `/app/memory/test_credentials.md`.

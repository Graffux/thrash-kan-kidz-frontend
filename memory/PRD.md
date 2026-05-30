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

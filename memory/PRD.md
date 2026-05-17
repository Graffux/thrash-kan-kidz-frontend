# Thrash Kan Kidz — Product Requirements

## Original problem statement
A mobile card-collecting game featuring thrash/death metal parody cards (Garbage
Pail Kids style). Built with React Native (Expo SDK 54) + FastAPI + MongoDB.

## Status
- **Live on Google Play Production** (v80 series shipping; v82 prepared and queued for next push).
- Custom domain `thrashkankidz.com` mapped via Porkbun → Cloudflare Pages.
- 567 cards seeded; Series 1–7 FULLY seeded. Series 1–6 released, Series 7 "Grind Edition" unlocks **2026-05-17**.
- CI/CD: GitHub Actions auto-deploys backend to Render and builds Android `.aab` for free via `eas build --local` on the GitHub runner.

## Architecture
```
/app
├── backend
│   ├── server.py                # Core API + auth + pack/spin/trade logic
│   ├── series_config.py         # Series release schedule
│   ├── routers/{cards,diagnostics,static_pages,feedback,friends}.py
│   ├── tests/test_ranks.py      # Pytest for rank computation
│   └── data
│       ├── cards_data.py        # Master catalog (CARD_IMAGE_URLS, backs, variants)
│       ├── goals_data.py        # Goals (rewards system)
│       ├── ranks.py             # 9-rank ladder, compute_user_rank() (NEW)
│       └── badges.py            # 15 badges with server-evaluated conditions (NEW)
└── frontend
    ├── app.json / eas.json      # versionCode 82, version 1.8.9, newArchEnabled
    ├── app/{index,collection,shop,trade,profile,goals}.tsx
    └── src
        ├── components
        │   ├── ScratchCard.tsx              # SVG-mask scratch-off
        │   ├── RankCrest.tsx                # Rank badge image (sm/md/lg) (NEW)
        │   ├── BadgeCabinet.tsx             # Profile achievements grid (NEW)
        │   ├── MetalButton, OozeProgressBar
        │   ├── MascotSplash, MascotStamp, MascotEmptyState, RonchTrashTalk
        │   └── PackRevealWrapper, CoinGainPop
        └── context/AppContext.tsx
```

## What's been implemented

### 2026-05-15 (this session) — Ranks + Badges + Build Fixes
- **Player rank system** (`data/ranks.py` + `<RankCrest>`):
  - 9 ranks: Poser → Roadie → Fist Banger → Tape Trader → Headbanger → Mosher → Pit Dweller → **Stage Diver** (S7) → Thrash Maniac (S8, future)
  - Unlock = N series cleared (base cards). Server-authoritative via `compute_user_rank()`.
  - `GET /api/ranks` lists ladder; `rank` field attached to `/users/{id}`, `/users/search`, `/users/recently-active`.
  - Crest UI: small badge next to username (Home + Trade), large crest with label on Profile.
  - 6/6 pytest cases pass.
- **Badge Cabinet** (`data/badges.py` + `<BadgeCabinet>`):
  - 15 badges defined with 9 condition types (login streak, trades count, variants owned, series base complete, friend count, total spent, own specific card, etc.).
  - `GET /api/badges` (catalog), `GET /api/users/{id}/badges` (per-user state).
  - Visual-only — no rewards (Goals keep their rewards, Badges layer added on top).
  - Renders on Profile page with Ionicons fallback until custom art is added (`image_url` field on each badge ready for swap).
- **Bug fix:** Tranquilized Adam back image was showing Sadam Tranquilli's front (URL collision in `CARD_BACK_IMAGE_URLS`). Replaced with correct Butt Feast artwork.
- **Build unblock:** `app.json` updated with `newArchEnabled: true` (root + `expo-build-properties` for android/ios) — required for `react-native-reanimated` v4. Bumped to v1.8.9 / versionCode 82.

### Earlier in this fork
- Series 7 fully seeded (all 8 bands + Alien Dubin reward).
- Scratch-off variant reveal (`react-native-svg`) shipped on pack-opens, spins, trade-ins.
- Mascot integration: Thrash Man Ronch via MascotSplash, MascotEmptyState, RonchTrashTalk easter eggs.
- Visual polish: MetalButton, OozeProgressBar, PackRevealWrapper, CoinGainPop.
- CI/CD pipelines: `deploy-render.yml` (backend auto-deploy on push to `backend/**`), `build-android.yml` (free EAS Android builds on GitHub runner using `eas build --local`).
- FOREGROUND_SERVICE permissions stripped via `remove-permissions.js` plugin.

### Pre-fork
- Live on Google Play v77.
- Custom domain + Cloudflare landing page deployed.
- Mini-games (Daily Wheel, Card Picker) on Home screen.
- Scheduled series releases via `series_config.py`.
- Privacy Policy + Delete Account pages on Render.

## API surface (selected)
- `GET /api/ranks` — rank ladder catalog
- `GET /api/badges` — badge catalog
- `GET /api/users/{id}` — now includes `rank` field
- `GET /api/users/{id}/badges` — `{ badges: [...with earned flag], earned_count }`
- `GET /api/users/search`, `/users/recently-active` — now include `rank`
- `GET /api/cards` — variant cards include `scratch_cover_url` when registered

## Prioritized backlog
### P0
- **Push pending commits** (user is away from desktop): ranks system, badges system, Tranquilized Adam back fix, app.json newArch unblock
- Verify GitHub Action `.aab` build succeeds with new arch enabled
- Verify Series 7 reward unlock logic (rarity check) still works

### P1
- Upload custom badge artwork — drop URLs into `image_url` field per badge in `data/badges.py`
- Build & upload v82 AAB to Play Console once GH Actions completes
- Swap app icon to Ronch mascot face (requires new build)

### P2
- Landing page upgrades on Cloudflare Pages: screenshots, card grid, email signup
- Refactor `server.py` into more `/routers/` (users, trades, shop, spin, payments, goals)
- Upload remaining 28 variant scratch covers

### P3
- iOS App Store release (Apple Developer Program enrollment + StoreKit rebuild)

## Test credentials
See `/app/memory/test_credentials.md`.

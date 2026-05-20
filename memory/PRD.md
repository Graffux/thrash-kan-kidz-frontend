# Thrash Kan Kidz — Product Requirements

## Original problem statement
A mobile card-collecting game featuring thrash/death metal parody cards (Garbage
Pail Kids style). Built with React Native (Expo SDK 54) + FastAPI + MongoDB.

## Status
- **Live on Google Play Production**; current prepared build is v1.9.0 / versionCode 84.
- Custom domain `thrashkankidz.com` mapped via Porkbun → Cloudflare Pages.
- **567 cards seeded**. Series 1–7 FULLY seeded. Series 7 "Grind Edition" unlocked **2026-05-17**.
- CI/CD: GitHub Actions auto-deploys backend to Render and builds Android `.aab` for free via `eas build --local` on the GitHub runner.

## Architecture
```
/app
├── backend
│   ├── server.py                # Core API + auth + pack/spin/trade logic
│   ├── series_config.py         # Series release schedule + rare rewards
│   ├── routers/cards.py         # /api/cards (cap raised 500→2000)
│   ├── tests/test_ranks.py
│   └── data
│       ├── cards_data.py        # 567-card catalog
│       ├── goals_data.py        # Goals (rewards system)
│       ├── ranks.py             # 9-rank ladder
│       └── badges.py            # 15 badges
└── frontend
    ├── app.json                 # version 1.9.0, versionCode 84, newArchEnabled
    └── src/components
        ├── RankCrest.tsx, BadgeCabinet.tsx, ScratchCard.tsx
        └── MetalButton, OozeProgressBar, Mascot* etc.
```

## What's been implemented

### Visual Overhaul — Batch 3 Final Aesthetic Polish (2026-05-20)
- `MetalMania` font wired in via `@expo-google-fonts/metal-mania@0.4.1` — `useFonts`
  hook in `_layout.tsx` blocks splash until font loads (no system-font flash on
  first render)
- `theme.ts` central design tokens (toxic slime + anarchy purple + rust palette)
- `<SplatTitle>` paint-splat section header with drip details, reads `FONTS.metal`
- `<ToxicBar>` slime-tube progress bar with gradient fill, bubbles, highlight stripe
- `<SlimeBubbles>` ambient looping animated particles (RN Animated, no Reanimated dep)
- `<GrungeBackground>` extended with rust texture overlay + Ronch peek silhouette
  + SlimeBubbles. Removed deprecated `pointerEvents` Image prop.
- Custom Ronch peek + rust texture art assets generated via Nano Banana

### Visual Overhaul — Batch 1 (2026-05-19)
- `featured_card_ids: List[str]` added to User model (max 5, owned-only)
- `PUT /api/users/{id}/featured-cards` endpoint validates ownership + dedupes
- `<GrungeBackground>` shared wrapper (dark base + slime vignette + rust corners
  + noise overlay) — applied to Home & Profile screens
- `<FeaturedCards>` 5-slot showcase on Profile with picker modal (own-only)
- `<RippableDailyPack>` drag-to-tear daily bonus on Home (reuses SVG mask tech
  from `<ScratchCard>` — no new image assets needed)
- Bottom nav redesigned: rusted-metal plates per tab, Ionicons (skull/flame/
  flash/swap/person-circle), animated slime drip on the active tab only
- pytest `tests/test_featured_cards.py` (5 integration tests, all passing)

## What's been implemented (previous session: 2026-05-17)

### Series 7 Grind Edition — fully shipped
- All 8 bands seeded with 2 base + 8 variants each = 80 cards
  - Napalm Breath, Cheese Grater Mutilation, Anel Cant, Foreseen Terror,
    Snasum, Minimal Noise Horror, Brutal Lies, Horrorizer
- Alien Dubin epic reward card seeded with proper `series: 7` field and correct
  front/back URLs (front: `i4e0c7o8_...`, back: `vu8xlmum_...`)
- Series 7 cover image wired into shop's series toggle
- `SERIES_CONFIG[7].rare_reward = "card_alien_dubin"` — series-completion now
  auto-grants the epic reward (was silently `None`)

### Player rank + badge systems (earlier this session)
- 9-rank ladder Poser → Thrash Maniac (Stage Diver at S7, Thrash Maniac future S8)
- 15-badge cabinet on profile (server-evaluated conditions)
- Crests shown in home header, profile, trade screen

### Bugs fixed this session
- **`/api/cards` 500 limit** — silently truncating responses. Raised to 2000.
- **Tranquilized Adam back image** swapped to Butt Feast artwork (was Sadam front)
- **Alien Dubin front/back** swapped (correct orientations now)
- **Series 7 variant rarity** — 32 cards were tagged `rarity:"common"`, now `"variant"`
- **Meth Putnam + Shane Embryo rarity** — overcorrected to `"variant"`, restored to `"common"`
- **Epic reward unlock query** — was only matching `rarity:"rare"`. Now also matches
  `rarity:"epic"` so Sean Kill-Again, Martin Generic Ain't, Nicklebag Darrell,
  and Alien Dubin actually unlock when card-count threshold is met. Backfill at
  startup retroactively granted 30 unlocks.
- **Series 7 reward backfill** — startup script now grants Alien Dubin to any
  user who already owns all 16 S7 base cards. Granted retroactively to 2 users.
- **Sync function** now propagates `rarity` and `series` changes from
  cards_data.py → MongoDB (previously only URLs + descriptions synced)

### App config updates
- `version: 1.9.0`, `versionCode: 84`
- `newArchEnabled: true` (required for Reanimated v4)
- `expo-build-properties` plugin with android/ios newArch flags

## API surface (selected)
- `GET /api/cards` — returns all released-series cards (cap 2000)
- `GET /api/ranks`, `GET /api/badges` — catalogs
- `GET /api/users/{id}` — includes `rank` field
- `GET /api/users/{id}/badges` — per-user earned state
- `POST /api/users/{id}/check-series-completion/{series}` — grants reward on completion

## Prioritized backlog
### P0
- **Push backend + frontend repos** — backend has Series 7 reward fix + image
  swap + multiple critical bug fixes; frontend has S7 cover image + rank/badge
  UI + versionCode 84 ready to build
- Build & upload v84 AAB to Play Console after frontend push

### P1
- Upload custom badge artwork (drop URLs into `image_url` field per badge)
- Swap app icon to Ronch mascot face (requires new build)
- Audit if "Series 7 Reward Revealed" celebration triggers properly for users
  who hit completion organically (not via backfill)

### P2
- Landing page upgrades on Cloudflare Pages: screenshots, card grid, email signup
- Refactor `server.py` into more `/routers/` (users, trades, shop, spin, payments, goals)
- Series 7 variant scratch covers (already present for blacklight/chrome/digital/melted)

### P3
- iOS App Store release

## Test credentials
See `/app/memory/test_credentials.md`.

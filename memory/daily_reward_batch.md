# Daily Reward Cards — Batch Upload Queue (Jun 2026)

User uploaded 9 new daily-reward cards that share a **universal back** (back image upload pending — will land in a follow-up message).

All cards: `rarity: "rare"`, `is_daily_reward: True`, `available: False`, `series: 8`, no `card_type` field, no variants. Each gets its own `front_image_url`; all 9 reuse the same `back_image_url` once user uploads the universal back.

## Card list (in upload order)

| # | Display Name | Slug | Notes / Band hint |
|---|---|---|---|
| 1 | Paul Bawl Off | `paul_bawl_off` | Phil Anselmo parody (Pantera), crying with megaphone, Exodus vest |
| 2 | Chum Araya | `chum_araya` | Tom Araya parody (Slayer), bass in bucket of chum |
| 3 | Musty Dave | `musty_dave` | Dave Mustaine parody (Megadeth), moldy hair |
| 4 | Dave's Mustang | `daves_mustang` | Mustaine + green Mustang car parody |
| 5 | Ronchy | `ronchy` | Death Metal Edition — vomit/skulls, "Pinball Moose" shirt |
| 6 | Tank Mullen | `tank_mullen` | Death Metal Edition — shirtless big guy eating burger |
| 7 | Heave Tucker | `heave_tucker` | Death Metal Edition — bassist heaving green vomit |
| 8 | George Porkgrinder | `george_porkgrinder` | Death Metal — George Fisher parody, Cannibal Corpse shirt |
| 9 | Chunk Schuldiner | `chunk_schuldiner` | Death Metal — Chuck Schuldiner parody, eating intestines |

## Implementation steps for next session

1. **Wait for universal back image upload** from user.
2. Call `get_assets_tool` and identify the 10 newest assets (9 fronts + 1 universal back).
3. Add 9 entries to `CARD_IMAGE_URLS` in `/app/backend/data/cards_data.py` using slugs above.
4. Add **one** universal back URL: `"daily_reward_universal_back"` in `CARD_BACK_IMAGE_URLS`.
5. Add 9 INITIAL_CARDS entries (template from `card_chris_pervalicious` — same shape). All 9 use `CARD_BACK_IMAGE_URLS["daily_reward_universal_back"]` for their `back_image_url`.
6. Force-insert into MongoDB (seeder skips because DB count > INITIAL_CARDS count) via the same `db.cards.insert_one(c)` pattern used for Chris/I-Gore.
7. Extend `DAILY_REWARD_BY_DATE` in `/app/backend/routers/daily_challenges.py` — assign each card to a future UTC date (one per day starting 2026-06-21).

## Suggested rotation order

```python
DAILY_REWARD_BY_DATE = {
    "2026-06-19": "card_i_gore_cavahorror",       # today
    "2026-06-20": "card_chris_pervalicious",      # tomorrow
    "2026-06-21": "card_paul_bawl_off",
    "2026-06-22": "card_chum_araya",
    "2026-06-23": "card_musty_dave",
    "2026-06-24": "card_daves_mustang",
    "2026-06-25": "card_ronchy",
    "2026-06-26": "card_tank_mullen",
    "2026-06-27": "card_heave_tucker",
    "2026-06-28": "card_george_porkgrinder",
    "2026-06-29": "card_chunk_schuldiner",
}
```

That gives ~11 days of unique daily reward cards locked in.

## Existing pending URL swaps (carry-over)

1. I-Gore Cavahorror front (`TODO_URL_i_gore_cavahorror_front`)
2. I-Gore Cavahorror back (`TODO_URL_i_gore_cavahorror_back`)
3. Chris Pervalicious front (`TODO_URL_chris_pervalicious_front`)
4. Chris Pervalicious back (`TODO_URL_chris_pervalicious_back`)
5. Series 8 Master badge (`TODO_URL_series_8_master_badge`)
6. Series 9 Master badge (`TODO_URL_series_9_master_badge`)

Note: once the universal back lands, swap #2 + #4 above to point at the same universal back URL too (so I-Gore and Chris also use the universal back going forward — consistent UX).

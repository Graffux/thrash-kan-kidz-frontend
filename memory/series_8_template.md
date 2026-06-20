# Series 8 — Slam Edition: INITIAL_CARDS Template

Mirrors the exact Series 7 / Grind Edition pattern. Total when complete:
- 16 base cards (2 per band × 8 bands)
- 64 variant cards (4 flavors × 16 bases)
- 1 epic reward (Crisp Chris — already live)
- **Grand total: 81 new S8 documents**

Bands locked in:
1. Deflowerment ✅ DONE — Rubber Ruben (A) + Ruben Grossas (B)
2. Abominable Snowman ⏳
3. Prophetic ⏳
4. Drooping ⏳
5. Cadaver Melt ⏳
6. Crying Fetus ⏳
7. Skinful ⏳
8. Feeling Plesh ⏳

Variant flavors (universal scratch cover + universal back already wired):
- Holographic / Comic / Graffiti / Neon

---

## Part 1 — `CARD_IMAGE_URLS` (front images) additions

Append these alphabetically by band. Replace each `TODO:...` with the artifact URL from `get_assets_tool` after upload.

```python
# ---- Series 8 — Slam Edition (base + variant fronts) ----
# Deflowerment / Rubber Ruben (Card A) ✅
"rubber_ruben":              "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/fx6c62e6_enhanced-1780098706026.jpg",
"rubber_ruben_holographic":  "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/866yqj72_Screenshot_20260602_014936_ChatGPT.png",
"rubber_ruben_comic":        "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/hmjih433_Screenshot_20260602_021257_ChatGPT.png",
"rubber_ruben_graffiti":     "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/b7kpz7dv_Screenshot_20260602_021331_ChatGPT.png",
"rubber_ruben_neon":         "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/7sluimey_Screenshot_20260602_021623_ChatGPT.png",

# Deflowerment / Ruben Grossas (Card B) ✅
"ruben_grossas":             "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/3z7qwzj1_enhanced-1780099203422.jpg",
"ruben_grossas_holographic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/v6wd643f_Screenshot_20260602_023553_ChatGPT.png",
"ruben_grossas_comic":       "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/kjp1ajm1_Screenshot_20260602_024111_ChatGPT.png",
"ruben_grossas_graffiti":    "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/pyjhp2l4_Screenshot_20260602_030615_ChatGPT.png",
"ruben_grossas_neon":        "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/6qgtfvnm_Screenshot_20260602_075459_ChatGPT.png",

# Abominable Snowman / Card A
"snow_a_slug":                "TODO:front URL",
"snow_a_slug_holographic":    "TODO:holographic URL",
"snow_a_slug_comic":          "TODO:comic URL",
"snow_a_slug_graffiti":       "TODO:graffiti URL",
"snow_a_slug_neon":           "TODO:neon URL",
# Abominable Snowman / Card B
"snow_b_slug":                "TODO:front URL",
"snow_b_slug_holographic":    "TODO:holographic URL",
"snow_b_slug_comic":          "TODO:comic URL",
"snow_b_slug_graffiti":       "TODO:graffiti URL",
"snow_b_slug_neon":           "TODO:neon URL",

# Prophetic / Card A
"prophet_a_slug":              "TODO:front URL",
"prophet_a_slug_holographic":  "TODO:holographic URL",
"prophet_a_slug_comic":        "TODO:comic URL",
"prophet_a_slug_graffiti":     "TODO:graffiti URL",
"prophet_a_slug_neon":         "TODO:neon URL",
# Prophetic / Card B
"prophet_b_slug":              "TODO:front URL",
"prophet_b_slug_holographic":  "TODO:holographic URL",
"prophet_b_slug_comic":        "TODO:comic URL",
"prophet_b_slug_graffiti":     "TODO:graffiti URL",
"prophet_b_slug_neon":         "TODO:neon URL",

# Drooping / Card A
"droop_a_slug":                "TODO:front URL",
"droop_a_slug_holographic":    "TODO:holographic URL",
"droop_a_slug_comic":          "TODO:comic URL",
"droop_a_slug_graffiti":       "TODO:graffiti URL",
"droop_a_slug_neon":           "TODO:neon URL",
# Drooping / Card B
"droop_b_slug":                "TODO:front URL",
"droop_b_slug_holographic":    "TODO:holographic URL",
"droop_b_slug_comic":          "TODO:comic URL",
"droop_b_slug_graffiti":       "TODO:graffiti URL",
"droop_b_slug_neon":           "TODO:neon URL",

# Cadaver Melt / Card A
"melt_a_slug":                 "TODO:front URL",
"melt_a_slug_holographic":     "TODO:holographic URL",
"melt_a_slug_comic":           "TODO:comic URL",
"melt_a_slug_graffiti":        "TODO:graffiti URL",
"melt_a_slug_neon":            "TODO:neon URL",
# Cadaver Melt / Card B
"melt_b_slug":                 "TODO:front URL",
"melt_b_slug_holographic":     "TODO:holographic URL",
"melt_b_slug_comic":           "TODO:comic URL",
"melt_b_slug_graffiti":        "TODO:graffiti URL",
"melt_b_slug_neon":            "TODO:neon URL",

# Crying Fetus / Card A
"fetus_a_slug":                "TODO:front URL",
"fetus_a_slug_holographic":    "TODO:holographic URL",
"fetus_a_slug_comic":          "TODO:comic URL",
"fetus_a_slug_graffiti":       "TODO:graffiti URL",
"fetus_a_slug_neon":           "TODO:neon URL",
# Crying Fetus / Card B
"fetus_b_slug":                "TODO:front URL",
"fetus_b_slug_holographic":    "TODO:holographic URL",
"fetus_b_slug_comic":          "TODO:comic URL",
"fetus_b_slug_graffiti":       "TODO:graffiti URL",
"fetus_b_slug_neon":           "TODO:neon URL",

# Skinful / Card A
"skin_a_slug":                 "TODO:front URL",
"skin_a_slug_holographic":     "TODO:holographic URL",
"skin_a_slug_comic":           "TODO:comic URL",
"skin_a_slug_graffiti":        "TODO:graffiti URL",
"skin_a_slug_neon":            "TODO:neon URL",
# Skinful / Card B
"skin_b_slug":                 "TODO:front URL",
"skin_b_slug_holographic":     "TODO:holographic URL",
"skin_b_slug_comic":           "TODO:comic URL",
"skin_b_slug_graffiti":        "TODO:graffiti URL",
"skin_b_slug_neon":            "TODO:neon URL",

# Feeling Plesh / Card A
"plesh_a_slug":                "TODO:front URL",
"plesh_a_slug_holographic":    "TODO:holographic URL",
"plesh_a_slug_comic":          "TODO:comic URL",
"plesh_a_slug_graffiti":       "TODO:graffiti URL",
"plesh_a_slug_neon":           "TODO:neon URL",
# Feeling Plesh / Card B
"plesh_b_slug":                "TODO:front URL",
"plesh_b_slug_holographic":    "TODO:holographic URL",
"plesh_b_slug_comic":          "TODO:comic URL",
"plesh_b_slug_graffiti":       "TODO:graffiti URL",
"plesh_b_slug_neon":           "TODO:neon URL",
```

---

## Part 2 — `CARD_BACK_IMAGE_URLS` additions

Only ONE back URL per base card. Variants reuse the universal `variant_back_holographic / variant_back_comic / variant_back_graffiti / variant_back_neon` already wired in the dict.

```python
# ---- Series 8 — Slam Edition (base card backs) ----
"rubber_ruben":     "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/uba3netc_enhanced-1780098829928.jpg",  # ✅
"ruben_grossas":    "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/xx3yuzzh_enhanced-1780102951101.jpg",  # ✅
"snow_a_slug":      "TODO:back URL",
"snow_b_slug":      "TODO:back URL",
"prophet_a_slug":   "TODO:back URL",
"prophet_b_slug":   "TODO:back URL",
"droop_a_slug":     "TODO:back URL",
"droop_b_slug":     "TODO:back URL",
"melt_a_slug":      "TODO:back URL",
"melt_b_slug":      "TODO:back URL",
"fetus_a_slug":     "TODO:back URL",
"fetus_b_slug":     "TODO:back URL",
"skin_a_slug":      "TODO:back URL",
"skin_b_slug":      "TODO:back URL",
"plesh_a_slug":     "TODO:back URL",
"plesh_b_slug":     "TODO:back URL",
```

---

## Part 3 — `INITIAL_CARDS` list entries

### Already live (for reference)

```python
# ---- Deflowerment / Rubber Ruben (Card A) ✅
{
    "id": "card_rubber_ruben",
    "name": "Rubber Ruben",
    "description": "The Flexible Frontman of Deflowerment. Squishy, stretchy, and ready to slam!...",
    "rarity": "common",
    "front_image_url": CARD_IMAGE_URLS["rubber_ruben"],
    "back_image_url":  CARD_BACK_IMAGE_URLS["rubber_ruben"],
    "coin_cost": 50,
    "available": True,
    "series": 8,
    "band": "Deflowerment",
    "card_type": "A"
},
# + 4 variants: card_rubber_ruben_holographic / _comic / _graffiti / _neon

# ---- Deflowerment / Ruben Grossas (Card B) ✅
{
    "id": "card_ruben_grossas",
    "name": "Ruben Grossas",
    ...
    "card_type": "B"
},
# + 4 variants: card_ruben_grossas_holographic / _comic / _graffiti / _neon
```

### Template — repeat this 14-card block for each remaining band

Replace tokens:
- `{SLUG}` → unique snake_case slug, e.g. `frosty_blast`, `prophet_pukus`
- `{NAME}` → display name (no parens)
- `{BAND}` → exact band name from the list above
- `{TYPE}` → `"A"` for the first card of the band, `"B"` for the second
- `{BASE_DESC}` → full bio + stats + signature move
- `{HOLO_DESC}` / `{COMIC_DESC}` / `{GRAFFITI_DESC}` / `{NEON_DESC}` → 1–2 sentence variant flavor texts

```python
# =====================
# SERIES 8 - Band X: {BAND}
# =====================
# ---- {BAND} / {NAME} (Card {TYPE}) ----
{
    "id": "card_{SLUG}",
    "name": "{NAME}",
    "description": "{BASE_DESC}",
    "rarity": "common",
    "front_image_url": CARD_IMAGE_URLS["{SLUG}"],
    "back_image_url":  CARD_BACK_IMAGE_URLS["{SLUG}"],
    "coin_cost": 50,
    "available": True,
    "series": 8,
    "band": "{BAND}",
    "card_type": "{TYPE}"
},
# ---- {NAME} variants (Series 8 / Slam Edition) ----
{
    "id": "card_{SLUG}_holographic",
    "name": "{NAME} (Holographic)",
    "description": "{HOLO_DESC}",
    "rarity": "variant",
    "front_image_url": CARD_IMAGE_URLS["{SLUG}_holographic"],
    "back_image_url":  CARD_BACK_IMAGE_URLS["variant_back_holographic"],
    "coin_cost": 50,
    "available": True,
    "series": 8,
    "band": "{BAND}",
    "card_type": "{TYPE}",
    "is_variant": True,
    "base_card_id": "card_{SLUG}",
    "variant_name": "Holographic"
},
{
    "id": "card_{SLUG}_comic",
    "name": "{NAME} (Comic)",
    "description": "{COMIC_DESC}",
    "rarity": "variant",
    "front_image_url": CARD_IMAGE_URLS["{SLUG}_comic"],
    "back_image_url":  CARD_BACK_IMAGE_URLS["variant_back_comic"],
    "coin_cost": 50,
    "available": True,
    "series": 8,
    "band": "{BAND}",
    "card_type": "{TYPE}",
    "is_variant": True,
    "base_card_id": "card_{SLUG}",
    "variant_name": "Comic"
},
{
    "id": "card_{SLUG}_graffiti",
    "name": "{NAME} (Graffiti)",
    "description": "{GRAFFITI_DESC}",
    "rarity": "variant",
    "front_image_url": CARD_IMAGE_URLS["{SLUG}_graffiti"],
    "back_image_url":  CARD_BACK_IMAGE_URLS["variant_back_graffiti"],
    "coin_cost": 50,
    "available": True,
    "series": 8,
    "band": "{BAND}",
    "card_type": "{TYPE}",
    "is_variant": True,
    "base_card_id": "card_{SLUG}",
    "variant_name": "Graffiti"
},
{
    "id": "card_{SLUG}_neon",
    "name": "{NAME} (Neon)",
    "description": "{NEON_DESC}",
    "rarity": "variant",
    "front_image_url": CARD_IMAGE_URLS["{SLUG}_neon"],
    "back_image_url":  CARD_BACK_IMAGE_URLS["variant_back_neon"],
    "coin_cost": 50,
    "available": True,
    "series": 8,
    "band": "{BAND}",
    "card_type": "{TYPE}",
    "is_variant": True,
    "base_card_id": "card_{SLUG}",
    "variant_name": "Neon"
},
```

---

## Part 4 — Per-band rollout order

Each remaining band needs 2 base + 8 variants = 10 inserts × 7 bands = 70 cards.

When you send the next character, include:
1. **Band name** (one from the locked list above)
2. **Card slot** (A or B)
3. **Character name** (e.g. "Frostbite Floyd")
4. **6 images attached in order**: front, back, holographic, comic, graffiti, neon

I'll then:
- Add 5 entries to `CARD_IMAGE_URLS`
- Add 1 entry to `CARD_BACK_IMAGE_URLS`
- Append 5 dicts to `INITIAL_CARDS` (1 base + 4 variants) using the template above
- Auto-write descriptions from the stats card on the back image
- Confirm `Inserted new card: X` × 5 in the seeder log

Backend hot-reloads — no EAS build, no DB wipe, user collections untouched.

---

## Sanity checks before launch (June 13, 2026 05:00 UTC)

- [ ] All 16 base cards present (`db.cards.count_documents({"series": 8, "is_variant": {"$ne": True}}) == 16`)
- [ ] All 64 variants present (`db.cards.count_documents({"series": 8, "is_variant": True}) == 64`)
- [ ] Crisp Chris epic reward exists with `achievement_required: 128` ✅
- [ ] `SERIES_CONFIG[8].release_date` matches the wanted launch moment ✅ (Sat Jun 13 05:00 UTC)
- [ ] Each card has both `front_image_url` and `back_image_url` populated (no empty strings)
- [ ] Each variant has `is_variant: True`, `base_card_id`, and `variant_name` set
- [ ] Spot-check Pillow: `curl /api/cards/card_{slug}/thumb?w=240` returns ~30 KB JPEG
- [ ] Spot-check scratch cover: `curl /api/cards/card_{slug}_holographic/scratch-cover?w=540` returns ~80 KB JPEG

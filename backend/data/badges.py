"""
Badge system for Thrash Kan Kidz.

Badges are server-authoritative achievements computed from existing user state
(cards collected, trades accepted, login streak, etc.) — no separate badge
table or migration required. Adding/removing/tuning a badge is a single edit
to this file.

Each badge has:
  - id, name, description, icon (Ionicons name), tint (hex color)
  - condition_type: one of the well-known checks below
  - condition_params: arguments to the check (varies by type)
  - image_url: optional override — when set, frontend renders this instead
    of the icon. Leave blank until custom art exists.
"""
from typing import Optional

# Condition types — kept as bare strings (not an Enum) so the frontend can
# inspect them without a generated TypeScript binding.
COND_SERIES_BASE_COMPLETE = "series_base_complete"   # params: {"series_num": int}
COND_LOGIN_STREAK = "login_streak"                   # params: {"min": int}
COND_TRADES_ACCEPTED = "trades_accepted"             # params: {"min": int}
COND_VARIANTS_OWNED = "variants_owned"               # params: {"min": int}
COND_CREATED_BEFORE_SERIES = "created_before_series" # params: {"series_num": int}
COND_OWN_ANY_CARD = "own_any_card"                   # params: {}
COND_TOTAL_SPENT = "total_spent"                     # params: {"min": int}
COND_FRIEND_COUNT = "friend_count"                   # params: {"min": int}
COND_OWN_SPECIFIC_CARD = "own_specific_card"         # params: {"card_id": str}
COND_GRANTED = "granted"                             # params: {}; admin/founder-granted via users.granted_badges


BADGES = [
    # --- The 5 the user explicitly asked for ---
    {
        "id": "series_1_master",
        "name": "Series 1 Master",
        "description": "Collect every base card from Series 1",
        "icon": "ribbon",
        "tint": "#FFD700",
        "condition_type": COND_SERIES_BASE_COMPLETE,
        "condition_params": {"series_num": 1},
        "image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/5g83qmi2_enhanced-1779076898405.png",
    },
    {
        "id": "streak_100",
        "name": "100 Day Streak",
        "description": "Log in for 100 consecutive days",
        "icon": "flame",
        "tint": "#FF4500",
        "condition_type": COND_LOGIN_STREAK,
        "condition_params": {"min": 100},
        "image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/928oqvaj_enhanced-1779097988195.png",
    },
    {
        "id": "trade_addict",
        "name": "Trade Addict",
        "description": "Complete 25 accepted trades",
        "icon": "swap-horizontal",
        "tint": "#00BFFF",
        "condition_type": COND_TRADES_ACCEPTED,
        "condition_params": {"min": 25},
        "image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/teb3l3je_enhanced-1779098063309.png",
    },
    {
        "id": "variant_hunter",
        "name": "Variant Hunter",
        "description": "Collect 10 variant cards",
        "icon": "sparkles",
        "tint": "#C770FF",
        "condition_type": COND_VARIANTS_OWNED,
        "condition_params": {"min": 10},
        "image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/m74kq8ac_enhanced-1779098162990.png",
    },
    {
        "id": "og_collector",
        "name": "OG Collector",
        "description": "Joined before Series 4 dropped",
        "icon": "medal",
        "tint": "#B87333",
        "condition_type": COND_CREATED_BEFORE_SERIES,
        "condition_params": {"series_num": 4},
        "image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/pt7eqpwu_enhanced-1779098273380.png",
    },

    # --- Series 2-7 Master mirrors ---
    {
        "id": "series_2_master",
        "name": "Series 2 Master",
        "description": "Collect every base card from Series 2",
        "icon": "ribbon",
        "tint": "#FFD700",
        "condition_type": COND_SERIES_BASE_COMPLETE,
        "condition_params": {"series_num": 2},
        "image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/tugzi06r_enhanced-1779077203881.png",
    },
    {
        "id": "series_3_master",
        "name": "Series 3 Master",
        "description": "Collect every base card from Series 3",
        "icon": "ribbon",
        "tint": "#FFD700",
        "condition_type": COND_SERIES_BASE_COMPLETE,
        "condition_params": {"series_num": 3},
        "image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/bjdtkz6n_enhanced-1779077356786.png",
    },
    {
        "id": "series_4_master",
        "name": "Series 4 Master",
        "description": "Collect every base card from Series 4",
        "icon": "ribbon",
        "tint": "#FFD700",
        "condition_type": COND_SERIES_BASE_COMPLETE,
        "condition_params": {"series_num": 4},
        "image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/de6uw9qg_enhanced-1779077568638.png",
    },
    {
        "id": "series_5_master",
        "name": "Series 5 Master",
        "description": "Collect every base card from Series 5",
        "icon": "ribbon",
        "tint": "#FFD700",
        "condition_type": COND_SERIES_BASE_COMPLETE,
        "condition_params": {"series_num": 5},
        "image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/ym5bexzi_enhanced-1779077842748.png",
    },
    {
        "id": "series_6_master",
        "name": "Series 6 Master",
        "description": "Collect every base card from Series 6",
        "icon": "ribbon",
        "tint": "#FFD700",
        "condition_type": COND_SERIES_BASE_COMPLETE,
        "condition_params": {"series_num": 6},
        "image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/clxtquwo_enhanced-1779078150758.png",
    },
    {
        "id": "series_7_master",
        "name": "Series 7 Master",
        "description": "Collect every base card from Series 7",
        "icon": "ribbon",
        "tint": "#FFD700",
        "condition_type": COND_SERIES_BASE_COMPLETE,
        "condition_params": {"series_num": 7},
        "image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/b8qfgszs_enhanced-1779078359336.png",
    },
    {
        "id": "series_8_master",
        "name": "Series 8 Master",
        "description": "Collect every base card from Series 8",
        "icon": "ribbon",
        "tint": "#39ff14",  # neon green to match the badge art
        "condition_type": COND_SERIES_BASE_COMPLETE,
        "condition_params": {"series_num": 8},
        "image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/ys2a0zds_file_0000000024a871fda2c8f23705204a9c.png",
    },
    {
        "id": "series_9_master",
        "name": "Series 9 Master",
        "description": "Collect every base card from Series 9",
        "icon": "ribbon",
        "tint": "#ffd700",  # gold to match the badge art
        "condition_type": COND_SERIES_BASE_COMPLETE,
        "condition_params": {"series_num": 9},
        "image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/p6upndw7_file_00000000388471fd96baba97e39cf724.png",
    },

    # --- Easy wins (proactive additions) ---
    {
        "id": "first_pull",
        "name": "First Pull",
        "description": "Open your first pack",
        "icon": "gift",
        "tint": "#4CAF50",
        "condition_type": COND_OWN_ANY_CARD,
        "condition_params": {},
        "image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/8pfbiq6o_enhanced-1779097079250.png",
    },
    {
        "id": "big_spender",
        "name": "Big Spender",
        "description": "Spend 50,000 coins total",
        "icon": "cash",
        "tint": "#FFD700",
        "condition_type": COND_TOTAL_SPENT,
        "condition_params": {"min": 50000},
        "image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/xphfw3tl_enhanced-1779098352745.png",
    },
    {
        "id": "friend_magnet",
        "name": "Friend Magnet",
        "description": "Become friends with 10 other thrashers",
        "icon": "people",
        "tint": "#00CED1",
        "condition_type": COND_FRIEND_COUNT,
        "condition_params": {"min": 10},
        "image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/h9zielj3_enhanced-1779098964603.png",
    },
    {
        "id": "alien_believer",
        "name": "Alien Believer",
        "description": "Pull Alien Dubin from Series 7",
        "icon": "planet",
        "tint": "#9C27B0",
        "condition_type": COND_OWN_SPECIFIC_CARD,
        "condition_params": {"card_id": "card_alien_dubin"},
        "image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/e2quc12v_enhanced-1779099024275.png",
    },
    # --- New badges (placeholder conditions until proper tracking is added) ---
    {
        "id": "midnight_maniac",
        "name": "Midnight Maniac",
        "description": "Keep a 30-day login streak (no sleep, just cards)",
        "icon": "moon",
        "tint": "#9C27B0",
        "condition_type": COND_LOGIN_STREAK,
        "condition_params": {"min": 30},
        "image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/t2cq4tsp_enhanced-1779153899003.png",
    },
    {
        "id": "weekend_warrior",
        "name": "Weekend Warrior",
        "description": "Spend 25,000 coins on packs (weekend mayhem)",
        "icon": "flash",
        "tint": "#4CAF50",
        "condition_type": COND_TOTAL_SPENT,
        "condition_params": {"min": 25000},
        "image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/yaz6fygi_enhanced-1779154497137.png",
    },
    # Founders' badge — granted to every existing internal tester at
    # the moment of release. Not auto-earnable; stamped on user docs
    # via the `granted_badges` array.
    {
        "id": "founding_thrasher",
        "name": "Founding Thrasher",
        "description": "Day-one banger — slammed the pit before the gates opened.",
        "icon": "trophy",
        "tint": "#FFD24A",
        "condition_type": COND_GRANTED,
        "condition_params": {},
        "image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/5lqglpcu_Screenshot_20260530_171350_ChatGPT.png",
    },
]


def get_badge(badge_id: str) -> Optional[dict]:
    """Find a badge definition by id."""
    return next((b for b in BADGES if b["id"] == badge_id), None)

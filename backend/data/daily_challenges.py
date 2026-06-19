"""
Daily Challenges catalog. The "pool" is the universe of possible challenges;
each user is shown 3 deterministic picks per day (seeded by user_id + date)
and picks exactly one to chase. Progress is computed on-the-fly from the
authoritative collections (`user_cards`, `trades`) — no progress events
need to be written by other routes.

Reward keys map 1:1 to user fields:
  - coins            -> user.coins (incremented)
  - free_packs       -> user.free_packs (incremented)
  - wheel_tickets    -> user.wheel_tickets (created/incremented)
  - bonus_card_id    -> card_id to grant in user_cards (chosen at claim time
                        from the existing rare/variant pool if value is "*")
"""
from __future__ import annotations

CHALLENGE_POOL = [
    # ---------- PACK-OPEN CHALLENGES ----------
    {
        "id": "open_3_packs",
        "type": "open_packs",
        "name": "Rip 3 Packs",
        "description": "Open 3 packs today. Any type counts.",
        "target": 3,
        "icon": "package",
        "rewards": {
            "coins": 300,
            "free_packs": 1,
            "wheel_tickets": 0,
            "bonus_card_id": None,
        },
    },
    {
        "id": "open_5_packs",
        "type": "open_packs",
        "name": "Pack Frenzy",
        "description": "Open 5 packs today for a bigger payout.",
        "target": 5,
        "icon": "package",
        "rewards": {
            "coins": 500,
            "free_packs": 2,
            "wheel_tickets": 1,
            "bonus_card_id": None,
        },
    },
    {
        "id": "open_8_packs",
        "type": "open_packs",
        "name": "Pit Master",
        "description": "Open 8 packs today. For pack-ripping diehards.",
        "target": 8,
        "icon": "package",
        "rewards": {
            "coins": 800,
            "free_packs": 3,
            "wheel_tickets": 1,
            "bonus_card_id": "*",  # random variant card on claim
        },
    },
    # ---------- VARIANT-COLLECT CHALLENGES ----------
    {
        "id": "collect_3_variants",
        "type": "collect_variants",
        "name": "Variant Hunter",
        "description": "Collect 3 variant cards (any flavor) today.",
        "target": 3,
        "icon": "sparkles",
        "rewards": {
            "coins": 400,
            "free_packs": 1,
            "wheel_tickets": 0,
            "bonus_card_id": None,
        },
    },
    {
        "id": "collect_5_variants",
        "type": "collect_variants",
        "name": "Shiny Squad",
        "description": "Collect 5 variant cards today. Pull rate test.",
        "target": 5,
        "icon": "sparkles",
        "rewards": {
            "coins": 600,
            "free_packs": 1,
            "wheel_tickets": 1,
            "bonus_card_id": "*",  # guaranteed variant on claim
        },
    },
    {
        "id": "collect_7_variants",
        "type": "collect_variants",
        "name": "Glittered Out",
        "description": "Collect 7 variant cards today. For the truly cursed.",
        "target": 7,
        "icon": "sparkles",
        "rewards": {
            "coins": 900,
            "free_packs": 2,
            "wheel_tickets": 1,
            "bonus_card_id": "*",
        },
    },
    # ---------- TRADE CHALLENGES ----------
    {
        "id": "complete_1_trade",
        "type": "complete_trades",
        "name": "First Bump",
        "description": "Complete 1 trade today.",
        "target": 1,
        "icon": "users",
        "rewards": {
            "coins": 300,
            "free_packs": 1,
            "wheel_tickets": 0,
            "bonus_card_id": None,
        },
    },
    {
        "id": "complete_2_trades",
        "type": "complete_trades",
        "name": "Trade Pit",
        "description": "Complete 2 trades today. Find your crew.",
        "target": 2,
        "icon": "users",
        "rewards": {
            "coins": 500,
            "free_packs": 1,
            "wheel_tickets": 1,
            "bonus_card_id": None,
        },
    },
    {
        "id": "complete_3_trades",
        "type": "complete_trades",
        "name": "Mosh Diplomat",
        "description": "Complete 3 trades today. Pure social slam.",
        "target": 3,
        "icon": "users",
        "rewards": {
            "coins": 750,
            "free_packs": 2,
            "wheel_tickets": 1,
            "bonus_card_id": "*",
        },
    },
]

CHALLENGE_BY_ID = {c["id"]: c for c in CHALLENGE_POOL}


def pick_daily_offering(user_id: str, date_utc_iso: str) -> list[dict]:
    """
    Deterministically pick 3 challenges for a given (user, date) pair.
    Picks one from each of the 3 categories so users always see a balanced
    set. Same user + same date always yields the same 3 challenges, so
    offerings don't reshuffle if the user re-fetches the endpoint.
    """
    import hashlib

    pack = [c for c in CHALLENGE_POOL if c["type"] == "open_packs"]
    variants = [c for c in CHALLENGE_POOL if c["type"] == "collect_variants"]
    trades = [c for c in CHALLENGE_POOL if c["type"] == "complete_trades"]

    def pick_one(bucket: list[dict], salt: str) -> dict:
        seed = hashlib.sha1(f"{user_id}|{date_utc_iso}|{salt}".encode()).digest()
        idx = seed[0] % len(bucket)
        return bucket[idx]

    return [pick_one(pack, "P"), pick_one(variants, "V"), pick_one(trades, "T")]

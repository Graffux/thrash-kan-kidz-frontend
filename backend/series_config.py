"""
Single source of truth for series progression metadata.

Why this module exists
----------------------
* `server.py` and `routers/cards.py` both need to know which series are
  publicly visible at any given moment. Importing from `server.py` would be
  circular (server imports the routers), so the static config + release helpers
  live here and both modules import from this file.

Release scheduling model
------------------------
Each series may be in one of three states:

* `released` — visible to all players. Cards in this series are returned by
  `/api/cards`, the series shows up in `/api/series/list` as released, and
  series-completion logic auto-unlocks the next one.
* `scheduled` — has a `release_date` in the future. Hidden from `/api/cards`
  and from `series-progress`, but the frontend still shows a "Coming Soon"
  tile with a countdown via `/api/series/list`.
* `coming_soon` — declared in code but no `release_date` set yet. Same
  visibility as `scheduled`, but the tile shows "Coming Soon" with no
  countdown. An admin can flip it to `scheduled` at runtime via
  `POST /api/admin/series/{n}/release-date` without a redeploy.

Runtime overrides
-----------------
Admin-set release dates persist in `db.series_overrides` so they survive
backend restarts. `init_overrides()` is awaited at app startup; after that the
sync helpers (`is_series_released`, `released_series_nums`, `current_max_series`)
can safely be called from any code path.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, List, Optional


# Static metadata. Add new series here. `release_date` is optional; if absent
# the series is treated as `coming_soon` until an admin sets one (or you ship
# an update to populate the date directly).
SERIES_CONFIG: Dict[int, dict] = {
    1: {
        "name": "Series 1",
        "cards_required": 16,
        "rare_reward": "card_kerry_the_king",
        "description": "The Original Thrash Kan Kidz",
    },
    2: {
        "name": "Series 2",
        "cards_required": 16,
        "rare_reward": "card_strap_on_taylor",
        "description": "More Mayhem",
    },
    3: {
        "name": "Series 3",
        "cards_required": 16,
        "rare_reward": "card_sean_kill_again",
        "description": "The Thrash Continues",
    },
    4: {
        "name": "Series 4",
        "cards_required": 16,
        "rare_reward": "card_jeff_wanker",
        "description": "Death Metal Edition",
    },
    5: {
        "name": "Series 5",
        "cards_required": 16,
        "rare_reward": "card_martin_generic_aint",
        "description": "Thrash Metal Edition",
    },
    6: {
        "name": "Series 6",
        "cards_required": 16,
        "rare_reward": "card_nicklebag_darrell",
        "description": "Maximum Dose",
    },
    # Series 7 — Grind Edition. Reward is the epic "Alien Dubin" card,
    # auto-granted on series completion (all 16 base cards collected).
    7: {
        "name": "Series 7",
        "cards_required": 16,
        "rare_reward": "card_alien_dubin",
        "description": "Grind Edition",
    },
    # Series 8 — Slam Edition. Reward is the epic "Crisp Chris" card,
    # auto-granted on series completion (all 128 cards across S1–S8 collected).
    # release_date scheduled for Saturday June 13, 2026 @ 00:00 CDT (= 05:00 UTC).
    8: {
        "name": "Series 8",
        "cards_required": 16,
        "rare_reward": "card_crisp_chris",
        "description": "Slam Edition",
        "release_date": datetime(2026, 6, 13, 5, 0, 0, tzinfo=timezone.utc),
    },
}

# Highest series number declared in code. NOT the same as the highest
# *released* series — use `current_max_series()` for visibility checks.
MAX_DECLARED_SERIES: int = max(SERIES_CONFIG.keys())

# Runtime release-date overrides (admin-set, persisted in MongoDB).
#   _release_overrides[series_num] = datetime (released on/after) | None (coming soon)
# A series number absent from this map falls back to SERIES_CONFIG[n]["release_date"].
_release_overrides: Dict[int, Optional[datetime]] = {}


def _normalize_dt(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_release_date(series_num: int) -> Optional[datetime]:
    """Return the effective release date for a series (override > config > None)."""
    if series_num in _release_overrides:
        return _release_overrides[series_num]
    cfg = SERIES_CONFIG.get(series_num)
    if not cfg:
        return None
    return _normalize_dt(cfg.get("release_date"))


# Series numbers that were already in production before scheduled releases
# shipped. They can never be hidden — they're already in the wild and the
# users own cards from them. Anything <= this number is always "released",
# regardless of stale overrides in the DB.
LEGACY_RELEASED_THROUGH = 6


def is_series_released(series_num: int) -> bool:
    """A series is released when its release_date is set AND in the past.

    Series 1-LEGACY_RELEASED_THROUGH are pre-scheduling-system content and
    are always treated as released. Anything newer must have a release_date
    set (either in SERIES_CONFIG or via the admin endpoint) to flip live.
    """
    if series_num not in SERIES_CONFIG:
        return False
    if series_num <= LEGACY_RELEASED_THROUGH:
        return True

    rel = get_release_date(series_num)
    if rel is None:
        return False
    return datetime.now(timezone.utc) >= rel


def series_status(series_num: int) -> str:
    """One of: released | scheduled | coming_soon | unknown."""
    if series_num not in SERIES_CONFIG:
        return "unknown"
    if is_series_released(series_num):
        return "released"
    if get_release_date(series_num) is not None:
        return "scheduled"
    return "coming_soon"


def released_series_nums() -> List[int]:
    return [n for n in sorted(SERIES_CONFIG.keys()) if is_series_released(n)]


def current_max_series() -> int:
    """Highest series number currently visible to players (defaults to 1)."""
    rel = released_series_nums()
    return rel[-1] if rel else 1


def set_release_date_in_memory(series_num: int, dt: Optional[datetime]) -> None:
    """Apply an in-memory override. Caller is responsible for persisting."""
    if series_num not in SERIES_CONFIG:
        raise KeyError(f"Series {series_num} is not declared in SERIES_CONFIG")
    _release_overrides[series_num] = _normalize_dt(dt)


async def init_overrides(db) -> None:
    """Load persisted overrides from `db.series_overrides` into memory.

    Call this once at app startup, after the Mongo client is wired up.
    """
    cursor = db.series_overrides.find({}, {"_id": 0})
    async for doc in cursor:
        sn = doc.get("series_num")
        if sn in SERIES_CONFIG:
            _release_overrides[sn] = _normalize_dt(doc.get("release_date"))


async def persist_release_date(db, series_num: int, dt: Optional[datetime]) -> None:
    """Upsert the override into MongoDB AND update the in-memory cache."""
    set_release_date_in_memory(series_num, dt)
    await db.series_overrides.update_one(
        {"series_num": series_num},
        {"$set": {"series_num": series_num, "release_date": _normalize_dt(dt)}},
        upsert=True,
    )

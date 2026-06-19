"""
Daily Challenges router.

Endpoints (all prefixed with /api by the parent router):
  GET  /users/{user_id}/daily-challenges       -> {offerings, selected, progress, claimed, reset_at}
  POST /users/{user_id}/daily-challenges/select?challenge_id=...
  POST /users/{user_id}/daily-challenges/claim

Design notes:
  - 3 offerings/day, deterministic per (user_id, date_utc).
  - User picks ONE; lock-in is final until the next UTC midnight.
  - Progress is computed live from `user_cards` and `trades` — no event
    plumbing into existing endpoints required.
  - Rewards dispatched at /claim only (so playing past the target doesn't
    drip rewards by accident).
"""
from __future__ import annotations

import os
import random
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Body
from motor.motor_asyncio import AsyncIOMotorClient

from data.daily_challenges import (
    CHALLENGE_BY_ID,
    pick_daily_offering,
)

router = APIRouter()

mongo_url = os.environ["MONGO_URL"]
db_name = os.environ["DB_NAME"]
_client = AsyncIOMotorClient(mongo_url)
db = _client[db_name]


def _today_utc_iso() -> str:
    """YYYY-MM-DD in UTC. Used as the doc key for /daily-challenges state."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _next_reset_iso() -> str:
    """ISO timestamp of the next UTC midnight."""
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return tomorrow.isoformat()


def _start_of_today_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


async def _compute_progress(user_id: str, challenge: dict) -> int:
    """Compute today's progress against a challenge by querying authoritative
    collections. Returns an integer count (caller compares to challenge['target'])."""
    today_start = _start_of_today_utc()
    ctype = challenge["type"]

    if ctype == "open_packs":
        # Every user_card row inserted today represents a pulled card. Pack
        # opens, scratches, wheel rewards, and card-picker prizes all
        # write here, so this proxy is "you played the game today" rather
        # than strictly pack-only. Good enough for v1; tighten later by
        # tagging the source field on each insert.
        return await db.user_cards.count_documents({
            "user_id": user_id,
            "acquired_at": {"$gte": today_start},
        })

    if ctype == "collect_variants":
        # Need to filter user_cards by referenced card's is_variant flag.
        # Two-step is cleaner than $lookup since the cards collection is
        # small and hot in cache anyway.
        rows = await db.user_cards.find(
            {"user_id": user_id, "acquired_at": {"$gte": today_start}},
            {"_id": 0, "card_id": 1},
        ).to_list(500)
        if not rows:
            return 0
        card_ids = list({r["card_id"] for r in rows})
        variant_count_cursor = db.cards.find(
            {"id": {"$in": card_ids}, "is_variant": True},
            {"_id": 0, "id": 1},
        )
        variant_ids = {c["id"] for c in await variant_count_cursor.to_list(None)}
        # Sum quantity for variant inserts today
        # (each row already represents 1 acquisition event since we filter by acquired_at)
        return sum(1 for r in rows if r["card_id"] in variant_ids)

    if ctype == "complete_trades":
        return await db.trades.count_documents({
            "$or": [{"from_user_id": user_id}, {"to_user_id": user_id}],
            "status": "accepted",
            "created_at": {"$gte": today_start},
        })

    return 0


async def _get_or_create_state(user_id: str, date_iso: str) -> dict:
    """Fetch (or lazily create) the user's daily state doc. Picks the 3
    offerings deterministically so we don't need to persist them."""
    doc = await db.user_daily_challenges.find_one(
        {"user_id": user_id, "date_utc": date_iso}
    )
    if doc:
        return doc
    offerings = [c["id"] for c in pick_daily_offering(user_id, date_iso)]
    doc = {
        "user_id": user_id,
        "date_utc": date_iso,
        "offerings": offerings,  # 3 challenge ids
        "selected_id": None,     # locked-in pick (or None)
        "claimed_at": None,      # iso timestamp once rewards dispatched
    }
    await db.user_daily_challenges.insert_one(doc)
    return doc


def _decorate_offering(challenge: dict, progress: int) -> dict:
    """Shape a single offering for the API response."""
    target = challenge["target"]
    return {
        "id": challenge["id"],
        "type": challenge["type"],
        "name": challenge["name"],
        "description": challenge["description"],
        "icon": challenge.get("icon"),
        "target": target,
        "progress": min(progress, target),
        "is_complete": progress >= target,
        "rewards": challenge["rewards"],
    }


@router.get("/users/{user_id}/daily-challenges")
async def get_daily_challenges(user_id: str):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(404, "User not found")

    date_iso = _today_utc_iso()
    state = await _get_or_create_state(user_id, date_iso)

    offerings_out = []
    for cid in state["offerings"]:
        challenge = CHALLENGE_BY_ID.get(cid)
        if not challenge:
            continue
        progress = await _compute_progress(user_id, challenge)
        offerings_out.append(_decorate_offering(challenge, progress))

    selected_id = state.get("selected_id")
    selected_progress = 0
    selected_target = 0
    selected_is_complete = False
    if selected_id and selected_id in CHALLENGE_BY_ID:
        sc = CHALLENGE_BY_ID[selected_id]
        selected_progress = await _compute_progress(user_id, sc)
        selected_target = sc["target"]
        selected_is_complete = selected_progress >= selected_target

    return {
        "date_utc": date_iso,
        "reset_at_utc": _next_reset_iso(),
        "offerings": offerings_out,
        "selected_id": selected_id,
        "selected_progress": min(selected_progress, selected_target) if selected_target else 0,
        "selected_target": selected_target,
        "selected_is_complete": selected_is_complete,
        "claimed_at": state.get("claimed_at"),
    }


@router.post("/users/{user_id}/daily-challenges/select")
async def select_daily_challenge(user_id: str, challenge_id: str = Body(..., embed=True)):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(404, "User not found")
    date_iso = _today_utc_iso()
    state = await _get_or_create_state(user_id, date_iso)

    if challenge_id not in state["offerings"]:
        raise HTTPException(400, "challenge_id not in today's offerings")
    if state.get("selected_id") and state["selected_id"] != challenge_id:
        raise HTTPException(
            409, "Already locked in a different challenge today. Comes back tomorrow."
        )

    await db.user_daily_challenges.update_one(
        {"user_id": user_id, "date_utc": date_iso},
        {"$set": {"selected_id": challenge_id}},
    )
    return {"ok": True, "selected_id": challenge_id}


async def _pick_bonus_card_id() -> str | None:
    """Pick a random variant card from any released series. Returns None
    if no variants exist (shouldn't happen in production)."""
    candidates = await db.cards.find(
        {"is_variant": True}, {"_id": 0, "id": 1}
    ).to_list(2000)
    if not candidates:
        return None
    return random.choice(candidates)["id"]


@router.post("/users/{user_id}/daily-challenges/claim")
async def claim_daily_challenge(user_id: str):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(404, "User not found")
    date_iso = _today_utc_iso()
    state = await _get_or_create_state(user_id, date_iso)

    selected_id = state.get("selected_id")
    if not selected_id:
        raise HTTPException(400, "No challenge selected yet")
    if state.get("claimed_at"):
        raise HTTPException(409, "Already claimed today's reward")

    challenge = CHALLENGE_BY_ID.get(selected_id)
    if not challenge:
        raise HTTPException(500, "Selected challenge no longer exists")

    progress = await _compute_progress(user_id, challenge)
    if progress < challenge["target"]:
        raise HTTPException(
            400,
            f"Not done yet — {progress}/{challenge['target']}",
        )

    rewards = challenge["rewards"]
    granted = {
        "coins": int(rewards.get("coins") or 0),
        "free_packs": int(rewards.get("free_packs") or 0),
        "wheel_tickets": int(rewards.get("wheel_tickets") or 0),
        "bonus_card_id": None,
    }

    # Coins + packs + spin tickets
    update_doc = {}
    if granted["coins"]:
        update_doc["coins"] = int(user.get("coins", 0)) + granted["coins"]
    if granted["free_packs"]:
        update_doc["free_packs"] = int(user.get("free_packs", 0)) + granted["free_packs"]
    if granted["wheel_tickets"]:
        update_doc["wheel_tickets"] = (
            int(user.get("wheel_tickets", 0)) + granted["wheel_tickets"]
        )
    if update_doc:
        await db.users.update_one({"id": user_id}, {"$set": update_doc})

    # Bonus card (random variant on "*" sentinel)
    bcid = rewards.get("bonus_card_id")
    if bcid == "*":
        bcid = await _pick_bonus_card_id()
    if bcid:
        import uuid
        await db.user_cards.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "card_id": bcid,
            "quantity": 1,
            "acquired_at": datetime.now(timezone.utc),
        })
        granted["bonus_card_id"] = bcid

    claimed_iso = datetime.now(timezone.utc).isoformat()
    await db.user_daily_challenges.update_one(
        {"user_id": user_id, "date_utc": date_iso},
        {"$set": {"claimed_at": claimed_iso, "granted": granted}},
    )

    return {
        "ok": True,
        "challenge_id": selected_id,
        "granted": granted,
        "claimed_at": claimed_iso,
    }

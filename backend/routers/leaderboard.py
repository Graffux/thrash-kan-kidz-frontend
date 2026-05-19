"""
Leaderboard — composite ranking with switchable metric tabs.

Endpoints:
  GET /api/leaderboard?metric={cards|coins|series|streak|composite}
                      &limit=100&viewer_id=<optional>

Returns:
  {
    "metric": "composite",
    "rows": [{ rank, user_id, username, score, ...metric_stats }, ...],
    "viewer": { rank, score, ...metric_stats } | null,
  }

`viewer.rank` is the user's *global* rank even when they're not in the top N,
so the frontend can pin "Your rank: #237" at the bottom.

Composite formula:
  score = cards_owned + (completed_series * 100) + (daily_streak * 10) +
          (coins // 100)
This rewards collection breadth + series completion + engagement while
keeping coin-spamming from dominating.
"""
from fastapi import APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
import os

router = APIRouter()

_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = _client[os.environ["DB_NAME"]]

VALID_METRICS = {"cards", "coins", "series", "streak", "composite"}


def _compute_score(user: dict, cards_count: int, metric: str) -> int:
    completed = len(user.get("completed_series") or [])
    streak = int(user.get("daily_login_streak") or 0)
    coins = int(user.get("coins") or 0)
    if metric == "cards":
        return cards_count
    if metric == "coins":
        return coins
    if metric == "series":
        return completed
    if metric == "streak":
        return streak
    # composite
    return cards_count + (completed * 100) + (streak * 10) + (coins // 100)


def _row(rank: int, user: dict, cards_count: int, metric: str) -> dict:
    return {
        "rank": rank,
        "user_id": user["id"],
        "username": user.get("username", "anon"),
        "score": _compute_score(user, cards_count, metric),
        "cards_count": cards_count,
        "coins": int(user.get("coins") or 0),
        "completed_series": len(user.get("completed_series") or []),
        "daily_streak": int(user.get("daily_login_streak") or 0),
    }


@router.get("/leaderboard")
async def get_leaderboard(
    metric: str = "composite",
    limit: int = 100,
    viewer_id: str | None = None,
):
    if metric not in VALID_METRICS:
        raise HTTPException(400, f"metric must be one of {sorted(VALID_METRICS)}")
    limit = max(1, min(limit, 500))

    # Pull all users at once — fine while user count is modest. When it grows,
    # convert to an aggregation pipeline with $lookup against user_cards.
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(10000)
    # Card counts per user
    pipeline = [{"$group": {"_id": "$user_id", "n": {"$sum": 1}}}]
    counts_cur = db.user_cards.aggregate(pipeline)
    counts: dict[str, int] = {c["_id"]: c["n"] async for c in counts_cur}

    rows = [
        _row(0, u, counts.get(u["id"], 0), metric)
        for u in users
    ]
    rows.sort(key=lambda r: r["score"], reverse=True)
    # Apply ranks (1-indexed). Tied scores share the same rank.
    last_score = None
    rank = 0
    for i, r in enumerate(rows, start=1):
        if r["score"] != last_score:
            rank = i
            last_score = r["score"]
        r["rank"] = rank

    top = rows[:limit]
    viewer = None
    if viewer_id:
        for r in rows:
            if r["user_id"] == viewer_id:
                viewer = r
                break

    return {
        "metric": metric,
        "rows": top,
        "viewer": viewer,
    }

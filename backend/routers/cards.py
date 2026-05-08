"""
Card read endpoints (catalog browsing).
Fully self-contained — no business logic, just reads from db.cards. Cards
belonging to unreleased series are filtered out so content can be seeded
ahead of launch without leaking to clients.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid
import os
from motor.motor_asyncio import AsyncIOMotorClient

from series_config import released_series_nums

router = APIRouter()

# Reuse the same mongo connection. Both this module and server.py read/write
# the same logical database via the shared env vars.
_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = _client[os.environ["DB_NAME"]]


class Card(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    rarity: str  # common, rare, epic, variant
    front_image_url: str
    back_image_url: str = ""
    coin_cost: int = 100
    available: bool = True
    achievement_required: Optional[int] = None
    streak_required: Optional[int] = None
    engagement_milestone: Optional[str] = None
    series: Optional[int] = None
    series_reward: Optional[int] = None
    band: Optional[str] = None
    card_type: Optional[str] = None
    is_variant: bool = False
    base_card_id: Optional[str] = None
    variant_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


@router.get("/cards")
async def get_all_cards():
    """
    Get all cards from currently-released series.

    Cards belonging to a scheduled / coming-soon series are filtered out so
    Series 7+ data can be seeded ahead of launch without leaking. Rare/epic
    achievement & engagement cards (which carry `series_reward` instead of
    a numeric `series` value, or are series-agnostic) are included only when
    their `series_reward` series — if any — is released.
    """
    released = released_series_nums()
    cards = await db.cards.find({
        "$or": [
            {"series": {"$in": released}},
            # Cards with no series field at all (legacy unscoped cards)
            {"series": {"$exists": False}},
            {"series": None},
        ],
    }).to_list(500)
    # Secondary filter for series_reward-only cards (rare reward cards):
    # if their reward series is unreleased, drop them too.
    filtered = []
    for c in cards:
        sr = c.get("series_reward")
        if sr is not None and sr not in released:
            continue
        filtered.append(c)
    return [Card(**card) for card in filtered]


@router.get("/cards/rare")
async def get_rare_cards():
    """Get all rare achievement cards"""
    rare_cards = await db.cards.find({"rarity": "rare"}).to_list(100)
    return [Card(**rare_card) for rare_card in rare_cards]


@router.get("/cards/epic")
async def get_epic_cards():
    """Get all epic streak cards"""
    epic_cards = await db.cards.find({"rarity": "epic"}).to_list(100)
    return [Card(**epic_card) for epic_card in epic_cards]


@router.get("/cards/{card_id}")
async def get_card(card_id: str):
    """Get a specific card"""
    card = await db.cards.find_one({"id": card_id})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return Card(**card)

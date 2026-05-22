"""
Card read endpoints (catalog browsing).
Fully self-contained — no business logic, just reads from db.cards. Cards
belonging to unreleased series are filtered out so content can be seeded
ahead of launch without leaking to clients.
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from io import BytesIO
from functools import lru_cache
import uuid
import os
import logging
import requests
from PIL import Image
from motor.motor_asyncio import AsyncIOMotorClient

from series_config import released_series_nums
from data.cards_data import VARIANT_SCRATCH_COVERS

router = APIRouter()
log = logging.getLogger(__name__)

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
    scratch_cover_url: Optional[str] = None  # Variant-themed scratch overlay shown on pack-open
    created_at: datetime = Field(default_factory=datetime.utcnow)


def _attach_scratch_cover(card_doc: dict) -> dict:
    """Populate scratch_cover_url on the fly from VARIANT_SCRATCH_COVERS.

    The dict is keyed by lowercase variant_name so e.g. variant_name="Toxic"
    -> covers["toxic"]. Only variant cards get covers; non-variants and
    variants without a registered cover return None (frontend will skip the
    scratch overlay entirely in that case).
    """
    if card_doc.get("is_variant") and card_doc.get("variant_name"):
        key = str(card_doc["variant_name"]).lower()
        card_doc["scratch_cover_url"] = VARIANT_SCRATCH_COVERS.get(key)
    return card_doc


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
    # Card catalog now exceeds 500 entries (S1-S7 totals 567+). The previous
    # `to_list(500)` cap silently truncated, dropping random cards from the
    # response. Bumped to 2000 — enough headroom for ~25 series.
    cards = await db.cards.find({
        "$or": [
            {"series": {"$in": released}},
            # Cards with no series field at all (legacy unscoped cards)
            {"series": {"$exists": False}},
            {"series": None},
        ],
    }).to_list(2000)
    # Secondary filter for series_reward-only cards (rare reward cards):
    # if their reward series is unreleased, drop them too.
    filtered = []
    for c in cards:
        sr = c.get("series_reward")
        if sr is not None and sr not in released:
            continue
        filtered.append(c)
    return [Card(**_attach_scratch_cover(card)) for card in filtered]


@router.get("/cards/rare")
async def get_rare_cards():
    """Get all rare achievement cards"""
    rare_cards = await db.cards.find({"rarity": "rare"}).to_list(100)
    return [Card(**_attach_scratch_cover(rare_card)) for rare_card in rare_cards]


@router.get("/cards/epic")
async def get_epic_cards():
    """Get all epic streak cards"""
    epic_cards = await db.cards.find({"rarity": "epic"}).to_list(100)
    return [Card(**_attach_scratch_cover(epic_card)) for epic_card in epic_cards]


@router.get("/cards/{card_id}")
async def get_card(card_id: str):
    """Get a specific card"""
    card = await db.cards.find_one({"id": card_id})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return Card(**_attach_scratch_cover(card))


# ---------------------------------------------------------------------------
# Thumbnail endpoint
#
# Card images in the catalog point to full-resolution PNGs on S3 (3-5 MB each).
# Rendering a 542-card grid on cellular = ~1.5 GB of pulls = images never finish
# loading on weak signal. This endpoint:
#   1. Fetches the original from S3 (server-side, fast pipe)
#   2. Resizes to a sane width (default 360px wide ~= 25-50 KB JPEG)
#   3. Returns JPEG with aggressive HTTP cache headers
#   4. Caches the resized bytes in-process (LRU 600 entries) so repeat hits skip
#      the S3 round-trip entirely
#
# Trade-off: original PNGs lose transparency, but card faces don't use alpha.
# Pack-reveal screens and zoomed views should keep hitting the original URL.
# ---------------------------------------------------------------------------

# In-process LRU. Each entry ~50 KB × 600 = ~30 MB max — well under Render
# free tier RAM. Cleared on process restart, which is fine since clients also
# cache via HTTP headers.
@lru_cache(maxsize=600)
def _resize_image(url: str, width: int) -> bytes:
    """Synchronously fetch + resize. Cached by (url, width)."""
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    img = Image.open(BytesIO(r.content))
    # Flatten alpha to white so JPEG conversion doesn't trash transparent pixels.
    if img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.convert("RGBA").split()[-1] if img.mode != "P" else None)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    # Preserve aspect ratio; only constrain by width.
    if img.width > width:
        ratio = width / img.width
        new_h = int(img.height * ratio)
        img = img.resize((width, new_h), Image.LANCZOS)
    out = BytesIO()
    img.save(out, format="JPEG", quality=78, optimize=True)
    return out.getvalue()


@router.get("/cards/{card_id}/thumb")
async def get_card_thumb(
    card_id: str,
    w: int = Query(360, ge=80, le=800, description="Target width in pixels"),
):
    """Return a small JPEG thumbnail of the card's front image.

    Aggressive caching: response carries `Cache-Control: public, max-age=31536000,
    immutable` so the device + CDN cache it for a year. Card-image URLs are
    content-addressed on S3, so they never change — safe to cache forever.
    """
    card = await db.cards.find_one({"id": card_id}, {"front_image_url": 1, "_id": 0})
    if not card or not card.get("front_image_url"):
        raise HTTPException(status_code=404, detail="Card or image not found")
    try:
        jpeg_bytes = _resize_image(card["front_image_url"], w)
    except Exception as e:
        log.warning("thumb fetch failed for %s: %s", card_id, e)
        raise HTTPException(status_code=502, detail="Upstream image fetch failed")
    return Response(
        content=jpeg_bytes,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "Vary": "Accept",
        },
    )

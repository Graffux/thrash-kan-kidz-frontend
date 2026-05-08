"""
Card model and initial card data
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


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
    card_type: Optional[str] = None  # "A" or "B"
    is_variant: bool = False
    base_card_id: Optional[str] = None
    variant_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

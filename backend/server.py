from fastapi import FastAPI, APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta, timezone
import base64
import random
import bcrypt
import stripe
from data.cards_data import INITIAL_CARDS, CARD_IMAGE_URLS, CARD_BACK_IMAGE_URLS, RARE_CARD_ACHIEVEMENTS, VARIANT_SCRATCH_COVERS

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env', override=False)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# =====================
# Models
# =====================

class Card(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    rarity: str  # common, rare, epic, variant
    front_image_url: str  # URL to the front image
    back_image_url: str = ""  # URL to the back image
    coin_cost: int = 100
    available: bool = True  # Whether the card is available for purchase
    achievement_required: Optional[int] = None  # Number of cards needed to unlock (for rare cards)
    streak_required: Optional[int] = None  # Number of consecutive login days needed to unlock (for epic cards)
    engagement_milestone: Optional[str] = None  # Type of engagement milestone required (dedicated_fan, big_spender, monthly_master)
    series: Optional[int] = None  # Series number (1, 2, 3, etc.)
    series_reward: Optional[int] = None  # Which series this card is a reward for
    band: Optional[str] = None  # Band name for grouping A/B cards
    card_type: Optional[str] = None  # "A" or "B" for band card variants
    is_variant: bool = False  # Whether this is a variant card
    base_card_id: Optional[str] = None  # The base card this is a variant of
    variant_name: Optional[str] = None  # Name of the variant (e.g., "Toxic", "Electric")
    scratch_cover_url: Optional[str] = None  # Variant-themed scratch-off overlay (only for variants on pack open)
    created_at: datetime = Field(default_factory=datetime.utcnow)


def _with_scratch_cover(card_doc: dict) -> dict:
    """Inject scratch_cover_url onto a card dict from VARIANT_SCRATCH_COVERS.

    Mutates a shallow copy so the caller can safely unpack into ``Card(**...)``.
    Only variant cards get a cover; non-variants or unmapped variants return
    None (frontend skips the scratch overlay in that case).
    """
    out = dict(card_doc)
    if out.get("is_variant") and out.get("variant_name"):
        out["scratch_cover_url"] = VARIANT_SCRATCH_COVERS.get(
            str(out["variant_name"]).lower()
        )
    return out

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    password_hash: str = ""  # Hashed password for authentication
    coins: int = 0
    daily_login_streak: int = 0
    last_login_date: Optional[str] = None
    profile_completed: bool = False
    bio: str = ""
    avatar_url: str = ""
    total_spent_coins: int = 0  # Track total coins spent for Big Spender milestone
    monthly_logins: dict = Field(default_factory=dict)  # Track logins per month {"YYYY-MM": [day1, day2...]}
    unlocked_series: List[int] = Field(default_factory=lambda: [1])  # Series user has access to (starts with series 1)
    completed_series: List[int] = Field(default_factory=list)  # Series user has fully completed
    series_milestone_claimed: List[int] = Field(default_factory=list)  # Series the user has claimed the 100% completion milestone bonus for
    featured_card_ids: List[str] = Field(default_factory=list)  # Up to 5 card IDs the player has pinned to their Profile showcase
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Auth request models
class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class FriendRequest(BaseModel):
    from_user_id: str
    to_user_id: str

class UserCard(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    card_id: str
    quantity: int = 1
    acquired_at: datetime = Field(default_factory=datetime.utcnow)

class Goal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    goal_type: str  # daily_login, profile_complete, collect_coins, collect_cards
    target_value: int
    reward_coins: int
    reward_card_id: Optional[str] = None

class UserGoal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    goal_id: str
    progress: int = 0
    completed: bool = False
    completed_at: Optional[datetime] = None

class Trade(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_user_id: str
    to_user_id: str
    offered_card_ids: List[str]
    requested_card_ids: List[str]
    status: str = "pending"  # pending, accepted, rejected, cancelled
    created_at: datetime = Field(default_factory=datetime.utcnow)

# =====================
# Request/Response Models
# =====================

class CreateUserRequest(BaseModel):
    username: str

class UpdateProfileRequest(BaseModel):
    bio: Optional[str] = None
    avatar_url: Optional[str] = None

class UpdateFeaturedCardsRequest(BaseModel):
    # Up to 5 user-owned card IDs to pin on the Profile showcase. Empty list clears the slots.
    card_ids: List[str]

class ClaimDailyLoginRequest(BaseModel):
    user_id: str

class PurchaseCardRequest(BaseModel):
    user_id: str
    card_id: str

class CreateTradeRequest(BaseModel):
    from_user_id: str
    to_user_id: str
    offered_card_ids: List[str]
    requested_card_ids: List[str]

class TradeActionRequest(BaseModel):
    trade_id: str
    user_id: str
    action: str  # accept, reject, cancel

class SpinWheelRequest(BaseModel):
    user_id: str

# =====================
# Spin Wheel Configuration
# =====================
SPIN_COST = 75  # Coins per pack (3 cards)
REROLL_COST_MEDALS = 1  # Medals to reroll all 3 cards
FREE_PACK_COST_MEDALS = 10  # Medals for a free pack

# Daily Wheel Configuration
DAILY_WHEEL_PRIZES = [
    {"type": "coins", "amount": 25, "label": "25 Coins", "weight": 25},
    {"type": "coins", "amount": 50, "label": "50 Coins", "weight": 20},
    {"type": "coins", "amount": 100, "label": "100 Coins", "weight": 15},
    {"type": "coins", "amount": 200, "label": "200 Coins", "weight": 5},
    {"type": "medals", "amount": 1, "label": "1 Medal", "weight": 20},
    {"type": "medals", "amount": 3, "label": "3 Medals", "weight": 10},
    {"type": "medals", "amount": 5, "label": "5 Medals", "weight": 3},
    {"type": "free_pack", "amount": 1, "label": "Free Pack!", "weight": 2},
]

# =====================
# Series Configuration
# =====================
# SERIES_CONFIG, MAX_DECLARED_SERIES, and the release-scheduling helpers live
# in `series_config.py` so `routers/cards.py` can import them without forming
# a circular dependency through `server.py`. Anything operating on the
# series catalog (validation, completion handlers, /api/series/list) goes
# through these helpers — never hardcode the cap.
from series_config import (  # noqa: E402
    SERIES_CONFIG,
    MAX_DECLARED_SERIES,
    is_series_released,
    released_series_nums,
    current_max_series,
    series_status,
    get_release_date,
    init_overrides as init_series_overrides,
    persist_release_date as persist_series_release_date,
)
from data.ranks import RANKS, compute_user_rank  # noqa: E402
from data.badges import BADGES, COND_SERIES_BASE_COMPLETE, COND_LOGIN_STREAK, COND_TRADES_ACCEPTED, COND_VARIANTS_OWNED, COND_CREATED_BEFORE_SERIES, COND_OWN_ANY_CARD, COND_TOTAL_SPENT, COND_FRIEND_COUNT, COND_OWN_SPECIFIC_CARD  # noqa: E402

class CoinPurchaseRequest(BaseModel):
    user_id: str
    package_id: str
    origin_url: str  # Frontend origin URL for success/cancel redirects

class PaymentTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_id: str
    package_id: str
    amount: float
    currency: str = "usd"
    coins_amount: int
    payment_status: str = "pending"  # pending, paid, failed, expired
    status: str = "initiated"  # initiated, completed, failed
    metadata: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# =====================
# Coin Purchase Packages (Server-side defined - NEVER accept from frontend)
# =====================
COIN_PACKAGES = {
    "small": {
        "id": "small",
        "google_play_product_id": "thrash_kan_kidz_coins_200",
        "name": "Starter Pack",
        "coins": 200,
        "price": 1.99,
        "currency": "usd",
        "description": "200 coins for new collectors",
        "coins_per_dollar": 100.5,
        "bonus_percentage": 0
    },
    "medium": {
        "id": "medium",
        "google_play_product_id": "thrash_kan_kidz_coins_500",
        "name": "Collector Pack",
        "coins": 500,
        "price": 4.99,
        "currency": "usd",
        "description": "500 coins - Best for regular collectors",
        "coins_per_dollar": 100.2,
        "bonus_percentage": 0
    },
    "large": {
        "id": "large",
        "google_play_product_id": "thrash_kan_kidz_coins_1000",
        "name": "Ultimate Pack",
        "coins": 1000,
        "price": 9.99,
        "currency": "usd",
        "description": "1000 coins - Best value!",
        "coins_per_dollar": 100.1,
        "bonus_percentage": 0,
        "best_value": True
    }
}

# Google Play product ID to package mapping
GOOGLE_PLAY_PRODUCT_MAP = {
    pkg["google_play_product_id"]: pkg["id"]
    for pkg in COIN_PACKAGES.values()
}

# First-time purchase bonus
FIRST_PURCHASE_BONUS_PERCENTAGE = 50  # 50% extra coins on first purchase

# =====================
# Seed Data - Series 1 Cards (8 bands, 16 cards)
# =====================

CARD_IMAGE_URLS = {
    # Band 1: $LAYA
    "tom_da_playa": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/8p3eb259_file_00000000172471f8a3d8c4e632f699f7.png",
    "chum_araya": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/19mw7g72_file_000000008df471f5b300702b42b32cd0.png",
    # Tom Da Playa Variants
    "tom_da_playa_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/8ijovlfp_enhanced-1773602336149.jpg",
    "tom_da_playa_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/3q3w1vwe_enhanced-1773602540143.jpg",
    "tom_da_playa_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/qeil0ghj_enhanced-1773618665694.jpg",
    "tom_da_playa_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/741jupbe_enhanced-1773618832172.jpg",
    # Chum Araya Variants
    "chum_araya_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/p2swl9mk_enhanced-1774166623212.jpg",
    "chum_araya_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/1gk3o5lo_enhanced-1774166736101.jpg",
    "chum_araya_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/t7rcvvon_enhanced-1774166884359.jpg",
    "chum_araya_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/d0ln8fri_enhanced-1774166976308.jpg",
    # Band 2: Megadef
    "musty_dave": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/nggi41l4_file_00000000319871f583003b0145086e96.png",
    "daves_mustang": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/8t15nt7u_file_0000000079ec71fdbe0a31c88426db30.png",
    # Dave's Mustang Variants
    "daves_mustang_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/hmkamrxq_enhanced-1774169523717.jpg",
    "daves_mustang_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/prdcq3g3_enhanced-1774169621597.jpg",
    "daves_mustang_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/mt88cv38_enhanced-1774169804783.jpg",
    "daves_mustang_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/h971vlcd_enhanced-1774169992545.jpg",
    # Musty Dave Variants
    "musty_dave_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/qgxycgo3_enhanced-1774167107939.jpg",
    "musty_dave_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/x1stt0y5_enhanced-1774167202963.jpg",
    "musty_dave_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/yw3e73lp_enhanced-1774167306194.jpg",
    "musty_dave_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/cazix3sc_enhanced-1774167385926.jpg",
    # Band 3: Sepulchura
    "maxi_pad": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/6cc9oltm_file_000000000a5471f5ae6a72ba59efab72.png",
    "maximum": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/2revzgsz_file_000000000f8c71f5a1ceebe96981364d.png",
    # Maxi Pad Variants
    "maxi_pad_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/itufg769_file_00000000ce5071fd9678d1143ae8b19c.png",
    "maxi_pad_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/jnosp4ca_file_00000000636c722faa0ead59b1aab559.png",
    "maxi_pad_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/a1u4ygu4_file_000000008cf0722fb6a4ff38e9edd7f0.png",
    "maxi_pad_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/fwqzpzlu_file_0000000016ec71f5b0764ebedc2590f5.png",
    # Maximum Variants
    "maximum_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/gidcqv6f_file_0000000008c0722f967622ac6d44f172.png",
    "maximum_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/qcyw3z6g_file_00000000b5fc722fb5faa6f099123dbb.png",
    "maximum_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/qen1z2pk_file_000000003f60722f934e1828af65a56d.png",
    "maximum_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/3k1a9dub_file_00000000684071f5956c32e7b432127d.png",
    # Band 4: Testyment
    "billy_chuck": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/wyz5xr3e_file_00000000fb00722fa6b9aa0e95bdfee0.png",
    "chuck_roast": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/tt9zf49y_file_000000009cf471fd9f9ec310d1d825f1%20%282%29.png",
    # Billy Chuck Variants
    "billy_chuck_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/4elgkv20_enhanced-1774205918055.jpg",
    "billy_chuck_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/tg5h8pxn_enhanced-1774206040191.jpg",
    "billy_chuck_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/j8l0vapq_enhanced-1774206227254.jpg",
    "billy_chuck_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/oqh3kmd8_enhanced-1774206317657.jpg",
    # Chuck Roast Variants
    "chuck_roast_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/h79t7f20_enhanced-1774206412636.jpg",
    "chuck_roast_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/hsi6fsfh_enhanced-1774206558892.jpg",
    "chuck_roast_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/ppaobxx7_enhanced-1774206845954.jpg",
    "chuck_roast_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/lsc02h95_enhanced-1774206935519.jpg",
    # Band 5: Metallikuh
    "cliff_diver": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/3253t70u_file_00000000da2c71f8a3882344e443bca5.png",
    "cliff_burpin": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/vj8zbqec_file_00000000efb871f8aff2dad98e7da9e0.png",
    # Cliff Diver Variants
    "cliff_diver_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/mc5ce0am_file_00000000b28471f59ee4f09204ae8b4c.png",
    "cliff_diver_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/gvht2fcl_file_00000000e45871f58bb0cd737a148e65.png",
    "cliff_diver_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/cbcqxk2v_file_00000000be2871f89046161bc2021442.png",
    "cliff_diver_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/pkla48mo_file_000000007b9071fd99ae61a5d7af6f09.png",
    # Cliff Burpin Variants
    "cliff_burpin_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/71biwhb5_file_000000000ee4722fa9c2b4c0f6b3139f.png",
    "cliff_burpin_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/4p896zhf_enhanced-1774674468823.jpg",
    "cliff_burpin_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/irnn5899_file_00000000d8f471fd957140f6f64fbc5e.png",
    "cliff_burpin_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/2kd1s8h7_file_00000000b06071f8803d4356e2c07470.png",
    # Band 6: Anthrash
    "scotch_ian": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/wfx5afyp_file_0000000067c071fd8fbea79ea1359879.png",
    # Scotch Ian Variants
    "scotch_ian_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/0vxhdv3x_file_00000000a2cc71fd9e0d49ab78036784.png",
    "scotch_ian_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/979s4bg7_file_000000000f4871f8a0e8899b1e56bc1f.png",
    "scotch_ian_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/puhuton7_file_000000001964722fbd1c833ab3337e12.png",
    "scotch_ian_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/vvma6lix_file_000000003cdc71fbae9f27b5061a4d98.png",
    "scott_eaten": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/g7kyk9s9_file_00000000d70c71fdb7b87b53d2b770cd.png",
    # Scott Eaten Variants
    "scott_eaten_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/8wm9sb0k_file_00000000ee6c71fd8223cc73a03471a6.png",
    "scott_eaten_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/u6tv4vgp_file_00000000bc7c71fdba47c183ea1bd559.png",
    "scott_eaten_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/dmse8kub_file_00000000dd60722f970c4f446e24ed56.png",
    "scott_eaten_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/6c4kgqg4_file_00000000dc18722f93a43028ec656e4f.png",
    # Band 7: Kreaturd
    "silly_mille": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/paaodduf_file_0000000018b871fda0fd7e44b8c11def.png",
    "mille_gorezza": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/g91wp9yv_file_000000002b6871f8adc873413d3619f3.png",
    # Silly Mille Variants
    "silly_mille_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/yxz0k3vt_file_0000000064a071f5aa5f311ef7df96ec.png",
    "silly_mille_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/c4ieu7h8_file_00000000d45c722f8144b642c24a0ed1.png",
    "silly_mille_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/rnv4fjhr_file_00000000a3e471fbbd30932d141bb0fc.png",
    "silly_mille_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/55afmtp5_file_00000000888071fb925da62eb81eea9f.png",
    # Mille Gorezza Variants
    "mille_gorezza_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/ow7acz7e_file_00000000924471fdb60a336062ff095a.png",
    "mille_gorezza_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/z0rbyxim_file_00000000620c71fdb6ba2e714e615181.png",
    "mille_gorezza_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/tub6n8uk_file_00000000242071fd8bfc8c00e401fbe3.png",
    "mille_gorezza_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/vub685gp_file_000000003f0471f59809c0b94b90116d.png",
    # Band 8: Eggsodus
    "paul_bawl_off": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/qwai8wue_file_00000000442871fd8945003a4fd9662a.png",
    # Paul Bawl Off Variants
    "paul_bawl_off_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/qpl9cxot_file_00000000d00471fb8822de231e69e17e.png",
    "paul_bawl_off_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/wa8zr17p_file_00000000d48871fd82860c470018e081.png",
    "paul_bawl_off_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/q9u38yoo_file_00000000c50071f8ab272c1ec07d5bf3.png",
    "paul_bawl_off_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/epkvtm5w_file_00000000526471f89cb084328cb8f62f.png",
    "blood_bonder": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/63m30i4q_file_00000000a374722f8343b54e3a06558f.png",
    # Blood Bonder Variants
    "blood_bonder_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/g1gj4638_file_000000009c7c722fa8d83b8cb6c61f3b.png",
    "blood_bonder_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/w8bozxys_file_000000005390722faad4ad5fc2e117aa.png",
    "blood_bonder_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/x2b5h7d0_file_00000000beb071f59440c7ab80f96f0a.png",
    "blood_bonder_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/zkg799uk_file_00000000357071f58e97192639f90e1b.png",
    # Rare achievement cards (Series completion rewards)
    "kerry_the_king": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/gfh1huso_file_000000001f5071fd88973aa9c05bebac.png",
    "strap_on_taylor": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/ruqqtjrv_file_00000000ca38722f86b98bf35e6892e2.png",
    # =====================
    # SERIES 2 CARDS - Front Images
    # =====================
    # Band 1: Construction
    "smeared_schmier": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/jshleumx_enhanced-1771278042580.jpg",
    # Smeared Schmier Variants
    "smeared_schmier_bloodbath": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/1kge2loz_file_00000000caa071fdbe4eb5d61e2f9138.png",
    "smeared_schmier_ice": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/7ky8bjoa_file_000000009c3071fd844145018bca9441.png",
    "smeared_schmier_psychedelic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/ok3xdw4b_file_00000000ab4071fda2bcb5f8eb22a220.png",
    "smeared_schmier_biomechanical": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/a9oasf2f_file_00000000432071fdb28eabcd111ceaa1.png",
    "beer_schmier": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/lutlvn34_enhanced-1771279297015.jpg",
    # Beer Schmier Variants
    "beer_schmier_bloodbath": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/9t6m1r4d_file_00000000333471fd9e68b65a1c5fefe0.png",
    "beer_schmier_ice": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/k8v188j5_file_00000000faf071fda77eb92f27226ff0.png",
    "beer_schmier_psychedelic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/kthvupwq_file_00000000bd9871f5a03ad06c03c4cbbb.png",
    "beer_schmier_biomechanical": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/83x9qu5o_file_00000000c3d071fd964f422deec4fecc.png",
    # Band 2: Voivodka
    "piggy_in_a_blanket": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/dpfv01yo_enhanced-1771278142034.jpg",
    # Piggy in a Blanket Variants
    "piggy_in_a_blanket_bloodbath": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/7ausfquy_file_000000007b4071f5b73d200c35225f35.png",
    "piggy_in_a_blanket_ice": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/3os4mgu1_file_00000000a35c722fb4e343a7069b26ba.png",
    "piggy_in_a_blanket_psychedelic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/sb7p4pej_file_000000006534722f96b6b7103c74b005.png",
    "piggy_in_a_blanket_biomechanical": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/7zknda8j_file_00000000a1fc71f5890e45a8cca1352e.png",
    "rotting_away": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/0bqomm5i_enhanced-1771278196496.jpg",
    # Rotting Away Variants
    "rotting_away_bloodbath": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/zp2cnvz4_file_000000009c4c722f9c290211c77abc32.png",
    "rotting_away_ice": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/rcqmp28y_file_00000000740871f580fc8a4537496ebc.png",
    "rotting_away_psychedelic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/ulu36sy8_file_00000000e240722f924f92f4b0b4f50f.png",
    "rotting_away_biomechanical": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/1brkt1la_file_000000003a9c722f8c67113dd520abd0.png",
    # Band 3: Hallows Heave
    "tommy_stewart": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/k4dqnji8_enhanced-1771278246182.jpg",
    # Tommy Stewart Variants
    "tommy_stewart_bloodbath": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/e4uik3pv_file_00000000f6e071f8882de66a8557a169.png",
    "tommy_stewart_ice": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/xxv96r0f_file_00000000b43871fda4c35295cf7390db.png",
    "tommy_stewart_psychedelic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/vpzhq4cm_file_00000000612871f88b5f91b298325a76.png",
    "tommy_stewart_biomechanical": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/adraiy0y_file_00000000446071f8864335af1f30030a.png",
    "tommy_spewart": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/f61hd5kz_enhanced-1771278293743.jpg",
    # Tommy Spewart Variants
    "tommy_spewart_bloodbath": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/l9cehmsx_file_0000000032e471f8b3bb69e79bb36030.png",
    "tommy_spewart_ice": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/0qbjl54p_file_00000000e4b871fdb1054996d5bbce6f.png",
    "tommy_spewart_psychedelic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/c5x56s9a_file_000000003c4471f8bedd0b1b70e8df4a.png",
    "tommy_spewart_biomechanical": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/25jwdchg_file_00000000448c71fdbe6c4f2338bcf41c.png",
    # Band 4: Pussessed
    "jeff_possess_ya_s2": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/jzgfyc6y_enhanced-1771278343087.jpg",
    # Jeff Possess Ya Variants
    "jeff_possess_ya_s2_bloodbath": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/sko2mg1w_file_00000000e43c722facc931a950c73822.png",
    "jeff_possess_ya_s2_ice": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/7ra8qofd_file_00000000b85c71f5b52b0e719aa774d8.png",
    "jeff_possess_ya_s2_psychedelic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/0wcfw7ln_file_00000000414c71f5b0779143a7f60123.png",
    "jeff_possess_ya_s2_biomechanical": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/cu4c31u3_file_0000000047d4722fa70d135c54f6eeb8.png",
    "chef_becerra": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/iz6crfrh_enhanced-1771278405486.jpg",
    # Chef Becerra Variants
    "chef_becerra_bloodbath": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/x7y4u9qv_file_000000003dcc722f9493a7b764ccbd7a.png",
    "chef_becerra_ice": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/ylq0jem0_file_00000000561071f59a0d40c1717ff235.png",
    "chef_becerra_psychedelic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/ocoxl9fb_file_000000002968722f9b43e07d92424afe.png",
    "chef_becerra_biomechanical": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/ieq76zc7_file_00000000466471f5b296a59b24a0e552.png",
    # Band 5: S.T.D.
    "bully_milano": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/rrqcmuzv_enhanced-1771278534417.jpg",
    # Bully Milano Variants
    "bully_milano_bloodbath": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/xg9q7tmu_file_000000002ff0722fa1bcec7fdecc3a58.png",
    "bully_milano_ice": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/1s53wnt7_file_00000000a4fc722fb1fbb27de3f0cec5.png",
    "bully_milano_psychedelic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/mhg2fovw_file_00000000af84722fb0ab4b66f6f00771.png",
    "bully_milano_biomechanical": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/ih7ih44l_file_00000000a6d071f5bff6136380f6f8cc.png",
    "billy_mylanta": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/5mr9wy38_enhanced-1771278589241.jpg",
    # Billy Mylanta Variants
    "billy_mylanta_bloodbath": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/fad7md56_file_00000000f0b4722f99ff248a683bda81.png",
    "billy_mylanta_ice": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/tix9wkpe_file_0000000005b071f5b38bdd77f001aeb5.png",
    "billy_mylanta_psychedelic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/crzi5bte_file_000000005250722f87d13de42f4c702f.png",
    "billy_mylanta_biomechanical": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/4lzzq94u_file_00000000f1ac71f586e113e856bdde57.png",
    # Band 6: Sodumb
    "tom_angeltipper": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/kopt4n28_enhanced-1771278644576.jpg",
    # Tom Angeltipper Variants
    "tom_angeltipper_bloodbath": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/yrxwxwg8_file_000000004458722fafb993524e957280.png",
    "tom_angeltipper_ice": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/5u7rau5t_file_000000004c6071f5879ceb73630534e4.png",
    "tom_angeltipper_psychedelic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/er6nkpjt_file_000000002e90722fbd1dd4539682f0de.png",
    "tom_angeltipper_biomechanical": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/orhnkc9q_file_000000001a4071f59cc34259021437b7.png",
    "tom_angelflipper": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/pli2mcqj_enhanced-1771278822551.jpg",
    # Tom Angelflipper Variants
    "tom_angelflipper_bloodbath": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/w9jxdjnr_file_00000000735471f59d340025ba270a9c.png",
    "tom_angelflipper_ice": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/3nnmp0jy_file_00000000ecf871f5bf2cfe681d6dfff7.png",
    "tom_angelflipper_psychedelic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/35ri9jnz_file_000000001d78722f95d7a5a44a627feb.png",
    "tom_angelflipper_biomechanical": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/t64siqy9_file_00000000ebe071f5812f8e6817887525.png",
    # Band 7: Sacrud Ryche
    "philled_up": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/a4luonk7_enhanced-1771278919638.jpg",
    # Philled Up Variants
    "philled_up_bloodbath": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/x0yr166c_file_00000000ce2471fda82439cc818dd6b5.png",
    "philled_up_ice": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/15r3ssr0_file_000000002bb8722fa57b9562422f87b7.png",
    "philled_up_psychedelic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/89gx29li_file_000000001ec471f5908b351ce1209fad.png",
    "philled_up_biomechanical": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/xhmhc77w_file_0000000037d0722fac383d7ad8ea4d3a.png",
    "phil_grind": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/535v6r16_enhanced-1771278999569.jpg",
    # Phil Grind Variants
    "phil_grind_bloodbath": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/z5cuo22s_file_00000000ac88722fa1b156df4828028d.png",
    "phil_grind_ice": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/joed1hef_file_00000000bf4071f58a8a96f6ab628567.png",
    "phil_grind_psychedelic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/ugt3jsoa_file_0000000047c871f5b916416de198a3c8.png",
    "phil_grind_biomechanical": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/wboewn3l_file_00000000012071f8818bc88eb150b4e6.png",
    # Band 8: Dork Angel
    "don_doody": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/zb0sa00g_enhanced-1771279108828.jpg",
    # Don Doody Variants
    "don_doody_bloodbath": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/agbprfjp_file_00000000749c722f90cd6da49dbfd536.png",
    "don_doody_ice": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/1g2s5129_file_000000008d14722f93f4775fef82125e.png",
    "don_doody_psychedelic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/804wwp3d_file_000000009430722f8696911ebe26c81b.png",
    "don_doody_biomechanical": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/m8zezmdk_file_00000000567871f5914537bed5604952.png",
    "don_rotty": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/im3hu6sw_enhanced-1771279057803.jpg",
    # Don Rotty Variants
    "don_rotty_bloodbath": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/ttif47x7_file_000000005160722fbceac1f2323fad0e.png",
    "don_rotty_ice": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/83wu0ydg_file_00000000fbe0722fa6e67badbf2932ee.png",
    "don_rotty_psychedelic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/015dfeaa_file_00000000f844722fbddca5b8bf26c14d.png",
    "don_rotty_biomechanical": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/wmjcdh1f_file_000000005c5471f5996b99da5d585e71.png",
    # =====================
    # SERIES 3 CARDS - Front Images
    # =====================
    # Band 1: Underkill
    "nobby_blitz": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/da8apu4g_file_000000002df871fd8b305fcf9ab03516.png",
    "bobby_blitzed": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/lu063bq0_enhanced-1773629964983.jpg",
    # Band 2: Meadow Church
    "david_whine": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/7ozsynle_enhanced-1771761544757.jpg",
    "david_slayne": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/lbqueqph_enhanced-1771761582312.jpg",
    # Band 3: Sabutt
    "martini_walkyier": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/c2di7ijf_enhanced-1771761620137.jpg",
    "martin_wankyier": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/7q2a177y_enhanced-1771761655080.jpg",
    # Band 4: Celtic Frosty
    "tom_g_worrier": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/nwq6liuo_enhanced-1772424120932.jpg",
    "tom_g_wore_out": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/sicmrezn_enhanced-1772424264300.jpg",
    # Band 5: Venum
    "coronos": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/b6qbwv4h_enhanced-1772913854119.jpg",
    "groanos": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/f227o83l_enhanced-1772914984744.jpg",
    # Band 6: Sadust
    "darren_travesty": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/mcvafkhx_enhanced-1772919382679.jpg",
    "daring_travis": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/zs0t04mj_enhanced-1772919920441.jpg",
    # Band 7: High Racks
    "cretin_w_de_pena": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/bvbuwu6q_enhanced-1772996050805.jpg",
    "katon_de_pain": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/g5w4jwav_enhanced-1772997297722.jpg",
    # Band 8: Suckrifice
    "rob_urinati": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/sir3iy8h_enhanced-1773074599887.jpg",
    "slob_urbinati": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/at4glnr4_enhanced-1774075087938.jpg",
    # Epic reward card (Series 3)
    "sean_kill_again": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/lxq89ltr_file_000000007a0471f5a1da1f0e20a9b30a.png",
}

CARD_BACK_IMAGE_URLS = {
    # =====================
    # UNIVERSAL VARIANT BACKS - SERIES 1
    # =====================
    "variant_back_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/wgs923tx_file_000000002efc71f884f1688fbde05ac5.png",
    "variant_back_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/rfifnity_enhanced-1774169687540.jpg",
    "variant_back_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/xlpkt804_enhanced-1774169889456.jpg",
    "variant_back_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/dvr1ivtp_enhanced-1774170032529.jpg",
    # =====================
    # UNIVERSAL VARIANT BACKS - SERIES 2
    # =====================
    "variant_back_bloodbath": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/yc5wu6dn_file_00000000f364722f9b732847c2e993b5.png",
    "variant_back_ice": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/qctkgz9n_file_00000000277c71f5ada9f7e68128291d.png",
    "variant_back_psychedelic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/eg5va8ej_file_00000000373c71f59e06f259b07329a2.png",
    "variant_back_biomechanical": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/7p1jdb1p_file_00000000e13871f59e228eb1381b39aa.png",
    # =====================
    # Band 1: $LAYA
    "tom_da_playa": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/jlg546ha_file_00000000369c71f580be8b548f7c5be7.png",
    "chum_araya": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/ah6bgu7l_file_000000002aa0722fb5a83a6a51706776.png",
    # Tom Da Playa Variants (use same as front)
    "tom_da_playa_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/8ijovlfp_enhanced-1773602336149.jpg",
    "tom_da_playa_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/3q3w1vwe_enhanced-1773602540143.jpg",
    "tom_da_playa_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/qeil0ghj_enhanced-1773618665694.jpg",
    "tom_da_playa_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/741jupbe_enhanced-1773618832172.jpg",
    # Chum Araya Variants (use same as front)
    "chum_araya_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/p2swl9mk_enhanced-1774166623212.jpg",
    "chum_araya_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/1gk3o5lo_enhanced-1774166736101.jpg",
    "chum_araya_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/t7rcvvon_enhanced-1774166884359.jpg",
    "chum_araya_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/d0ln8fri_enhanced-1774166976308.jpg",
    # Band 2: Megadef
    "musty_dave": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/z7kf9k7g_file_00000000ae7c722f8927ccf43d190b52.png",
    "daves_mustang": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/05n3fgpt_file_000000008f0471fd8eb6563d4dc546d5.png",
    # Musty Dave Variants (use same as front)
    "musty_dave_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/qgxycgo3_enhanced-1774167107939.jpg",
    "musty_dave_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/x1stt0y5_enhanced-1774167202963.jpg",
    "musty_dave_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/yw3e73lp_enhanced-1774167306194.jpg",
    "musty_dave_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/cazix3sc_enhanced-1774167385926.jpg",
    # Band 3: Sepulchura
    "maxi_pad": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/rstninpu_file_00000000ed6c71f8801642ff21a5d10f.png",
    "maximum": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/xkztrnkt_file_00000000ea9871f8985aecfb04305ed7.png",
    # Maxi Pad Variants (use same as front)
    "maxi_pad_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/itufg769_file_00000000ce5071fd9678d1143ae8b19c.png",
    "maxi_pad_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/jnosp4ca_file_00000000636c722faa0ead59b1aab559.png",
    "maxi_pad_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/a1u4ygu4_file_000000008cf0722fb6a4ff38e9edd7f0.png",
    "maxi_pad_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/fwqzpzlu_file_0000000016ec71f5b0764ebedc2590f5.png",
    # Maximum Variants (use same as front)
    "maximum_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/gidcqv6f_file_0000000008c0722f967622ac6d44f172.png",
    "maximum_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/qcyw3z6g_file_00000000b5fc722fb5faa6f099123dbb.png",
    "maximum_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/qen1z2pk_file_000000003f60722f934e1828af65a56d.png",
    "maximum_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/3k1a9dub_file_00000000684071f5956c32e7b432127d.png",
    # Band 4: Testyment
    "billy_chuck": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/hxqdjff7_file_00000000a10c71f884e6b3625a31bd00.png",
    "chuck_roast": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/m158yvhx_file_00000000ee187230978fd25aac62ddc5.png",
    # Billy Chuck Variants (use same as front)
    "billy_chuck_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/4elgkv20_enhanced-1774205918055.jpg",
    "billy_chuck_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/tg5h8pxn_enhanced-1774206040191.jpg",
    "billy_chuck_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/j8l0vapq_enhanced-1774206227254.jpg",
    "billy_chuck_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/oqh3kmd8_enhanced-1774206317657.jpg",
    # Chuck Roast Variants (use same as front)
    "chuck_roast_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/h79t7f20_enhanced-1774206412636.jpg",
    "chuck_roast_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/hsi6fsfh_enhanced-1774206558892.jpg",
    "chuck_roast_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/ppaobxx7_enhanced-1774206845954.jpg",
    "chuck_roast_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/lsc02h95_enhanced-1774206935519.jpg",
    # Band 5: Metallikuh
    "cliff_diver": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/qpm4wvvq_file_0000000079d471f88a22462a2aded95c.png",
    "cliff_burpin": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/4yuf3wp5_file_00000000475471fd8fee6d503fb9b32c.png",
    # Cliff Diver Variants (use same as front)
    "cliff_diver_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/mc5ce0am_file_00000000b28471f59ee4f09204ae8b4c.png",
    "cliff_diver_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/gvht2fcl_file_00000000e45871f58bb0cd737a148e65.png",
    "cliff_diver_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/cbcqxk2v_file_00000000be2871f89046161bc2021442.png",
    "cliff_diver_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/pkla48mo_file_000000007b9071fd99ae61a5d7af6f09.png",
    # Cliff Burpin Variants (use same as front)
    "cliff_burpin_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/71biwhb5_file_000000000ee4722fa9c2b4c0f6b3139f.png",
    "cliff_burpin_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/4p896zhf_enhanced-1774674468823.jpg",
    "cliff_burpin_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/irnn5899_file_00000000d8f471fd957140f6f64fbc5e.png",
    "cliff_burpin_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/2kd1s8h7_file_00000000b06071f8803d4356e2c07470.png",
    # Band 6: Anthrash
    "scotch_ian": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/ecjxi0zu_file_0000000058b071fda35cc951b6f03a0b.png",
    # Scotch Ian Variants (use same as front)
    "scotch_ian_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/0vxhdv3x_file_00000000a2cc71fd9e0d49ab78036784.png",
    "scotch_ian_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/979s4bg7_file_000000000f4871f8a0e8899b1e56bc1f.png",
    "scotch_ian_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/puhuton7_file_000000001964722fbd1c833ab3337e12.png",
    "scotch_ian_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/vvma6lix_file_000000003cdc71fbae9f27b5061a4d98.png",
    "scott_eaten": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/mgyvbjh8_file_00000000c9dc71fdb2de5295e9fe4e18.png",
    # Scott Eaten Variants (use same as front)
    "scott_eaten_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/8wm9sb0k_file_00000000ee6c71fd8223cc73a03471a6.png",
    "scott_eaten_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/u6tv4vgp_file_00000000bc7c71fdba47c183ea1bd559.png",
    "scott_eaten_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/dmse8kub_file_00000000dd60722f970c4f446e24ed56.png",
    "scott_eaten_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/6c4kgqg4_file_00000000dc18722f93a43028ec656e4f.png",
    # Band 7: Kreaturd
    "silly_mille": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/jfks6ym6_file_0000000044cc71f5b295bcd8f73d0398.png",
    "mille_gorezza": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/1asg9g5i_file_00000000674c71f5a6ddd9c12c7ffcdb.png",
    # Silly Mille Variants
    "silly_mille_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/yxz0k3vt_file_0000000064a071f5aa5f311ef7df96ec.png",
    "silly_mille_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/c4ieu7h8_file_00000000d45c722f8144b642c24a0ed1.png",
    "silly_mille_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/rnv4fjhr_file_00000000a3e471fbbd30932d141bb0fc.png",
    "silly_mille_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/55afmtp5_file_00000000888071fb925da62eb81eea9f.png",
    # Mille Gorezza Variants (use same as front)
    "mille_gorezza_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/ow7acz7e_file_00000000924471fdb60a336062ff095a.png",
    "mille_gorezza_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/z0rbyxim_file_00000000620c71fdb6ba2e714e615181.png",
    "mille_gorezza_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/tub6n8uk_file_00000000242071fd8bfc8c00e401fbe3.png",
    "mille_gorezza_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/vub685gp_file_000000003f0471f59809c0b94b90116d.png",
    # Band 8: Eggsodus
    "paul_bawl_off": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/9dv3gzga_file_00000000b82471fdb1ce4df389a3cdb3.png",
    # Paul Bawl Off Variants (use same as front)
    "paul_bawl_off_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/qpl9cxot_file_00000000d00471fb8822de231e69e17e.png",
    "paul_bawl_off_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/wa8zr17p_file_00000000d48871fd82860c470018e081.png",
    "paul_bawl_off_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/q9u38yoo_file_00000000c50071f8ab272c1ec07d5bf3.png",
    "paul_bawl_off_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/epkvtm5w_file_00000000526471f89cb084328cb8f62f.png",
    "blood_bonder": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/uknhwlhn_file_00000000e53871f8b1042baf1259181b.png",
    # Blood Bonder Variants (use same as front)
    "blood_bonder_toxic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/g1gj4638_file_000000009c7c722fa8d83b8cb6c61f3b.png",
    "blood_bonder_electric": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/w8bozxys_file_000000005390722faad4ad5fc2e117aa.png",
    "blood_bonder_hellfire": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/x2b5h7d0_file_00000000beb071f59440c7ab80f96f0a.png",
    "blood_bonder_cosmic": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/zkg799uk_file_00000000357071f58e97192639f90e1b.png",
    # Rare achievement cards backs (Series completion rewards)
    "kerry_the_king": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/cwro1dog_file_00000000833071fd8adc51da518e9550.png",
    "strap_on_taylor": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/gz3tkef8_file_000000009ed8722f84c332f7ccad83d3.png",
    # =====================
    # SERIES 2 CARDS - Back Images
    # =====================
    # Band 1: Construction
    "smeared_schmier": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/yg8itc9l_enhanced-1771279344907.jpg",
    "beer_schmier": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/4lnsur9c_enhanced-1771278098766.jpg",
    # Band 2: Voivodka
    "piggy_in_a_blanket": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/fsqnoadq_enhanced-1771279398630.jpg",
    "rotting_away": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/1degzzdp_enhanced-1771280167989.jpg",
    # Band 3: Hallows Heave
    "tommy_stewart": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/yg9odtro_enhanced-1771279654471.jpg",
    "tommy_spewart": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/gujcwvzv_enhanced-1771279709991.jpg",
    # Band 4: Pussessed
    "jeff_possess_ya_s2": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/2l91fiuc_enhanced-1771279762052.jpg",
    "chef_becerra": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/qzejza95_enhanced-1771279833088.jpg",
    # Band 5: S.T.D.
    "bully_milano": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/lbi2bhyy_enhanced-1771279972254.jpg",
    "billy_mylanta": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/kyb5n9e1_enhanced-1771279912493.jpg",
    # Band 6: Sodumb
    "tom_angeltipper": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/mp5t3bry_enhanced-1771280220248.jpg",
    "tom_angelflipper": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/1m6d57zq_enhanced-1771280277113.jpg",
    # Band 7: Sacrud Ryche
    "philled_up": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/v26i4x7g_enhanced-1771280383938.jpg",
    "phil_grind": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/ds8y9a3p_enhanced-1771280329984.jpg",
    # Band 8: Dork Angel
    "don_doody": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/nsh58hp1_enhanced-1771280036887.jpg",
    "don_rotty": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/8xmjtls4_enhanced-1771280085627.jpg",
    # =====================
    # SERIES 3 CARDS - Back Images (using front images as placeholders)
    # =====================
    # Band 1: Underkill
    "nobby_blitz": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/da8apu4g_file_000000002df871fd8b305fcf9ab03516.png",
    "bobby_blitzed": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/lu063bq0_enhanced-1773629964983.jpg",
    # Band 2: Meadow Church
    "david_whine": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/7ozsynle_enhanced-1771761544757.jpg",
    "david_slayne": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/lbqueqph_enhanced-1771761582312.jpg",
    # Band 3: Sabutt
    "martini_walkyier": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/c2di7ijf_enhanced-1771761620137.jpg",
    "martin_wankyier": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/7q2a177y_enhanced-1771761655080.jpg",
    # Band 4: Celtic Frosty
    "tom_g_worrier": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/nwq6liuo_enhanced-1772424120932.jpg",
    "tom_g_wore_out": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/sicmrezn_enhanced-1772424264300.jpg",
    # Band 5: Venum
    "coronos": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/b6qbwv4h_enhanced-1772913854119.jpg",
    "groanos": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/f227o83l_enhanced-1772914984744.jpg",
    # Band 6: Sadust
    "darren_travesty": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/mcvafkhx_enhanced-1772919382679.jpg",
    "daring_travis": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/zs0t04mj_enhanced-1772919920441.jpg",
    # Band 7: High Racks
    "cretin_w_de_pena": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/bvbuwu6q_enhanced-1772996050805.jpg",
    "katon_de_pain": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/g5w4jwav_enhanced-1772997297722.jpg",
    # Band 8: Suckrifice
    "rob_urinati": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/sir3iy8h_enhanced-1773074599887.jpg",
    "slob_urbinati": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/at4glnr4_enhanced-1774075087938.jpg",
    # Epic reward card (Series 3)
    "sean_kill_again": "https://customer-assets.emergentagent.com/job_d9b7563a-44d0-4dcc-ab9c-25c405b50d3f/artifacts/lxq89ltr_file_000000007a0471f5a1da1f0e20a9b30a.png",
}

# Rare card achievement requirements (Series completion rewards)
RARE_CARD_ACHIEVEMENTS = {
    "card_kerry_the_king": {"required_cards": 16, "name": "Kerry The King"},  # Complete Series 1
    "card_strap_on_taylor": {"required_cards": 32, "name": "Strap-On Taylor"},  # Complete Series 2
    "card_sean_kill_again": {"required_cards": 48, "name": "Sean Kill-Again"}  # Complete Series 3
}


INITIAL_GOALS = [
    {
        "id": "goal_daily_login_30",
        "title": "30 Day Streak",
        "description": "Log in for 30 consecutive days",
        "goal_type": "daily_login",
        "target_value": 30,
        "reward_coins": 300,
        "reward_card_id": None
    },
    {
        "id": "goal_daily_login_60",
        "title": "60 Day Streak",
        "description": "Log in for 60 consecutive days",
        "goal_type": "daily_login",
        "target_value": 60,
        "reward_coins": 600,
        "reward_card_id": None
    },
    {
        "id": "goal_collect_cards_100",
        "title": "Card Hoarder",
        "description": "Collect 100 cards total",
        "goal_type": "collect_cards",
        "target_value": 100,
        "reward_coins": 500,
        "reward_card_id": None
    },
    {
        "id": "goal_collect_cards_150",
        "title": "Card Connoisseur",
        "description": "Collect 150 cards total",
        "goal_type": "collect_cards",
        "target_value": 150,
        "reward_coins": 750,
        "reward_card_id": None
    },
    {
        "id": "goal_collect_cards_200",
        "title": "Card Maniac",
        "description": "Collect 200 cards total",
        "goal_type": "collect_cards",
        "target_value": 200,
        "reward_coins": 1000,
        "reward_card_id": None
    },
    {
        "id": "goal_all_variants_s1",
        "title": "Series 1 Variant Master",
        "description": "Collect every variant in Series 1",
        "goal_type": "collect_all_variants_series",
        "target_value": 1,
        "reward_coins": 500,
        "reward_card_id": None
    },
    {
        "id": "goal_all_variants_s2",
        "title": "Series 2 Variant Master",
        "description": "Collect every variant in Series 2",
        "goal_type": "collect_all_variants_series",
        "target_value": 2,
        "reward_coins": 500,
        "reward_card_id": None
    },
    {
        "id": "goal_all_variants_s3",
        "title": "Series 3 Variant Master",
        "description": "Collect every variant in Series 3",
        "goal_type": "collect_all_variants_series",
        "target_value": 3,
        "reward_coins": 500,
        "reward_card_id": None
    },
    {
        "id": "goal_all_variants_s4",
        "title": "Series 4 Variant Master",
        "description": "Collect every variant in Series 4",
        "goal_type": "collect_all_variants_series",
        "target_value": 4,
        "reward_coins": 500,
        "reward_card_id": None
    },
    {
        "id": "goal_all_variants_s5",
        "title": "Series 5 Variant Master",
        "description": "Collect every variant in Series 5",
        "goal_type": "collect_all_variants_series",
        "target_value": 5,
        "reward_coins": 500,
        "reward_card_id": None
    },
    {
        "id": "goal_all_variants_s6",
        "title": "Series 6 Variant Master",
        "description": "Collect every variant in Series 6",
        "goal_type": "collect_all_variants_series",
        "target_value": 6,
        "reward_coins": 500,
        "reward_card_id": None
    },
    {
        "id": "goal_all_variants_s7",
        "title": "Series 7 Variant Master",
        "description": "Collect every variant in Series 7",
        "goal_type": "collect_all_variants_series",
        "target_value": 7,
        "reward_coins": 500,
        "reward_card_id": None
    }
]

# =====================
# Database Initialization
# =====================

async def seed_database():
    """Seed the database with initial cards and goals - skip if already seeded"""
    # Quick check - if we already have the right number of cards, skip the full seed
    card_count = await db.cards.count_documents({})
    expected_count = len(INITIAL_CARDS)
    
    # Insert any cards from INITIAL_CARDS that aren't already in the DB.
    # This lets us add new bands/series without wiping the existing collection.
    if card_count < expected_count:
        existing_ids = {c["id"] for c in await db.cards.find({}, {"id": 1, "_id": 0}).to_list(2000)}
        to_insert = [c for c in INITIAL_CARDS if c["id"] not in existing_ids]
        if to_insert:
            for c in to_insert:
                card_obj = Card(**c)
                await db.cards.insert_one(card_obj.dict())
                logger.info(f"Inserted new card: {c['name']}")
            card_count = await db.cards.count_documents({})
    
    if card_count >= expected_count:
        logger.info(f"Database already has {card_count} cards (expected {expected_count}), skipping seed")
        # Sync front/back image URLs AND descriptions for any card whose
        # values have drifted from the source-of-truth in cards_data.py.
        # Critical: name_fixes block only fixes names; we also need URLs and
        # descriptions to flow through on the fast path so swapped/wrong
        # artwork or stale descriptions in cards_data.py reach the DB. We
        # also sync `rarity` and `series` because variant-flag/series-gating
        # logic depends on those being correct.
        url_fixes = 0
        for card_data in INITIAL_CARDS:
            existing = await db.cards.find_one(
                {"id": card_data["id"]},
                {"_id": 0, "front_image_url": 1, "back_image_url": 1,
                 "description": 1, "rarity": 1, "series": 1},
            )
            if not existing:
                continue
            patch = {}
            if card_data.get("front_image_url") != existing.get("front_image_url"):
                patch["front_image_url"] = card_data["front_image_url"]
            if card_data.get("back_image_url") != existing.get("back_image_url"):
                patch["back_image_url"] = card_data["back_image_url"]
            if card_data.get("description") != existing.get("description"):
                patch["description"] = card_data["description"]
            if card_data.get("rarity") != existing.get("rarity"):
                patch["rarity"] = card_data["rarity"]
            if card_data.get("series") != existing.get("series"):
                patch["series"] = card_data.get("series")
            if patch:
                await db.cards.update_one({"id": card_data["id"]}, {"$set": patch})
                url_fixes += 1
        if url_fixes:
            logger.info(f"Synced image URLs / descriptions for {url_fixes} card(s)")
        # Force-fix any known name corrections even when skipping full seed
        name_fixes = {
            "card_jeff_possess_ya_s2_bloodbath": {
                "name": "Jeff Possess Ya (Bloodbath)",
                "description": "The Bloodbath variant of Jeff Possess Ya. His kitchen is now a slaughterhouse. Every dish comes with a side of fresh carnage."
            },
            "card_jeff_possess_ya_s2_ice": {
                "name": "Jeff Possess Ya (Ice)",
                "description": "The Ice variant of Jeff Possess Ya. His frozen cuisine keeps the meat fresh forever. Served ice cold, literally."
            },
            "card_jeff_possess_ya_s2_psychedelic": {
                "name": "Jeff Possess Ya (Psychedelic)",
                "description": "The Psychedelic variant of Jeff Possess Ya. His recipes include rainbow spices from another dimension."
            },
            "card_jeff_possess_ya_s2_biomechanical": {
                "name": "Jeff Possess Ya (Biomechanical)",
                "description": "The Biomechanical variant of Jeff Possess Ya. His cyborg kitchen serves up mechanized meals of terror."
            },
            "card_chum_araya_hellfire": {
                "front_image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/d0ln8fri_enhanced-1774166976308.jpg",
                "back_image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/d0ln8fri_enhanced-1774166976308.jpg",
            },
            "card_chum_araya_cosmic": {
                "front_image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/t7rcvvon_enhanced-1774166884359.jpg",
                "back_image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/t7rcvvon_enhanced-1774166884359.jpg",
            },
            "card_party_tardy_oceanic": {
                "front_image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/dvwxs6lo_file_000000002a5471f5ba219c1b112402c3.png",
            },
            "card_party_tardy_diamond": {
                "front_image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/raih3ab9_file_00000000676871f58458a04e4bbe5f62.png",
            },
            "card_chef_becerra": {
                "name": "Chef Becerra",
            },
            "card_chef_becerra_bloodbath": {
                "name": "Chef Becerra (Bloodbath)",
            },
            "card_chef_becerra_ice": {
                "name": "Chef Becerra (Ice)",
            },
            "card_chef_becerra_psychedelic": {
                "name": "Chef Becerra (Psychedelic)",
            },
            "card_chef_becerra_biomechanical": {
                "name": "Chef Becerra (Biomechanical)",
            },
            "card_sean_kill_again": {
                "front_image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/bczdtpd6_file_00000000586471f7a0c781bec98345ab.png",
                "back_image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/soday9u4_file_00000000f24471f58503370fd35d90d9.png",
            },
            "card_walter_trashler": {
                "front_image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/aqyov99f_file_00000000634871f5b7cb3181ea0ea9b0.png",
            },
            # Mickey Muir front-art refresh (April 30, 2026)
            "card_mickey_muir": {
                "front_image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/yf1sqmcw_enhanced-1777473144761.jpg",
            },
            "card_mickey_muir_shadow": {
                "front_image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/p7gurlyx_file_000000001f78722f80bc1375fce2d2c2.png",
            },
            "card_mickey_muir_magma": {
                "front_image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/9blzm966_file_0000000034f4722f938d43149b721822.png",
            },
            "card_mickey_muir_cheesy": {
                "front_image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/z3znfqh5_file_000000005c6c71f599937bed9371f1d1.png",
            },
            "card_mickey_muir_mutant": {
                "front_image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/kq29utan_file_00000000d9fc720c927aaf1aca0a9794.png",
            },
            "card_walter_trashler_shadow": {
                "front_image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/9he2g2mb_file_00000000c02871f5972df5f0acf6b476.png",
            },
            "card_walter_trashler_magma": {
                "front_image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/qczj7ieb_enhanced-1777438361506.jpg",
            },
            "card_walter_trashler_cheesy": {
                "front_image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/xarv9958_enhanced-1777438417383.jpg",
            },
            "card_walter_trashler_mutant": {
                "front_image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/6j1jk80n_enhanced-1777438461037.jpg",
            },
            "card_david_whine": {
                "front_image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/n5qr2tit_enhanced-1771761544757.jpg",
            },
            "card_david_slayne": {
                "front_image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/k397xir5_file_00000000e10c722fa904bebd4e778a90.png",
            },
            "card_martini_walkyier": {
                "front_image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/gcw3jipf_enhanced-1771761620137.jpg",
            },
            "card_darren_travesty": {
                "front_image_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/q3rfccmm_enhanced-1772919382679.jpg",
            },
        }
        for card_id, updates in name_fixes.items():
            query = {"id": card_id}
            if "name" in updates:
                query["name"] = {"$ne": updates["name"]}
            result = await db.cards.update_one(query, {"$set": updates})
            if result.modified_count > 0:
                label = updates.get("name", "images")
                logger.info(f"Fixed card: {card_id} -> {label}")
        
        # Sync goals: remove stale goals not in INITIAL_GOALS, seed new ones
        valid_goal_ids = {g["id"] for g in INITIAL_GOALS}
        deleted = await db.goals.delete_many({"id": {"$nin": list(valid_goal_ids)}})
        if deleted.deleted_count > 0:
            logger.info(f"Removed {deleted.deleted_count} stale goal(s)")
            # Also clean up user_goals pointing at deleted goals
            await db.user_goals.delete_many({"goal_id": {"$nin": list(valid_goal_ids)}})
        for goal_data in INITIAL_GOALS:
            existing_goal = await db.goals.find_one({"id": goal_data["id"]})
            if not existing_goal:
                goal = Goal(**goal_data)
                await db.goals.insert_one(goal.dict())
                logger.info(f"Seeded goal: {goal.title}")
                # Existing users won't have user_goals for newly-added goals.
                # Backfill so the goal shows up on every existing player's
                # Goals tab without them having to re-register.
                user_ids = await db.users.distinct("id")
                if user_ids:
                    await db.user_goals.insert_many([
                        UserGoal(user_id=uid, goal_id=goal.id).dict()
                        for uid in user_ids
                    ])
                    logger.info(
                        f"Backfilled '{goal.title}' for {len(user_ids)} existing user(s)"
                    )
        return
    
    logger.info(f"Database has {card_count}/{expected_count} cards, seeding...")
    
    # Seed cards
    for card_data in INITIAL_CARDS:
        existing = await db.cards.find_one({"id": card_data["id"]})
        if not existing:
            card = Card(**card_data)
            await db.cards.insert_one(card.dict())
            logger.info(f"Seeded card: {card.name}")
        else:
            # Update existing cards with new fields
            update_fields = {}
            # Update name if changed
            if card_data.get("name") != existing.get("name"):
                update_fields["name"] = card_data["name"]
            if card_data.get("achievement_required") is not None:
                update_fields["achievement_required"] = card_data["achievement_required"]
            if card_data.get("rarity") != existing.get("rarity"):
                update_fields["rarity"] = card_data["rarity"]
            if card_data.get("streak_required") is not None:
                update_fields["streak_required"] = card_data["streak_required"]
            # Update availability status
            if card_data.get("available") != existing.get("available"):
                update_fields["available"] = card_data["available"]
            # Update coin_cost if changed
            if card_data.get("coin_cost") != existing.get("coin_cost"):
                update_fields["coin_cost"] = card_data["coin_cost"]
            # Update engagement_milestone if set
            if card_data.get("engagement_milestone") is not None:
                update_fields["engagement_milestone"] = card_data["engagement_milestone"]
            # Update series info if set
            if card_data.get("series") is not None:
                update_fields["series"] = card_data["series"]
            if card_data.get("series_reward") is not None:
                update_fields["series_reward"] = card_data["series_reward"]
            if card_data.get("band") is not None:
                update_fields["band"] = card_data["band"]
            if card_data.get("card_type") is not None:
                update_fields["card_type"] = card_data["card_type"]
            # Update image URLs if changed (important for variant backs)
            if card_data.get("back_image_url") != existing.get("back_image_url"):
                update_fields["back_image_url"] = card_data["back_image_url"]
            if card_data.get("front_image_url") != existing.get("front_image_url"):
                update_fields["front_image_url"] = card_data["front_image_url"]
            if update_fields:
                await db.cards.update_one({"id": card_data["id"]}, {"$set": update_fields})
                logger.info(f"Updated card: {card_data['name']} with {update_fields}")
    
    # Seed goals
    for goal_data in INITIAL_GOALS:
        existing = await db.goals.find_one({"id": goal_data["id"]})
        if not existing:
            goal = Goal(**goal_data)
            await db.goals.insert_one(goal.dict())
            logger.info(f"Seeded goal: {goal.title}")

# =====================
# Card Routes
# =====================
# (Moved to routers/cards.py)

# =====================
# User Routes
# =====================

@api_router.post("/users")
async def create_user(request: CreateUserRequest):
    """Create a new user"""
    # Check if username exists
    existing = await db.users.find_one({"username": request.username})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    user = User(username=request.username, coins=5000)  # Start with 5000 coins for testing
    await db.users.insert_one(user.dict())
    
    # Initialize user goals
    goals = await db.goals.find().to_list(100)
    for goal in goals:
        user_goal = UserGoal(user_id=user.id, goal_id=goal["id"])
        await db.user_goals.insert_one(user_goal.dict())
    
    return user

@api_router.get("/users/search")
async def search_users_route(query: str = "", code: str = ""):
    """Search users by username or friend code"""
    if code:
        user = await db.users.find_one({"friend_code": code.upper()}, {"_id": 0, "password_hash": 0})
        if user:
            friend_count = await db.friends.count_documents({
                "$or": [{"user_id": user["id"]}, {"friend_id": user["id"]}]
            })
            user["friend_count"] = friend_count
            user["rank"] = compute_user_rank(user.get("completed_series", []))
            return {"users": [user]}
        return {"users": []}
    
    if query and len(query) >= 2:
        users = await db.users.find(
            {"username": {"$regex": query, "$options": "i"}},
            {"_id": 0, "password_hash": 0}
        ).to_list(20)
        for u in users:
            friend_count = await db.friends.count_documents({
                "$or": [{"user_id": u["id"]}, {"friend_id": u["id"]}]
            })
            u["friend_count"] = friend_count
            u["rank"] = compute_user_rank(u.get("completed_series", []))
        return {"users": users}
    
    return {"users": []}

@api_router.get("/users/recently-active")
async def get_recently_active_users(user_id: str = ""):
    """Get users active in the last 30 minutes"""
    cutoff = (datetime.utcnow() - timedelta(minutes=30)).isoformat()
    active_users = await db.users.find(
        {"last_active": {"$gte": cutoff}},
        {"_id": 0, "password_hash": 0}
    ).sort("last_active", -1).to_list(50)
    
    # Filter out requesting user, add friend count and friendship status
    result = []
    for u in active_users:
        if u["id"] == user_id:
            continue
        friend_count = await db.friends.count_documents({
            "$or": [{"user_id": u["id"]}, {"friend_id": u["id"]}]
        })
        u["friend_count"] = friend_count
        u["rank"] = compute_user_rank(u.get("completed_series", []))
        if user_id:
            is_friend = await db.friends.find_one({
                "$or": [
                    {"user_id": user_id, "friend_id": u["id"]},
                    {"user_id": u["id"], "friend_id": user_id}
                ]
            })
            pending = await db.friend_requests.find_one({
                "$or": [
                    {"from_user_id": user_id, "to_user_id": u["id"], "status": "pending"},
                    {"from_user_id": u["id"], "to_user_id": user_id, "status": "pending"}
                ]
            })
            u["is_friend"] = bool(is_friend)
            u["has_pending_request"] = bool(pending)
        result.append(u)
    
    return {"users": result, "count": len(result)}

@api_router.post("/users/{user_id}/heartbeat")
async def user_heartbeat(user_id: str):
    """Update user's last_active timestamp"""
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"last_active": datetime.utcnow().isoformat()}}
    )
    return {"success": True}

@api_router.get("/users/{user_id}")
async def get_user(user_id: str):
    """Get user details"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user_data = User(**user).model_dump()
    del user_data['password_hash']
    user_data['friend_code'] = user.get('friend_code', '')
    user_data['medals'] = user.get('medals', 0)
    user_data['free_packs'] = user.get('free_packs', 0)
    user_data['rank'] = compute_user_rank(user_data.get('completed_series', []))
    friend_count = await db.friends.count_documents({
        "$or": [{"user_id": user_id}, {"friend_id": user_id}]
    })
    user_data['friend_count'] = friend_count
    return user_data

@api_router.get("/ranks")
async def list_ranks():
    """Return the full ladder of ranks (for the rank-progress UI)."""
    return {"ranks": RANKS}


async def _evaluate_badge(badge: dict, user: dict) -> bool:
    """Return True if the given user currently satisfies the badge condition."""
    ct = badge["condition_type"]
    p = badge.get("condition_params", {}) or {}
    user_id = user["id"]

    if ct == COND_LOGIN_STREAK:
        return user.get("daily_login_streak", 0) >= p.get("min", 0)

    if ct == COND_TOTAL_SPENT:
        return user.get("total_spent_coins", 0) >= p.get("min", 0)

    if ct == COND_TRADES_ACCEPTED:
        count = await db.trades.count_documents({
            "status": "accepted",
            "$or": [{"from_user_id": user_id}, {"to_user_id": user_id}],
        })
        return count >= p.get("min", 0)

    if ct == COND_FRIEND_COUNT:
        count = await db.friends.count_documents({
            "$or": [{"user_id": user_id}, {"friend_id": user_id}]
        })
        return count >= p.get("min", 0)

    if ct == COND_OWN_ANY_CARD:
        return await db.user_cards.find_one({"user_id": user_id}) is not None

    if ct == COND_OWN_SPECIFIC_CARD:
        return await db.user_cards.find_one({
            "user_id": user_id,
            "card_id": p.get("card_id"),
        }) is not None

    if ct == COND_VARIANTS_OWNED:
        # Count distinct variant cards the user owns.
        variant_card_ids = await db.cards.distinct("id", {"is_variant": True})
        if not variant_card_ids:
            return False
        owned = await db.user_cards.count_documents({
            "user_id": user_id,
            "card_id": {"$in": variant_card_ids},
        })
        return owned >= p.get("min", 0)

    if ct == COND_SERIES_BASE_COMPLETE:
        series_num = p.get("series_num")
        # Series 7 stores band cards with rarity "rare"/"epic" plus the reward
        # — we only count base band cards (not variants, not the rare reward).
        base_card_ids = await db.cards.distinct("id", {
            "series": series_num,
            "is_variant": {"$ne": True},
            "series_reward": None,
        })
        if not base_card_ids:
            return False
        owned = await db.user_cards.count_documents({
            "user_id": user_id,
            "card_id": {"$in": base_card_ids},
        })
        return owned >= len(base_card_ids)

    if ct == COND_CREATED_BEFORE_SERIES:
        cutoff = get_release_date(p.get("series_num"))
        if cutoff is None:
            return False
        created = user.get("created_at")
        if isinstance(created, str):
            try:
                created = datetime.fromisoformat(created.replace("Z", "+00:00"))
            except ValueError:
                return False
        if created is None:
            return False
        # Normalize tz so naive datetimes don't crash the comparison.
        if created.tzinfo is None and cutoff.tzinfo is not None:
            created = created.replace(tzinfo=cutoff.tzinfo)
        elif cutoff.tzinfo is None and created.tzinfo is not None:
            cutoff = cutoff.replace(tzinfo=created.tzinfo)
        return created < cutoff

    return False


@api_router.get("/badges")
async def list_badges():
    """Return all badge definitions (icons, descriptions) — no per-user state."""
    return {"badges": BADGES}


@api_router.get("/users/{user_id}/badges")
async def get_user_badges(user_id: str):
    """Return every badge with an `earned` flag for this user."""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    result = []
    for badge in BADGES:
        earned = await _evaluate_badge(badge, user)
        result.append({**badge, "earned": earned})
    return {"badges": result, "earned_count": sum(1 for b in result if b["earned"])}

# =====================
# Authentication
# =====================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

@api_router.post("/auth/register")
async def register(request: RegisterRequest):
    """Register a new user with username and password"""
    # Check if username already exists
    existing_user = await db.users.find_one({"username": request.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Hash the password
    password_hash = hash_password(request.password)
    
    # Create new user with friend code
    import random, string
    friend_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    # Ensure unique friend code
    while await db.users.find_one({"friend_code": friend_code}):
        friend_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    new_user = User(
        username=request.username,
        password_hash=password_hash,
        coins=500  # Starting coins
    )
    user_data = new_user.model_dump()
    user_data['friend_code'] = friend_code
    
    await db.users.insert_one(user_data)
    
    # Return user without password hash
    del user_data['password_hash']
    user_data.pop('_id', None)
    return user_data

@api_router.post("/auth/login")
async def login(request: LoginRequest):
    """Login with username and password"""
    user = await db.users.find_one({"username": request.username})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Check if user has a password set (for legacy users without passwords)
    if not user.get('password_hash'):
        raise HTTPException(status_code=401, detail="Please set a password for your account")
    
    # Verify password
    if not verify_password(request.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Self-heal: re-evaluate series completion for every released series so
    # users who finished a series before the unlock logic was deployed (or
    # before a new series went live) get their next-series unlock + reward
    # backfilled on next login. Idempotent — function no-ops if reward
    # already granted. Failures are logged but don't block login.
    try:
        for sn in released_series_nums():
            await check_series_completion(user['id'], sn)
    except Exception as e:
        logging.warning(f"Series unlock backfill failed for {user.get('id')}: {e}")
    # Re-fetch user so the response reflects any unlocks the backfill applied.
    user = await db.users.find_one({"id": user['id']}) or user

    # Return user without password hash
    user_data = User(**user).model_dump()
    del user_data['password_hash']
    user_data['friend_code'] = user.get('friend_code', '')
    # Get friend count
    friend_count = await db.friends.count_documents({
        "$or": [{"user_id": user_data['id']}, {"friend_id": user_data['id']}]
    })
    user_data['friend_count'] = friend_count
    # Update last_active timestamp
    await db.users.update_one({"id": user_data['id']}, {"$set": {"last_active": datetime.utcnow().isoformat()}})
    return user_data

@api_router.post("/auth/set-password/{user_id}")
async def set_password(user_id: str, request: LoginRequest):
    """Set password for existing users (legacy migration)"""
    user = await db.users.find_one({"id": user_id, "username": request.username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Hash and set the new password
    password_hash = hash_password(request.password)
    await db.users.update_one({"id": user_id}, {"$set": {"password_hash": password_hash}})
    
    return {"message": "Password set successfully"}

@api_router.post("/auth/delete-account")
async def delete_account(request: LoginRequest):
    """Delete user account and all associated data"""
    user = await db.users.find_one({"username": request.username})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    if not user.get('password_hash') or not verify_password(request.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    user_id = user["id"]
    
    await db.user_cards.delete_many({"user_id": user_id})
    await db.trades.delete_many({"$or": [{"from_user_id": user_id}, {"to_user_id": user_id}]})
    await db.payment_transactions.delete_many({"user_id": user_id})
    await db.users.delete_one({"id": user_id})
    
    logger.info(f"Account deleted: {request.username} ({user_id})")
    
    return {"success": True, "message": "Account and all associated data have been permanently deleted"}

@api_router.get("/users/username/{username}")
async def get_user_by_username(username: str):
    """Get user by username"""
    user = await db.users.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return User(**user)

@api_router.get("/users")
async def get_all_users():
    """Get all users (for trading)"""
    users = await db.users.find().to_list(100)
    return [User(**user) for user in users]

@api_router.put("/users/{user_id}/profile")
async def update_profile(user_id: str, request: UpdateProfileRequest):
    """Update user profile"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = {}
    if request.bio is not None:
        update_data["bio"] = request.bio
        if request.bio.strip():
            update_data["profile_completed"] = True
    if request.avatar_url is not None:
        update_data["avatar_url"] = request.avatar_url
    
    if update_data:
        await db.users.update_one({"id": user_id}, {"$set": update_data})
        
        # Check profile completion goal
        if update_data.get("profile_completed"):
            await check_and_update_goals(user_id, "profile_complete", 1)
    
    updated_user = await db.users.find_one({"id": user_id})
    return User(**updated_user)

@api_router.put("/users/{user_id}/featured-cards")
async def update_featured_cards(user_id: str, request: UpdateFeaturedCardsRequest):
    """Update the user's pinned showcase cards (up to 5, must be cards they own).

    Strips duplicates, enforces the 5-card cap, and silently drops any IDs
    the user does not actually own. We don't 400 on bad IDs because the
    selection modal already filters owned-only; this defends against stale
    UI state from quick swaps mid-trade.
    """
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Cap at 5 and dedupe while preserving order
    seen: set = set()
    requested_ids: List[str] = []
    for cid in request.card_ids:
        if cid in seen:
            continue
        seen.add(cid)
        requested_ids.append(cid)
        if len(requested_ids) >= 5:
            break

    # Filter to only cards the user actually owns
    if requested_ids:
        owned = await db.user_cards.find(
            {"user_id": user_id, "card_id": {"$in": requested_ids}},
            {"_id": 0, "card_id": 1},
        ).to_list(50)
        owned_ids = {uc["card_id"] for uc in owned}
        validated = [cid for cid in requested_ids if cid in owned_ids]
    else:
        validated = []

    await db.users.update_one(
        {"id": user_id},
        {"$set": {"featured_card_ids": validated}},
    )

    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0})
    updated_user.pop("password_hash", None)
    updated_user["rank"] = compute_user_rank(updated_user.get("completed_series", []))
    return User(**updated_user)

@api_router.post("/users/{user_id}/daily-login")
async def claim_daily_login(user_id: str):
    """Claim daily login bonus"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    today = datetime.utcnow().strftime("%Y-%m-%d")
    last_login = user.get("last_login_date")
    
    if last_login == today:
        raise HTTPException(status_code=400, detail="Already claimed today")
    
    # Calculate streak
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    if last_login == yesterday:
        new_streak = user.get("daily_login_streak", 0) + 1
    else:
        new_streak = 1
    
    # Calculate bonus coins - flat 50 coins per day
    bonus_coins = 50
    
    new_coins = user.get("coins", 0) + bonus_coins
    
    # Track monthly logins for Monthly Master milestone
    current_month = datetime.utcnow().strftime("%Y-%m")
    today_day = datetime.utcnow().day
    monthly_logins = user.get("monthly_logins", {})
    
    # Get or create the list for this month
    if current_month not in monthly_logins:
        monthly_logins[current_month] = []
    
    # Add today if not already logged
    if today_day not in monthly_logins[current_month]:
        monthly_logins[current_month].append(today_day)
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "last_login_date": today,
            "daily_login_streak": new_streak,
            "coins": new_coins,
            "monthly_logins": monthly_logins
        }}
    )
    
    # Check daily login goals
    await check_and_update_goals(user_id, "daily_login", new_streak)
    
    # Check for newly unlocked epic cards (notify user they can now purchase)
    newly_unlocked_epic = await check_epic_streak_unlocks(user_id, new_streak)
    
    # Check for engagement milestone unlocks
    engagement_unlock = await check_engagement_milestones(user_id)
    
    return {
        "streak": new_streak,
        "bonus_coins": bonus_coins,
        "total_coins": new_coins,
        "message": f"Day {new_streak} streak! +{bonus_coins} coins",
        "newly_unlocked_epic_card": newly_unlocked_epic,
        "engagement_unlock": engagement_unlock
    }

# =====================
# Epic Streak Card Achievement System
# =====================

async def check_epic_streak_unlocks(user_id: str, current_streak: int):
    """Check if user has unlocked any epic cards for purchase based on their login streak"""
    # Get user's unlocked achievements
    user = await db.users.find_one({"id": user_id})
    unlocked_epics = user.get("unlocked_epic_cards", [])
    
    # Get all epic cards that require streak achievements
    epic_cards = await db.cards.find({"rarity": "epic", "streak_required": {"$ne": None}}).to_list(100)
    
    newly_unlocked = None
    
    for epic_card in epic_cards:
        required_streak = epic_card.get("streak_required", 0)
        
        if current_streak >= required_streak and epic_card["id"] not in unlocked_epics:
            # Mark as unlocked (purchasable) - don't auto-award
            await db.users.update_one(
                {"id": user_id},
                {"$addToSet": {"unlocked_epic_cards": epic_card["id"]}}
            )
            logger.info(f"User {user_id} unlocked epic card for purchase: {epic_card['name']} (streak: {current_streak})")
            newly_unlocked = Card(**epic_card)
    
    return newly_unlocked

@api_router.get("/users/{user_id}/check-epic-cards")
async def check_user_epic_cards(user_id: str):
    """Check status of all epic streak cards for a user"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    current_streak = user.get("daily_login_streak", 0)
    unlocked_epics = user.get("unlocked_epic_cards", [])
    
    # Get all epic cards and their status for this user
    epic_cards = await db.cards.find({"rarity": "epic"}).to_list(100)
    
    epic_cards_status = []
    for epic_card in epic_cards:
        owned = await db.user_cards.find_one({
            "user_id": user_id,
            "card_id": epic_card["id"]
        })
        
        required = epic_card.get("streak_required", 0)
        progress = min(current_streak, required) if required else 0
        is_unlocked = epic_card["id"] in unlocked_epics or current_streak >= required
        
        # Auto-unlock if streak requirement met
        if current_streak >= required and epic_card["id"] not in unlocked_epics:
            await db.users.update_one(
                {"id": user_id},
                {"$addToSet": {"unlocked_epic_cards": epic_card["id"]}}
            )
            is_unlocked = True
        
        epic_cards_status.append({
            "card": Card(**epic_card),
            "owned": owned is not None,
            "unlocked": is_unlocked,  # Can purchase
            "required_streak": required,
            "progress": progress,
            "can_purchase": is_unlocked and not owned
        })
    
    return {
        "current_streak": current_streak,
        "epic_cards": epic_cards_status
    }

# =====================
# Engagement Milestone System
# =====================

async def check_engagement_milestones(user_id: str):
    """Check and unlock engagement milestone cards based on user progress"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        return None
    
    unlocked_engagement = user.get("unlocked_engagement_cards", [])
    newly_unlocked = None
    
    # Get all engagement milestone cards
    engagement_cards = await db.cards.find({"engagement_milestone": {"$ne": None}}).to_list(100)
    
    for eng_card in engagement_cards:
        milestone_type = eng_card.get("engagement_milestone")
        card_id = eng_card["id"]
        
        if card_id in unlocked_engagement:
            continue
        
        unlocked = False
        
        if milestone_type == "dedicated_fan":
            # 30-day login streak
            if user.get("daily_login_streak", 0) >= 30:
                unlocked = True
                
        elif milestone_type == "big_spender":
            # 750 total coins spent
            if user.get("total_spent_coins", 0) >= 750:
                unlocked = True
                
        elif milestone_type == "monthly_master":
            # 20 days in a single month
            monthly_logins = user.get("monthly_logins", {})
            for month, days in monthly_logins.items():
                if len(days) >= 20:
                    unlocked = True
                    break
        
        if unlocked:
            await db.users.update_one(
                {"id": user_id},
                {"$addToSet": {"unlocked_engagement_cards": card_id}}
            )
            logger.info(f"User {user_id} unlocked engagement card: {eng_card['name']} ({milestone_type})")
            newly_unlocked = Card(**eng_card)
    
    return newly_unlocked

@api_router.get("/users/{user_id}/check-engagement-milestones")
async def check_user_engagement_milestones(user_id: str):
    """Check status of all engagement milestone cards for a user"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    unlocked_engagement = user.get("unlocked_engagement_cards", [])
    current_streak = user.get("daily_login_streak", 0)
    total_spent = user.get("total_spent_coins", 0)
    monthly_logins = user.get("monthly_logins", {})
    
    # Find best month login count
    best_month_logins = 0
    current_month = datetime.utcnow().strftime("%Y-%m")
    current_month_logins = 0
    
    for month, days in monthly_logins.items():
        if len(days) > best_month_logins:
            best_month_logins = len(days)
        if month == current_month:
            current_month_logins = len(days)
    
    # Get all engagement milestone cards
    engagement_cards = await db.cards.find({"engagement_milestone": {"$ne": None}}).to_list(100)
    
    engagement_status = []
    newly_unlocked = None
    
    for eng_card in engagement_cards:
        milestone_type = eng_card.get("engagement_milestone")
        card_id = eng_card["id"]
        
        owned = await db.user_cards.find_one({
            "user_id": user_id,
            "card_id": card_id
        })
        
        # Determine progress and requirement based on milestone type
        if milestone_type == "dedicated_fan":
            requirement = 30  # 30-day streak
            progress = current_streak
            description = "30-day login streak"
        elif milestone_type == "big_spender":
            requirement = 750  # 750 coins spent
            progress = total_spent
            description = "Spend 750 total coins"
        elif milestone_type == "monthly_master":
            requirement = 20  # 20 days in a month
            progress = current_month_logins
            description = "Log in 20 days this month"
        else:
            requirement = 0
            progress = 0
            description = ""
        
        is_unlocked = card_id in unlocked_engagement or progress >= requirement
        
        # Auto-unlock if requirement met
        if progress >= requirement and card_id not in unlocked_engagement:
            await db.users.update_one(
                {"id": user_id},
                {"$addToSet": {"unlocked_engagement_cards": card_id}}
            )
            is_unlocked = True
            if not owned:
                newly_unlocked = Card(**eng_card)
        
        engagement_status.append({
            "card": Card(**eng_card),
            "owned": owned is not None,
            "unlocked": is_unlocked,
            "milestone_type": milestone_type,
            "requirement": requirement,
            "progress": progress,
            "description": description,
            "can_purchase": is_unlocked and not owned
        })
    
    return {
        "current_streak": current_streak,
        "total_spent_coins": total_spent,
        "current_month_logins": current_month_logins,
        "best_month_logins": best_month_logins,
        "engagement_milestones": engagement_status,
        "newly_unlocked": newly_unlocked
    }

# =====================
# User Cards & Collection
# =====================

@api_router.get("/users/{user_id}/cards")
async def get_user_cards(user_id: str):
    """Get all cards owned by user"""
    user_cards = await db.user_cards.find({"user_id": user_id}).to_list(1000)
    
    result = []
    for uc in user_cards:
        card = await db.cards.find_one({"id": uc["card_id"]})
        if card:
            result.append({
                "user_card_id": uc["id"],
                "card": Card(**card),
                "quantity": uc.get("quantity", 1),
                "acquired_at": uc.get("acquired_at", datetime.utcnow().isoformat())
            })
    
    return result

@api_router.post("/users/{user_id}/purchase-card")
async def purchase_card(user_id: str, request: PurchaseCardRequest):
    """Purchase a card with coins"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    card = await db.cards.find_one({"id": request.card_id})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    # Check if card is available for purchase
    card_available = card.get("available", True)
    card_rarity = card.get("rarity", "common")
    
    # For rare/epic cards, check if user has unlocked them
    if not card_available:
        engagement_milestone = card.get("engagement_milestone")
        
        if engagement_milestone:
            # Check if user has unlocked this engagement milestone card
            unlocked_engagement = user.get("unlocked_engagement_cards", [])
            if card["id"] not in unlocked_engagement:
                # Get milestone info for error message
                if engagement_milestone == "dedicated_fan":
                    raise HTTPException(status_code=400, detail="Reach a 30-day login streak to unlock this card")
                elif engagement_milestone == "big_spender":
                    raise HTTPException(status_code=400, detail="Spend 750 total coins to unlock this card")
                elif engagement_milestone == "monthly_master":
                    raise HTTPException(status_code=400, detail="Log in 20 days in a single month to unlock this card")
                else:
                    raise HTTPException(status_code=400, detail="This card is not yet available")
        elif card_rarity == "rare":
            # Check if user has unlocked this rare card
            unlocked_rares = user.get("unlocked_rare_cards", [])
            if card["id"] not in unlocked_rares:
                # Check if they should have it unlocked based on card count
                user_cards = await db.user_cards.find({"user_id": user_id}).to_list(1000)
                total_cards = sum(uc.get("quantity", 1) for uc in user_cards)
                required = card.get("achievement_required", 0)
                if total_cards < required:
                    raise HTTPException(status_code=400, detail=f"Collect {required} cards to unlock this rare card")
        elif card_rarity == "epic":
            # Check if user has unlocked this epic card
            unlocked_epics = user.get("unlocked_epic_cards", [])
            if card["id"] not in unlocked_epics:
                # Check if they should have it unlocked based on streak
                current_streak = user.get("daily_login_streak", 0)
                required = card.get("streak_required", 0)
                if current_streak < required:
                    raise HTTPException(status_code=400, detail=f"Reach a {required}-day login streak to unlock this epic card")
        else:
            # Coming soon cards - not purchasable
            raise HTTPException(status_code=400, detail="This card is not yet available")
    
    if user.get("coins", 0) < card["coin_cost"]:
        raise HTTPException(status_code=400, detail="Not enough coins")
    
    # Deduct coins and track total spent
    new_coins = user.get("coins", 0) - card["coin_cost"]
    new_total_spent = user.get("total_spent_coins", 0) + card["coin_cost"]
    await db.users.update_one(
        {"id": user_id}, 
        {"$set": {"coins": new_coins, "total_spent_coins": new_total_spent}}
    )
    
    # Add card to collection
    existing_user_card = await db.user_cards.find_one({
        "user_id": user_id,
        "card_id": request.card_id
    })
    
    if existing_user_card:
        await db.user_cards.update_one(
            {"id": existing_user_card["id"]},
            {"$inc": {"quantity": 1}}
        )
    else:
        user_card = UserCard(user_id=user_id, card_id=request.card_id)
        await db.user_cards.insert_one(user_card.dict())
    
    # Check card collection goals
    unique_cards = await db.user_cards.count_documents({"user_id": user_id})
    await check_and_update_goals(user_id, "collect_cards", unique_cards)
    
    # Check all-rarities goal (collect one of each: common, rare, epic)
    await check_all_rarities_goal(user_id)
    
    # Check for rare card achievements
    newly_unlocked_rare = await check_rare_card_achievements(user_id)
    
    # Check for milestone rewards (free card every 10 cards)
    milestone_reward = await check_milestone_reward(user_id)
    
    # Check for engagement milestone unlocks (including Big Spender)
    engagement_unlock = await check_engagement_milestones(user_id)
    
    return {
        "success": True,
        "remaining_coins": new_coins,
        "card": Card(**card),
        "newly_unlocked_rare_card": newly_unlocked_rare,
        "milestone_reward": milestone_reward,
        "engagement_unlock": engagement_unlock
    }

# =====================
# Spin Wheel System
# =====================

# =====================
# Crash / error reporting
# =====================

class CrashReport(BaseModel):
    error: str
    stack: Optional[str] = None
    component_stack: Optional[str] = None
    screen: Optional[str] = None
    user_id: Optional[str] = None
    platform: Optional[str] = None
    app_version: Optional[str] = None
    device_info: Optional[Dict[str, Any]] = None
    breadcrumbs: Optional[List[str]] = None

@api_router.post("/crash-log")
async def post_crash_log(report: CrashReport, request: Request):
    """
    Lightweight client-side error capture. JS-thread render errors caught by the
    React error boundary post here so we see crashes with full screen/action
    context faster than Play Console can aggregate them.
    """
    payload = report.dict()
    payload["id"] = str(uuid.uuid4())
    payload["received_at"] = datetime.now(timezone.utc)
    # Trim runaway payloads — clients are untrusted.
    if payload.get("stack") and len(payload["stack"]) > 8000:
        payload["stack"] = payload["stack"][:8000] + "...[truncated]"
    if payload.get("component_stack") and len(payload["component_stack"]) > 8000:
        payload["component_stack"] = payload["component_stack"][:8000] + "...[truncated]"
    payload["client_ip"] = request.client.host if request.client else None
    await db.crash_logs.insert_one(payload)
    logger.warning(
        f"CRASH [{payload.get('app_version')} | {payload.get('platform')} | "
        f"screen={payload.get('screen')} | user={payload.get('user_id')}]: "
        f"{payload['error'][:200]}"
    )
    return {"ok": True, "id": payload["id"]}

@api_router.get("/series/list")
async def get_series_list():
    """
    Public series catalog. Frontend reads this to know how many series exist
    and their metadata, so adding a new series only requires a backend
    SERIES_CONFIG entry and a redeploy — no app rebuild needed.
    """
    series_entries = []
    for num, cfg in sorted(SERIES_CONFIG.items()):
        rel_dt = get_release_date(num)
        series_entries.append({
            "series": num,
            "name": cfg.get("name", f"Series {num}"),
            "description": cfg.get("description", ""),
            "cards_required": cfg.get("cards_required", 16),
            "has_reward": bool(cfg.get("rare_reward")),
            "released": is_series_released(num),
            "status": series_status(num),  # released | scheduled | coming_soon
            "release_date": rel_dt.isoformat() if rel_dt else None,
        })
    return {
        "max_series": current_max_series(),
        "max_declared_series": MAX_DECLARED_SERIES,
        "series": series_entries,
    }

@api_router.get("/spin/config")
async def get_spin_config():
    """Get spin wheel configuration"""
    return {
        "spin_cost": SPIN_COST,
        "odds": {"common": 100}  # All cards in spin pool are common for Series 1
    }

@api_router.post("/users/{user_id}/spin")
async def spin_wheel(user_id: str, series: int = None):
    """Spin the wheel to get a random card from the user's current unlocked series"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user has enough coins
    if user.get("coins", 0) < SPIN_COST:
        raise HTTPException(status_code=400, detail=f"Not enough coins. Need {SPIN_COST} coins to spin.")
    
    # Get user's unlocked series (default to series 1)
    unlocked_series = user.get("unlocked_series", [1])
    if not unlocked_series:
        unlocked_series = [1]
        await db.users.update_one({"id": user_id}, {"$set": {"unlocked_series": [1]}})
    
    # Get current series (the highest unlocked series that's not completed)
    completed_series = user.get("completed_series", [])
    if series and series in unlocked_series:
        current_series = series
    else:
        uncompleted = [s for s in unlocked_series if s not in completed_series]
        current_series = max(uncompleted) if uncompleted else max(unlocked_series)
    
    # Get available cards for the spin (from selected series only)
    series_cards = await db.cards.find({
        "series": current_series,
        "rarity": "common",
        "available": True,
        "engagement_milestone": None  # Exclude engagement milestone cards
    }).to_list(100)
    
    if not series_cards:
        raise HTTPException(status_code=400, detail="No cards available to spin in current series")
    
    # Pick 3 random cards (duplicates allowed across the pack)
    PACK_SIZE = 3
    won_cards = random.choices(series_cards, k=PACK_SIZE)
    
    # Deduct coins and track spending
    new_coins = user.get("coins", 0) - SPIN_COST
    new_total_spent = user.get("total_spent_coins", 0) + SPIN_COST
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"coins": new_coins, "total_spent_coins": new_total_spent}}
    )
    
    # Add each card to collection
    cards_result = []
    for won_card in won_cards:
        existing_user_card = await db.user_cards.find_one({
            "user_id": user_id,
            "card_id": won_card["id"]
        })
        
        is_duplicate = existing_user_card is not None
        
        if existing_user_card:
            await db.user_cards.update_one(
                {"id": existing_user_card["id"]},
                {"$inc": {"quantity": 1}}
            )
        else:
            user_card = UserCard(user_id=user_id, card_id=won_card["id"])
            await db.user_cards.insert_one(user_card.dict())
        
        cards_result.append({
            "card": Card(**_with_scratch_cover(won_card)),
            "is_duplicate": is_duplicate,
        })
    
    # Check for series completion
    series_completion = await check_series_completion(user_id, current_series)
    
    # Check for achievements after spin
    unique_cards = await db.user_cards.count_documents({"user_id": user_id})
    await check_and_update_goals(user_id, "collect_cards", unique_cards)
    await check_all_rarities_goal(user_id)
    await check_all_variants_series_goals(user_id)
    engagement_unlock = await check_engagement_milestones(user_id)
    
    return {
        "success": True,
        "won_cards": cards_result,
        "won_card": cards_result[0]["card"],  # Backwards compat
        "is_duplicate": cards_result[0]["is_duplicate"],  # Backwards compat
        "remaining_coins": new_coins,
        "spin_cost": SPIN_COST,
        "pack_size": PACK_SIZE,
        "current_series": current_series,
        "series_completion": series_completion,
        "engagement_unlock": engagement_unlock
    }

async def check_series_completion(user_id: str, series_num: int):
    """Check if user has completed a series and unlock next series + rare reward"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        return None
    
    # Get all cards in this series
    series_cards = await db.cards.find({
        "series": series_num,
        "rarity": "common"
    }).to_list(100)
    
    series_card_ids = [c["id"] for c in series_cards]
    
    # Get user's owned cards from this series
    user_cards = await db.user_cards.find({
        "user_id": user_id,
        "card_id": {"$in": series_card_ids}
    }).to_list(100)
    
    owned_ids = set(uc["card_id"] for uc in user_cards)
    owned_count = len(owned_ids)
    required_count = len(series_card_ids)
    
    # Check if series is complete
    completed_series = user.get("completed_series", [])
    series_config = SERIES_CONFIG.get(series_num, {})
    rare_reward_id = series_config.get("rare_reward")

    # Determine whether the user is *missing* the reward they should have.
    # We previously gated on "series_num not in completed_series" but that
    # caused the reward to be permanently skipped if the series was added to
    # SERIES_CONFIG *after* the user already completed it (e.g., Series 6
    # users who finished it before the config entry existed).
    unlocked_rares = user.get("unlocked_rare_cards", [])
    reward_already_granted = (
        rare_reward_id is not None and rare_reward_id in unlocked_rares
    )

    if owned_count >= required_count and not reward_already_granted:
        # Series completed! Mark as complete (idempotent thanks to set behavior)
        if series_num not in completed_series:
            completed_series.append(series_num)
        
        # Unlock next series — but only if it's been released. Scheduled
        # / coming-soon series stay locked even if the user finishes the
        # one before them; they auto-unlock at release time via the startup
        # backfill below.
        unlocked_series = user.get("unlocked_series", [1])
        next_series = series_num + 1
        max_visible = current_max_series()
        if next_series not in unlocked_series and next_series <= max_visible:
            unlocked_series.append(next_series)
        
        # Get rare reward card for this series
        rare_reward_card = None
        
        if rare_reward_id:
            # Add rare reward to user's collection
            rare_card = await db.cards.find_one({"id": rare_reward_id})
            if rare_card:
                # Check if user already owns it
                existing = await db.user_cards.find_one({
                    "user_id": user_id,
                    "card_id": rare_reward_id
                })
                if not existing:
                    user_card = UserCard(user_id=user_id, card_id=rare_reward_id)
                    await db.user_cards.insert_one(user_card.dict())
                    rare_reward_card = Card(**rare_card)
                
                # Also add to unlocked_rare_cards
                unlocked_rares = user.get("unlocked_rare_cards", [])
                if rare_reward_id not in unlocked_rares:
                    unlocked_rares.append(rare_reward_id)
                    await db.users.update_one(
                        {"id": user_id},
                        {"$set": {"unlocked_rare_cards": unlocked_rares}}
                    )
        
        await db.users.update_one(
            {"id": user_id},
            {"$set": {
                "completed_series": completed_series,
                "unlocked_series": unlocked_series
            }}
        )
        
        return {
            "series_completed": series_num,
            "series_name": series_config.get("name", f"Series {series_num}"),
            "rare_reward": rare_reward_card,
            "next_series_unlocked": next_series if next_series <= max_visible else None
        }
    
    return {
        "series_completed": None,
        "progress": owned_count,
        "required": required_count
    }

@api_router.get("/users/{user_id}/spin-pool")
async def get_spin_pool(user_id: str, series: int = None):
    """Get the cards available in the spin pool for all unlocked series"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's unlocked series (default to series 1)
    unlocked_series = user.get("unlocked_series", [1])
    if not unlocked_series:
        unlocked_series = [1]
    
    # Use requested series if provided and unlocked, otherwise auto-detect
    completed_series = user.get("completed_series", [])
    if series and series in unlocked_series:
        current_series = series
    else:
        uncompleted = [s for s in unlocked_series if s not in completed_series]
        current_series = max(uncompleted) if uncompleted else max(unlocked_series)
    
    # Get series config for current series (for display purposes)
    series_config = SERIES_CONFIG.get(current_series, {})
    
    # Get cards from ALL unlocked series (so users can collect duplicates for variants)
    series_cards = await db.cards.find({
        "series": {"$in": unlocked_series},
        "rarity": "common",
        "available": True,
        "engagement_milestone": None
    }, {"_id": 0}).to_list(500)
    
    # Get user's owned cards
    user_cards = await db.user_cards.find({"user_id": user_id}).to_list(1000)
    owned_card_ids = set(uc["card_id"] for uc in user_cards)
    
    # Mark which cards are owned
    for card in series_cards:
        card["owned"] = card["id"] in owned_card_ids
    
    # Get rare reward info for current series
    rare_reward = None
    if series_config.get("rare_reward"):
        rare_card = await db.cards.find_one({"id": series_config["rare_reward"]}, {"_id": 0})
        if rare_card:
            rare_reward = rare_card
    
    # Count owned cards in current series only (for progress display)
    current_series_cards = [c for c in series_cards if c.get("series") == current_series]
    owned_count = sum(1 for c in current_series_cards if c["owned"])
    
    return {
        "current_series": current_series,
        "series_name": series_config.get("name", f"Series {current_series}"),
        "series_description": series_config.get("description", ""),
        "series_cards": series_cards,
        "owned_count": owned_count,
        "total_count": len(current_series_cards),
        "rare_reward": rare_reward,
        "spin_cost": SPIN_COST,
        "is_complete": current_series in completed_series,
        "completed_series": completed_series,
        "unlocked_series": unlocked_series
    }

@api_router.get("/users/{user_id}/series-progress")
async def get_series_progress(user_id: str):
    """Get detailed series progress for a user"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    unlocked_series = user.get("unlocked_series", [1])
    completed_series = user.get("completed_series", [])
    user_cards = await db.user_cards.find({"user_id": user_id}).to_list(1000)
    owned_card_ids = set(uc["card_id"] for uc in user_cards)
    
    all_series = []
    # Show ALL declared series (released + scheduled + coming_soon) so the
    # frontend can render greyed-out "Coming Soon" tiles for unreleased ones.
    for series_num in range(1, MAX_DECLARED_SERIES + 1):
        series_config = SERIES_CONFIG.get(series_num, {})
        
        # Get cards in this series
        series_cards = await db.cards.find({
            "series": series_num,
            "rarity": "common"
        }, {"_id": 0}).to_list(100)
        
        owned_in_series = sum(1 for c in series_cards if c["id"] in owned_card_ids)
        
        # Get rare reward
        rare_reward = None
        if series_config.get("rare_reward"):
            rare_card = await db.cards.find_one({"id": series_config["rare_reward"]}, {"_id": 0})
            if rare_card:
                rare_reward = rare_card
                rare_reward["owned"] = rare_card["id"] in owned_card_ids
        
        rel_dt = get_release_date(series_num)
        all_series.append({
            "series_num": series_num,
            "name": series_config.get("name", f"Series {series_num}"),
            "description": series_config.get("description", ""),
            "unlocked": series_num in unlocked_series,
            "completed": series_num in completed_series,
            "owned_count": owned_in_series,
            "total_count": len(series_cards),
            "rare_reward": rare_reward,
            "released": is_series_released(series_num),
            "status": series_status(series_num),
            "release_date": rel_dt.isoformat() if rel_dt else None,
        })
    
    return {
        "series": all_series,
        "current_series": max(s for s in unlocked_series if s not in completed_series) if [s for s in unlocked_series if s not in completed_series] else max(unlocked_series)
    }

SERIES_MILESTONE_MEDAL_REWARD = 200

@api_router.post("/users/{user_id}/series-milestone/{series}")
async def claim_series_milestone(user_id: str, series: int):
    """
    One-time celebration bonus when a user collects 100% of a series
    (every base + every variant + the rare/epic reward card).
    Idempotent: returns claimed=False if the user already received the bonus.
    """
    if series < 1 or series > MAX_DECLARED_SERIES:
        raise HTTPException(status_code=400, detail="Invalid series number")

    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    already_claimed = series in user.get("series_milestone_claimed", [])

    # All cards that count toward 100% for this series
    series_cards = await db.cards.find({
        "$or": [
            {"series": series},
            {"series_reward": series},
        ]
    }, {"_id": 0, "id": 1}).to_list(500)
    required_ids = {c["id"] for c in series_cards}

    if not required_ids:
        raise HTTPException(status_code=404, detail="No cards found for series")

    user_cards = await db.user_cards.find(
        {"user_id": user_id, "card_id": {"$in": list(required_ids)}}
    ).to_list(1000)
    owned_ids = {uc["card_id"] for uc in user_cards}

    is_complete = required_ids.issubset(owned_ids)
    total_required = len(required_ids)
    total_owned = len(owned_ids & required_ids)

    if already_claimed:
        return {
            "claimed": False,
            "already_claimed": True,
            "is_complete": is_complete,
            "total_required": total_required,
            "total_owned": total_owned,
            "medals_awarded": 0,
            "total_medals": user.get("medals", 0),
            "series": series,
        }

    if not is_complete:
        return {
            "claimed": False,
            "already_claimed": False,
            "is_complete": False,
            "total_required": total_required,
            "total_owned": total_owned,
            "medals_awarded": 0,
            "total_medals": user.get("medals", 0),
            "series": series,
        }

    # Atomically award the bonus
    new_total_medals = user.get("medals", 0) + SERIES_MILESTONE_MEDAL_REWARD
    await db.users.update_one(
        {"id": user_id},
        {
            "$set": {"medals": new_total_medals},
            "$addToSet": {"series_milestone_claimed": series},
        },
    )

    series_name = SERIES_CONFIG.get(series, {}).get("name", f"Series {series}")

    return {
        "claimed": True,
        "already_claimed": False,
        "is_complete": True,
        "total_required": total_required,
        "total_owned": total_owned,
        "medals_awarded": SERIES_MILESTONE_MEDAL_REWARD,
        "total_medals": new_total_medals,
        "series": series,
        "series_name": series_name,
    }

# =====================
# Milestone Reward System
# =====================

async def check_milestone_reward(user_id: str):
    """Award a free common card every 10 cards collected"""
    # Get user's total cards (including duplicates)
    user_cards = await db.user_cards.find({"user_id": user_id}).to_list(1000)
    total_cards = sum(uc.get("quantity", 1) for uc in user_cards)
    
    # Get user's milestone tracking (how many milestones have been claimed)
    user = await db.users.find_one({"id": user_id})
    milestones_claimed = user.get("milestones_claimed", 0)
    
    # Calculate how many milestones user should have based on total cards
    milestones_earned = total_cards // 10
    
    # If user has earned a new milestone they haven't claimed yet
    if milestones_earned > milestones_claimed:
        # Get all available common cards
        common_cards = await db.cards.find({
            "rarity": "common", 
            "available": True
        }).to_list(100)
        
        if common_cards:
            import random
            # Pick a random common card
            reward_card = random.choice(common_cards)
            
            # Add card to user's collection
            existing_user_card = await db.user_cards.find_one({
                "user_id": user_id,
                "card_id": reward_card["id"]
            })
            
            if existing_user_card:
                await db.user_cards.update_one(
                    {"_id": existing_user_card["_id"]},
                    {"$inc": {"quantity": 1}}
                )
            else:
                user_card = UserCard(user_id=user_id, card_id=reward_card["id"])
                await db.user_cards.insert_one(user_card.dict())
            
            # Update user's milestone count
            await db.users.update_one(
                {"id": user_id},
                {"$set": {"milestones_claimed": milestones_claimed + 1}}
            )
            
            logger.info(f"User {user_id} received milestone reward: {reward_card['name']} (milestone {milestones_claimed + 1})")
            
            return {
                "milestone_number": milestones_claimed + 1,
                "card": Card(**reward_card),
                "next_milestone_at": (milestones_claimed + 2) * 10
            }
    
    return None

# =====================
# Rare Card Achievement System
# =====================

async def check_rare_card_achievements(user_id: str):
    """Check if user has unlocked any rare achievement cards for purchase based on their collection size"""
    # Count total cards (including duplicates) owned by user
    user_cards = await db.user_cards.find({"user_id": user_id}).to_list(1000)
    total_cards = sum(uc.get("quantity", 1) for uc in user_cards)
    
    # Get user's unlocked rare cards
    user = await db.users.find_one({"id": user_id})
    unlocked_rares = user.get("unlocked_rare_cards", [])
    
    # Get all rare and epic cards that require achievements (epic reward cards
    # like Alien Dubin use the same achievement-gate flow as rare ones).
    rare_cards = await db.cards.find({"rarity": {"$in": ["rare", "epic"]}, "achievement_required": {"$ne": None}}).to_list(100)
    
    newly_unlocked = None
    
    for rare_card in rare_cards:
        required_cards = rare_card.get("achievement_required", 0)
        
        if total_cards >= required_cards and rare_card["id"] not in unlocked_rares:
            # Mark as unlocked (purchasable) - don't auto-award
            await db.users.update_one(
                {"id": user_id},
                {"$addToSet": {"unlocked_rare_cards": rare_card["id"]}}
            )
            logger.info(f"User {user_id} unlocked rare card for purchase: {rare_card['name']}")
            newly_unlocked = Card(**rare_card)
    
    return newly_unlocked

@api_router.get("/users/{user_id}/check-rare-cards")
async def check_user_rare_cards(user_id: str):
    """Check status of all rare cards for a user"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's total card count
    user_cards = await db.user_cards.find({"user_id": user_id}).to_list(1000)
    total_cards = sum(uc.get("quantity", 1) for uc in user_cards)
    
    unlocked_rares = user.get("unlocked_rare_cards", [])
    
    # Get all rare/epic achievement cards and their status for this user
    rare_cards = await db.cards.find({"rarity": {"$in": ["rare", "epic"]}, "achievement_required": {"$ne": None}}).to_list(100)
    
    rare_cards_status = []
    newly_unlocked = None
    
    for rare_card in rare_cards:
        owned = await db.user_cards.find_one({
            "user_id": user_id,
            "card_id": rare_card["id"]
        })
        
        required = rare_card.get("achievement_required", 0)
        progress = min(total_cards, required) if required else 0
        is_unlocked = rare_card["id"] in unlocked_rares or total_cards >= required
        
        # Auto-unlock if achievement requirement met
        if total_cards >= required and rare_card["id"] not in unlocked_rares:
            await db.users.update_one(
                {"id": user_id},
                {"$addToSet": {"unlocked_rare_cards": rare_card["id"]}}
            )
            is_unlocked = True
            if not owned:
                newly_unlocked = Card(**rare_card)
        
        rare_cards_status.append({
            "card": Card(**rare_card),
            "owned": owned is not None,
            "unlocked": is_unlocked,  # Can purchase
            "required_cards": required,
            "progress": progress,
            "can_purchase": is_unlocked and not owned
        })
    
    # Calculate milestone info
    milestones_claimed = user.get("milestones_claimed", 0)
    next_milestone_at = (milestones_claimed + 1) * 10
    cards_to_next_milestone = max(0, next_milestone_at - total_cards)
    
    return {
        "total_cards": total_cards,
        "rare_cards": rare_cards_status,
        "newly_unlocked": newly_unlocked,
        "milestone_info": {
            "milestones_claimed": milestones_claimed,
            "next_milestone_at": next_milestone_at,
            "cards_to_next_milestone": cards_to_next_milestone,
            "progress_to_next": total_cards % 5
        }
    }

# =====================
# Variant Trade-In System
# =====================

VARIANT_TYPES = ["Toxic", "Electric", "Hellfire", "Cosmic"]

@api_router.get("/users/{user_id}/trade-in-eligible")
async def get_trade_in_eligible_cards(user_id: str):
    """Get cards that are eligible for trade-in (5+ duplicates)"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's cards with quantities
    user_cards = await db.user_cards.find({"user_id": user_id}).to_list(1000)
    
    eligible_cards = []
    for uc in user_cards:
        quantity = uc.get("quantity", 1)
        if quantity >= 5:
            # Get the base card info
            card = await db.cards.find_one({"id": uc["card_id"]})
            if card and not card.get("is_variant", False):
                # Check if this card has variants
                variants = await db.cards.find({
                    "base_card_id": card["id"],
                    "is_variant": True
                }).to_list(10)
                
                if variants:
                    # Get which variants user already owns
                    owned_variant_ids = []
                    for v in variants:
                        owned = await db.user_cards.find_one({
                            "user_id": user_id,
                            "card_id": v["id"]
                        })
                        if owned:
                            owned_variant_ids.append(v["id"])
                    
                    # Check if user can still get more variants
                    unowned_variants = [v for v in variants if v["id"] not in owned_variant_ids]
                    
                    if unowned_variants:
                        card_copy = {k: v for k, v in card.items() if k != "_id"}
                        eligible_cards.append({
                            "card": Card(**card_copy),
                            "quantity": quantity,
                            "variants_owned": len(owned_variant_ids),
                            "variants_total": len(variants),
                            "can_trade": True
                        })
    
    return {"eligible_cards": eligible_cards}

@api_router.post("/users/{user_id}/trade-in/{card_id}")
async def trade_in_for_variant(user_id: str, card_id: str):
    """Trade in 5 duplicates of a card for a variant"""
    import random
    
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check user has this card with 5+ quantity
    user_card = await db.user_cards.find_one({
        "user_id": user_id,
        "card_id": card_id
    })
    
    if not user_card or user_card.get("quantity", 1) < 5:
        raise HTTPException(status_code=400, detail="Need at least 5 duplicates to trade in")
    
    # Get base card
    base_card = await db.cards.find_one({"id": card_id})
    if not base_card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    if base_card.get("is_variant", False):
        raise HTTPException(status_code=400, detail="Cannot trade in variant cards")
    
    # Get all variants for this card
    variants = await db.cards.find({
        "base_card_id": card_id,
        "is_variant": True
    }).to_list(10)
    
    if not variants:
        raise HTTPException(status_code=400, detail="No variants available for this card")
    
    # Get which variants user already owns
    owned_variant_ids = []
    for v in variants:
        owned = await db.user_cards.find_one({
            "user_id": user_id,
            "card_id": v["id"]
        })
        if owned:
            owned_variant_ids.append(v["id"])
    
    # Filter to unowned variants
    unowned_variants = [v for v in variants if v["id"] not in owned_variant_ids]
    
    if not unowned_variants:
        raise HTTPException(status_code=400, detail="You already own all variants of this card!")
    
    # Pick a random unowned variant
    won_variant = random.choice(unowned_variants)
    
    # Deduct 5 from user's card quantity
    new_quantity = user_card.get("quantity", 1) - 5
    if new_quantity <= 0:
        await db.user_cards.delete_one({"_id": user_card["_id"]})
    else:
        await db.user_cards.update_one(
            {"_id": user_card["_id"]},
            {"$set": {"quantity": new_quantity}}
        )
    
    # Add variant to user's collection (only if not already owned)
    existing_variant = await db.user_cards.find_one({
        "user_id": user_id,
        "card_id": won_variant["id"]
    })
    if not existing_variant:
        variant_user_card = UserCard(user_id=user_id, card_id=won_variant["id"])
        await db.user_cards.insert_one(variant_user_card.dict())
    
    logger.info(f"User {user_id} traded in 5x {base_card['name']} for variant: {won_variant['name']}")
    
    # Check if all 4 variants are now collected — award 200 coin bonus
    variants_now_owned = len(owned_variant_ids) + 1
    all_variants_complete = variants_now_owned >= len(variants)
    coin_bonus = 0
    
    if all_variants_complete:
        coin_bonus = 200
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"coins": coin_bonus}}
        )
        logger.info(f"User {user_id} completed all variants of {base_card['name']}! +200 coins bonus")
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "coins": 1})
    
    won_variant_copy = {k: v for k, v in won_variant.items() if k != "_id"}
    won_variant_copy = _with_scratch_cover(won_variant_copy)
    
    return {
        "success": True,
        "won_variant": Card(**won_variant_copy),
        "remaining_quantity": max(0, new_quantity),
        "variants_owned": variants_now_owned,
        "variants_total": len(variants),
        "all_variants_complete": all_variants_complete,
        "coin_bonus": coin_bonus,
        "new_coin_balance": updated_user.get("coins", 0) if updated_user else 0
    }

# =====================
# Goals System
# =====================

@api_router.get("/goals")
async def get_all_goals():
    """Get all available goals"""
    goals = await db.goals.find().to_list(100)
    return [Goal(**goal) for goal in goals]

@api_router.get("/users/{user_id}/goals")
async def get_user_goals(user_id: str):
    """Get user's goal progress.

    Self-heals the variant-master goals: re-evaluates them on every read so
    users who already owned variants before the goal was introduced see the
    correct progress on next load (no manual backfill script required).
    """
    # Lazy backfill — cheap (one query per series + one set intersection).
    try:
        await check_all_variants_series_goals(user_id)
    except Exception as e:
        # Never let a backfill failure block the goal list from rendering.
        logging.warning(f"Variant-goal backfill failed for {user_id}: {e}")

    user_goals = await db.user_goals.find({"user_id": user_id}).to_list(100)
    
    result = []
    for ug in user_goals:
        goal = await db.goals.find_one({"id": ug["goal_id"]})
        if goal:
            result.append({
                "user_goal": UserGoal(**ug),
                "goal": Goal(**goal)
            })
    
    return result

async def check_all_rarities_goal(user_id: str):
    """Check if user has collected at least one card from each rarity (common, rare, epic)"""
    # Get the goal
    goal = await db.goals.find_one({"goal_type": "collect_all_rarities"})
    if not goal:
        return
    
    # Get user's goal progress
    user_goal = await db.user_goals.find_one({
        "user_id": user_id,
        "goal_id": goal["id"]
    })
    
    if not user_goal:
        user_goal_obj = UserGoal(user_id=user_id, goal_id=goal["id"])
        await db.user_goals.insert_one(user_goal_obj.dict())
        user_goal = user_goal_obj.dict()
    
    if user_goal.get("completed"):
        return
    
    # Get user's cards with their rarities
    user_cards = await db.user_cards.find({"user_id": user_id}).to_list(1000)
    rarities_collected = set()
    
    for uc in user_cards:
        card = await db.cards.find_one({"id": uc["card_id"]})
        if card:
            rarities_collected.add(card.get("rarity"))
    
    # Count how many of the 3 rarities they have
    required_rarities = {"common", "rare", "epic"}
    collected_count = len(rarities_collected.intersection(required_rarities))
    
    # Update progress
    await db.user_goals.update_one(
        {"id": user_goal["id"]},
        {"$set": {"progress": collected_count}}
    )
    
    # Check if completed (has all 3 rarities)
    if collected_count >= 3:
        await db.user_goals.update_one(
            {"id": user_goal["id"]},
            {"$set": {
                "completed": True,
                "completed_at": datetime.utcnow()
            }}
        )
        
        # Award coins
        user = await db.users.find_one({"id": user_id})
        new_coins = user.get("coins", 0) + goal["reward_coins"]
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"coins": new_coins}}
        )
        logging.info(f"User {user_id} completed Card Enthusiast goal! +{goal['reward_coins']} coins")

async def check_all_variants_series_goals(user_id: str):
    """Check if user has collected every variant card in each series.
    target_value on the goal stores the series number (1..5)."""
    goals = await db.goals.find({"goal_type": "collect_all_variants_series"}).to_list(50)
    if not goals:
        return
    
    # Get all of the user's collected card IDs once
    user_cards = await db.user_cards.find({"user_id": user_id}).to_list(2000)
    user_card_ids = {uc["card_id"] for uc in user_cards}
    
    for goal in goals:
        series_num = goal.get("target_value", 0)
        # Get total variant cards for this series
        all_variants = await db.cards.find(
            {"is_variant": True, "series": series_num}, {"id": 1, "_id": 0}
        ).to_list(1000)
        if not all_variants:
            continue
        total = len(all_variants)
        owned = sum(1 for v in all_variants if v["id"] in user_card_ids)
        
        # Get/create user_goal
        user_goal = await db.user_goals.find_one({
            "user_id": user_id, "goal_id": goal["id"]
        })
        if not user_goal:
            user_goal_obj = UserGoal(user_id=user_id, goal_id=goal["id"])
            await db.user_goals.insert_one(user_goal_obj.dict())
            user_goal = user_goal_obj.dict()
        
        if user_goal.get("completed"):
            continue
        
        # Update progress (count of owned variants)
        await db.user_goals.update_one(
            {"id": user_goal["id"]},
            {"$set": {"progress": owned}}
        )
        
        if owned >= total:
            await db.user_goals.update_one(
                {"id": user_goal["id"]},
                {"$set": {"completed": True, "completed_at": datetime.utcnow()}}
            )
            user = await db.users.find_one({"id": user_id})
            new_coins = user.get("coins", 0) + goal["reward_coins"]
            await db.users.update_one({"id": user_id}, {"$set": {"coins": new_coins}})
            logging.info(f"User {user_id} completed Series {series_num} variant goal! +{goal['reward_coins']} coins")

async def check_and_update_goals(user_id: str, goal_type: str, current_value: int):
    """Check and update goals based on progress"""
    goals = await db.goals.find({"goal_type": goal_type}).to_list(100)
    
    for goal in goals:
        user_goal = await db.user_goals.find_one({
            "user_id": user_id,
            "goal_id": goal["id"]
        })
        
        if not user_goal:
            user_goal_obj = UserGoal(user_id=user_id, goal_id=goal["id"])
            await db.user_goals.insert_one(user_goal_obj.dict())
            user_goal = user_goal_obj.dict()
        
        if user_goal.get("completed"):
            continue
        
        # Update progress
        await db.user_goals.update_one(
            {"id": user_goal["id"]},
            {"$set": {"progress": current_value}}
        )
        
        # Check if goal is completed
        if current_value >= goal["target_value"]:
            await db.user_goals.update_one(
                {"id": user_goal["id"]},
                {"$set": {
                    "completed": True,
                    "completed_at": datetime.utcnow()
                }}
            )
            
            # Award rewards
            user = await db.users.find_one({"id": user_id})
            new_coins = user.get("coins", 0) + goal["reward_coins"]
            await db.users.update_one(
                {"id": user_id},
                {"$set": {"coins": new_coins}}
            )
            
            # Award card if applicable
            if goal.get("reward_card_id"):
                existing = await db.user_cards.find_one({
                    "user_id": user_id,
                    "card_id": goal["reward_card_id"]
                })
                if existing:
                    await db.user_cards.update_one(
                        {"id": existing["id"]},
                        {"$inc": {"quantity": 1}}
                    )
                else:
                    user_card = UserCard(
                        user_id=user_id,
                        card_id=goal["reward_card_id"]
                    )
                    await db.user_cards.insert_one(user_card.dict())
            
            logger.info(f"User {user_id} completed goal: {goal['title']}")

@api_router.post("/users/{user_id}/claim-goal/{goal_id}")
async def claim_goal_reward(user_id: str, goal_id: str):
    """Manually claim a goal reward (if auto-claim wasn't triggered)"""
    user_goal = await db.user_goals.find_one({
        "user_id": user_id,
        "goal_id": goal_id
    })
    
    if not user_goal:
        raise HTTPException(status_code=404, detail="Goal not found for user")
    
    goal = await db.goals.find_one({"id": goal_id})
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    if user_goal.get("completed"):
        raise HTTPException(status_code=400, detail="Goal already claimed")
    
    if user_goal.get("progress", 0) < goal["target_value"]:
        raise HTTPException(status_code=400, detail="Goal not yet completed")
    
    # Mark as completed and award rewards
    await db.user_goals.update_one(
        {"id": user_goal["id"]},
        {"$set": {
            "completed": True,
            "completed_at": datetime.utcnow()
        }}
    )
    
    user = await db.users.find_one({"id": user_id})
    new_coins = user.get("coins", 0) + goal["reward_coins"]
    await db.users.update_one({"id": user_id}, {"$set": {"coins": new_coins}})
    
    card_awarded = None
    if goal.get("reward_card_id"):
        existing = await db.user_cards.find_one({
            "user_id": user_id,
            "card_id": goal["reward_card_id"]
        })
        if existing:
            await db.user_cards.update_one(
                {"id": existing["id"]},
                {"$inc": {"quantity": 1}}
            )
        else:
            user_card = UserCard(user_id=user_id, card_id=goal["reward_card_id"])
            await db.user_cards.insert_one(user_card.dict())
        
        card = await db.cards.find_one({"id": goal["reward_card_id"]})
        card_awarded = Card(**card) if card else None
    
    return {
        "success": True,
        "coins_awarded": goal["reward_coins"],
        "card_awarded": card_awarded
    }

# =====================
# Trading System
# =====================

@api_router.post("/trades")
async def create_trade(request: CreateTradeRequest):
    """Create a new trade offer"""
    # Verify both users exist
    from_user = await db.users.find_one({"id": request.from_user_id})
    to_user = await db.users.find_one({"id": request.to_user_id})
    
    if not from_user or not to_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if request.from_user_id == request.to_user_id:
        raise HTTPException(status_code=400, detail="Cannot trade with yourself")
    
    # Verify users are friends
    friendship = await db.friends.find_one({
        "$or": [
            {"user_id": request.from_user_id, "friend_id": request.to_user_id},
            {"user_id": request.to_user_id, "friend_id": request.from_user_id}
        ]
    })
    if not friendship:
        raise HTTPException(status_code=400, detail="You must be friends to trade")
    
    # Verify from_user owns offered cards
    for card_id in request.offered_card_ids:
        user_card = await db.user_cards.find_one({
            "user_id": request.from_user_id,
            "card_id": card_id
        })
        if not user_card or user_card.get("quantity", 0) < 1:
            raise HTTPException(status_code=400, detail=f"You don't own card {card_id}")
    
    # Verify to_user owns requested cards
    for card_id in request.requested_card_ids:
        user_card = await db.user_cards.find_one({
            "user_id": request.to_user_id,
            "card_id": card_id
        })
        if not user_card or user_card.get("quantity", 0) < 1:
            raise HTTPException(status_code=400, detail=f"Target user doesn't own card {card_id}")
    
    trade = Trade(
        from_user_id=request.from_user_id,
        to_user_id=request.to_user_id,
        offered_card_ids=request.offered_card_ids,
        requested_card_ids=request.requested_card_ids
    )
    
    await db.trades.insert_one(trade.dict())
    return trade

@api_router.get("/users/{user_id}/trades")
async def get_user_trades(user_id: str):
    """Get all trades involving a user"""
    trades = await db.trades.find({
        "$or": [
            {"from_user_id": user_id},
            {"to_user_id": user_id}
        ]
    }).to_list(100)
    
    result = []
    for trade in trades:
        from_user = await db.users.find_one({"id": trade["from_user_id"]})
        to_user = await db.users.find_one({"id": trade["to_user_id"]})
        
        offered_cards = []
        for card_id in trade["offered_card_ids"]:
            card = await db.cards.find_one({"id": card_id})
            if card:
                offered_cards.append(Card(**card))
        
        requested_cards = []
        for card_id in trade["requested_card_ids"]:
            card = await db.cards.find_one({"id": card_id})
            if card:
                requested_cards.append(Card(**card))
        
        result.append({
            "trade": Trade(**trade),
            "from_user": User(**from_user) if from_user else None,
            "to_user": User(**to_user) if to_user else None,
            "offered_cards": offered_cards,
            "requested_cards": requested_cards
        })
    
    return result

@api_router.post("/trades/{trade_id}/action")
async def trade_action(trade_id: str, request: TradeActionRequest):
    """Accept, reject, or cancel a trade"""
    trade = await db.trades.find_one({"id": trade_id})
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    if trade["status"] != "pending":
        raise HTTPException(status_code=400, detail="Trade is no longer pending")
    
    if request.action == "cancel":
        if request.user_id != trade["from_user_id"]:
            raise HTTPException(status_code=403, detail="Only sender can cancel")
        await db.trades.update_one({"id": trade_id}, {"$set": {"status": "cancelled"}})
        return {"success": True, "message": "Trade cancelled"}
    
    if request.action == "reject":
        if request.user_id != trade["to_user_id"]:
            raise HTTPException(status_code=403, detail="Only recipient can reject")
        await db.trades.update_one({"id": trade_id}, {"$set": {"status": "rejected"}})
        return {"success": True, "message": "Trade rejected"}
    
    if request.action == "accept":
        if request.user_id != trade["to_user_id"]:
            raise HTTPException(status_code=403, detail="Only recipient can accept")
        
        # Transfer cards from sender to recipient
        for card_id in trade["offered_card_ids"]:
            # Decrease sender's quantity
            sender_card = await db.user_cards.find_one({
                "user_id": trade["from_user_id"],
                "card_id": card_id
            })
            if sender_card["quantity"] <= 1:
                await db.user_cards.delete_one({"id": sender_card["id"]})
            else:
                await db.user_cards.update_one(
                    {"id": sender_card["id"]},
                    {"$inc": {"quantity": -1}}
                )
            
            # Increase recipient's quantity
            recipient_card = await db.user_cards.find_one({
                "user_id": trade["to_user_id"],
                "card_id": card_id
            })
            if recipient_card:
                await db.user_cards.update_one(
                    {"id": recipient_card["id"]},
                    {"$inc": {"quantity": 1}}
                )
            else:
                new_card = UserCard(
                    user_id=trade["to_user_id"],
                    card_id=card_id
                )
                await db.user_cards.insert_one(new_card.dict())
        
        # Transfer cards from recipient to sender
        for card_id in trade["requested_card_ids"]:
            # Decrease recipient's quantity
            recipient_card = await db.user_cards.find_one({
                "user_id": trade["to_user_id"],
                "card_id": card_id
            })
            if recipient_card["quantity"] <= 1:
                await db.user_cards.delete_one({"id": recipient_card["id"]})
            else:
                await db.user_cards.update_one(
                    {"id": recipient_card["id"]},
                    {"$inc": {"quantity": -1}}
                )
            
            # Increase sender's quantity
            sender_card = await db.user_cards.find_one({
                "user_id": trade["from_user_id"],
                "card_id": card_id
            })
            if sender_card:
                await db.user_cards.update_one(
                    {"id": sender_card["id"]},
                    {"$inc": {"quantity": 1}}
                )
            else:
                new_card = UserCard(
                    user_id=trade["from_user_id"],
                    card_id=card_id
                )
                await db.user_cards.insert_one(new_card.dict())
        
        await db.trades.update_one({"id": trade_id}, {"$set": {"status": "accepted"}})
        return {"success": True, "message": "Trade completed!"}
    
    raise HTTPException(status_code=400, detail="Invalid action")

# =====================
# Root & Health Check
# =====================

# =====================
# Coin Purchase / Payment Endpoints
# =====================

@api_router.get("/coin-packages")
async def get_coin_packages():
    """Get available coin purchase packages"""
    return list(COIN_PACKAGES.values())

@api_router.get("/users/{user_id}/coin-packages")
async def get_user_coin_packages(user_id: str):
    """Get coin packages with first-purchase bonus info for a specific user"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user has made any successful purchases
    has_purchased = await db.payment_transactions.find_one({
        "user_id": user_id,
        "payment_status": "paid"
    })
    
    is_first_purchase = has_purchased is None
    
    packages_with_bonus = []
    for pkg in COIN_PACKAGES.values():
        package_copy = pkg.copy()
        
        # Calculate bonus coins for first purchase
        if is_first_purchase:
            bonus_coins = int(pkg["coins"] * FIRST_PURCHASE_BONUS_PERCENTAGE / 100)
            package_copy["bonus_coins"] = bonus_coins
            package_copy["total_coins"] = pkg["coins"] + bonus_coins
            package_copy["first_purchase_bonus"] = True
        else:
            package_copy["bonus_coins"] = 0
            package_copy["total_coins"] = pkg["coins"]
            package_copy["first_purchase_bonus"] = False
        
        # Calculate effective coins per dollar (including bonus)
        package_copy["effective_coins_per_dollar"] = round(package_copy["total_coins"] / pkg["price"], 1)
        
        packages_with_bonus.append(package_copy)
    
    return {
        "packages": packages_with_bonus,
        "is_first_purchase": is_first_purchase,
        "first_purchase_bonus_percentage": FIRST_PURCHASE_BONUS_PERCENTAGE if is_first_purchase else 0
    }

@api_router.post("/admin/add-coins/{user_id}")
async def admin_add_coins(user_id: str, request: Request):
    """Admin endpoint to add coins to a user"""
    body = await request.json()
    amount = body.get("amount", 0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    new_coins = user.get("coins", 0) + amount
    await db.users.update_one({"id": user_id}, {"$set": {"coins": new_coins}})
    return {"username": user["username"], "coins": new_coins}


@api_router.post("/admin/set-streak/{user_id}")
async def admin_set_streak(user_id: str, request: Request):
    """Admin endpoint to restore a user's daily login streak.

    Used to make users whole after they were locked out of the app for several
    days by broken testing-track builds. Sets streak + dates atomically so the
    next login on a new calendar day will increment, not reset.
    """
    body = await request.json()
    streak = body.get("streak", 0)
    if streak < 0 or streak > 9999:
        raise HTTPException(status_code=400, detail="Streak out of range")
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Set last_login_date to YESTERDAY so the next /login bumps streak to N+1
    # rather than resetting to 1. If we set today, the next login would short-
    # circuit ("already logged in today") and leave the value alone — fine but
    # less satisfying. Yesterday gives the user immediate "Day N+1!" gratification.
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"daily_login_streak": streak, "last_login_date": yesterday}},
    )
    return {"username": user["username"], "daily_login_streak": streak}

# Feedback and Friends endpoints live in /app/backend/routers/feedback.py and friends.py
# They are mounted onto api_router at server startup (see end of this file).

# =====================
# Daily Wheel & Medals System
# =====================

@api_router.get("/users/{user_id}/daily-wheel")
async def get_daily_wheel_status(user_id: str):
    """Check if user can spin the daily wheel"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    today = datetime.utcnow().strftime("%Y-%m-%d")
    last_wheel_spin = user.get("last_wheel_spin", "")
    can_spin = last_wheel_spin != today
    medals = user.get("medals", 0)
    free_packs = user.get("free_packs", 0)
    wheel_streak = user.get("wheel_streak", 0)
    
    return {
        "can_spin": can_spin,
        "medals": medals,
        "free_packs": free_packs,
        "wheel_streak": wheel_streak,
        "prizes": DAILY_WHEEL_PRIZES,
        "last_spin": last_wheel_spin,
        "reroll_cost": REROLL_COST_MEDALS,
        "free_pack_cost": FREE_PACK_COST_MEDALS,
    }

@api_router.post("/users/{user_id}/daily-wheel/spin")
async def spin_daily_wheel(user_id: str):
    """Spin the daily wheel for a prize"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    today = datetime.utcnow().strftime("%Y-%m-%d")
    last_wheel_spin = user.get("last_wheel_spin", "")
    
    if last_wheel_spin == today:
        raise HTTPException(status_code=400, detail="Already spun today! Come back tomorrow.")
    
    # Check streak
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    old_streak = user.get("wheel_streak", 0)
    new_streak = (old_streak + 1) if last_wheel_spin == yesterday else 1
    
    # Pick weighted random prize
    # On 7-day streak, guarantee a big prize
    if new_streak >= 7 and new_streak % 7 == 0:
        big_prizes = [p for p in DAILY_WHEEL_PRIZES if p["type"] == "free_pack" or (p["type"] == "medals" and p["amount"] >= 5) or (p["type"] == "coins" and p["amount"] >= 200)]
        prize = random.choice(big_prizes) if big_prizes else random.choice(DAILY_WHEEL_PRIZES)
    else:
        weights = [p["weight"] for p in DAILY_WHEEL_PRIZES]
        prize = random.choices(DAILY_WHEEL_PRIZES, weights=weights, k=1)[0]
    
    # Apply prize
    update = {
        "last_wheel_spin": today,
        "wheel_streak": new_streak,
    }
    
    if prize["type"] == "coins":
        update["coins"] = user.get("coins", 0) + prize["amount"]
    elif prize["type"] == "medals":
        update["medals"] = user.get("medals", 0) + prize["amount"]
    elif prize["type"] == "free_pack":
        update["free_packs"] = user.get("free_packs", 0) + prize["amount"]
    
    await db.users.update_one({"id": user_id}, {"$set": update})
    
    return {
        "success": True,
        "prize": prize,
        "streak": new_streak,
        "streak_bonus": new_streak >= 7 and new_streak % 7 == 0,
        "medals": update.get("medals", user.get("medals", 0)),
        "coins": update.get("coins", user.get("coins", 0)),
        "free_packs": update.get("free_packs", user.get("free_packs", 0)),
    }

@api_router.post("/users/{user_id}/reroll")
async def reroll_pack(user_id: str, request: Request):
    """Reroll all 3 cards in a pack for medals"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    medals = user.get("medals", 0)
    if medals < REROLL_COST_MEDALS:
        raise HTTPException(status_code=400, detail=f"Need {REROLL_COST_MEDALS} medals to reroll. You have {medals}.")
    
    body = await request.json()
    series = body.get("series", 1)
    old_card_ids = body.get("old_card_ids", [])
    
    # Get available cards for the series
    series_cards = await db.cards.find({
        "series": series,
        "rarity": "common",
        "available": True,
        "engagement_milestone": None
    }).to_list(100)
    
    if not series_cards:
        raise HTTPException(status_code=400, detail="No cards available")
    
    # Remove old cards from collection
    for card_id in old_card_ids:
        existing = await db.user_cards.find_one({"user_id": user_id, "card_id": card_id})
        if existing:
            if existing.get("quantity", 1) > 1:
                await db.user_cards.update_one({"id": existing["id"]}, {"$inc": {"quantity": -1}})
            else:
                await db.user_cards.delete_one({"id": existing["id"]})
    
    # Pick 3 new random cards
    won_cards = random.choices(series_cards, k=3)
    
    cards_result = []
    for won_card in won_cards:
        existing_user_card = await db.user_cards.find_one({"user_id": user_id, "card_id": won_card["id"]})
        is_duplicate = existing_user_card is not None
        if existing_user_card:
            await db.user_cards.update_one({"id": existing_user_card["id"]}, {"$inc": {"quantity": 1}})
        else:
            user_card = UserCard(user_id=user_id, card_id=won_card["id"])
            await db.user_cards.insert_one(user_card.dict())
        cards_result.append({"card": Card(**_with_scratch_cover(won_card)), "is_duplicate": is_duplicate})
    
    # Deduct medals
    new_medals = medals - REROLL_COST_MEDALS
    await db.users.update_one({"id": user_id}, {"$set": {"medals": new_medals}})
    
    return {
        "success": True,
        "won_cards": cards_result,
        "remaining_medals": new_medals,
    }

# =====================
# Card Picker Mini-Game
# =====================

CARD_PICKER_PRIZES = [
    {"type": "free_pack", "amount": 1, "label": "1 Free Pack"},
    {"type": "medals", "amount": 1, "label": "1 Medal"},
    {"type": "medals", "amount": 2, "label": "2 Medals"},
    {"type": "medals", "amount": 3, "label": "3 Medals"},
]
CARD_PICKER_COOLDOWN_HOURS = 24


def _card_picker_cooldown_remaining(user: dict) -> int:
    """Seconds until the user can play again (0 if eligible)."""
    last = user.get("card_picker_last_played")
    if not last:
        return 0
    if isinstance(last, str):
        try:
            last = datetime.fromisoformat(last)
        except Exception:
            return 0
    elapsed = (datetime.utcnow() - last).total_seconds()
    cooldown = CARD_PICKER_COOLDOWN_HOURS * 3600
    return max(0, int(cooldown - elapsed))


@api_router.get("/users/{user_id}/card-picker")
async def get_card_picker(user_id: str):
    """Get card picker state: layout (4 prizes shown twice = 8 cards), cooldown."""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    cooldown = _card_picker_cooldown_remaining(user)
    return {
        "can_play": cooldown == 0,
        "cooldown_seconds": cooldown,
        "prizes": CARD_PICKER_PRIZES,
    }


@api_router.post("/users/{user_id}/card-picker/claim")
async def claim_card_picker_prize(user_id: str, request: Request):
    """Player matched a pair. Server grants the prize they actually matched
    (identified by `prize_label` in the request body). Falls back to a random
    prize if the client didn't send a label, to remain backward compatible."""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    cooldown = _card_picker_cooldown_remaining(user)
    if cooldown > 0:
        raise HTTPException(
            status_code=400,
            detail=f"You already played today. Try again in {cooldown // 3600}h {(cooldown % 3600) // 60}m.",
        )

    # Determine which prize the user actually matched.
    body: dict = {}
    try:
        body = await request.json()
    except Exception:
        pass
    requested_label = body.get("prize_label") if isinstance(body, dict) else None

    if requested_label:
        prize = next(
            (p for p in CARD_PICKER_PRIZES if p.get("label") == requested_label),
            None,
        )
        if prize is None:
            raise HTTPException(status_code=400, detail="Unknown prize label")
    else:
        prize = random.choice(CARD_PICKER_PRIZES)

    update = {"card_picker_last_played": datetime.utcnow()}
    if prize["type"] == "free_pack":
        update["free_packs"] = user.get("free_packs", 0) + prize["amount"]
    elif prize["type"] == "medals":
        update["medals"] = user.get("medals", 0) + prize["amount"]

    await db.users.update_one({"id": user_id}, {"$set": update})

    return {
        "success": True,
        "prize": prize,
        "free_packs": update.get("free_packs", user.get("free_packs", 0)),
        "medals": update.get("medals", user.get("medals", 0)),
    }


@api_router.post("/users/{user_id}/redeem-free-pack")
async def redeem_free_pack(user_id: str, request: Request):
    """Use a free pack or spend medals for a free pack"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    body = await request.json()
    series = body.get("series", 1)
    use_medals = body.get("use_medals", False)
    
    free_packs = user.get("free_packs", 0)
    medals = user.get("medals", 0)
    
    if use_medals:
        if medals < FREE_PACK_COST_MEDALS:
            raise HTTPException(status_code=400, detail=f"Need {FREE_PACK_COST_MEDALS} medals. You have {medals}.")
        await db.users.update_one({"id": user_id}, {"$set": {"medals": medals - FREE_PACK_COST_MEDALS}})
    elif free_packs > 0:
        await db.users.update_one({"id": user_id}, {"$set": {"free_packs": free_packs - 1}})
    else:
        raise HTTPException(status_code=400, detail="No free packs available")
    
    # Get cards for the series
    series_cards = await db.cards.find({
        "series": series,
        "rarity": "common",
        "available": True,
        "engagement_milestone": None
    }).to_list(100)
    
    if not series_cards:
        raise HTTPException(status_code=400, detail="No cards available")
    
    won_cards = random.choices(series_cards, k=3)
    
    cards_result = []
    for won_card in won_cards:
        existing_user_card = await db.user_cards.find_one({"user_id": user_id, "card_id": won_card["id"]})
        is_duplicate = existing_user_card is not None
        if existing_user_card:
            await db.user_cards.update_one({"id": existing_user_card["id"]}, {"$inc": {"quantity": 1}})
        else:
            user_card = UserCard(user_id=user_id, card_id=won_card["id"])
            await db.user_cards.insert_one(user_card.dict())
        cards_result.append({"card": Card(**_with_scratch_cover(won_card)), "is_duplicate": is_duplicate})
    
    # Check series completion
    series_completion = await check_series_completion(user_id, series)
    
    updated_user = await db.users.find_one({"id": user_id})
    
    return {
        "success": True,
        "won_cards": cards_result,
        "remaining_coins": updated_user.get("coins", 0),
        "remaining_medals": updated_user.get("medals", 0),
        "remaining_free_packs": updated_user.get("free_packs", 0),
        "series_completion": series_completion,
    }

@api_router.get("/users/{user_id}/medals")
async def get_medals(user_id: str):
    """Get user's medal count and available rewards"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "medals": user.get("medals", 0),
        "free_packs": user.get("free_packs", 0),
        "reroll_cost": REROLL_COST_MEDALS,
        "free_pack_cost": FREE_PACK_COST_MEDALS,
    }

@api_router.post("/users/{user_id}/purchase-coins")
async def create_coin_checkout(user_id: str, request: CoinPurchaseRequest, http_request: Request):
    """Create a Stripe checkout session for purchasing coins"""
    # Validate user exists
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate package exists (NEVER accept amount from frontend)
    package = COIN_PACKAGES.get(request.package_id)
    if not package:
        raise HTTPException(status_code=400, detail="Invalid package")
    
    # Check if this is user's first purchase
    has_purchased = await db.payment_transactions.find_one({
        "user_id": user_id,
        "payment_status": "paid"
    })
    is_first_purchase = has_purchased is None
    
    # Calculate total coins including first-purchase bonus
    base_coins = package["coins"]
    bonus_coins = int(base_coins * FIRST_PURCHASE_BONUS_PERCENTAGE / 100) if is_first_purchase else 0
    total_coins = base_coins + bonus_coins
    
    # Get Stripe API key
    stripe_api_key = os.environ.get("STRIPE_API_KEY")
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Payment service not configured")
    
    # Build dynamic success/cancel URLs from frontend origin
    origin_url = request.origin_url.rstrip('/')
    success_url = f"{origin_url}/payment-success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin_url}/shop"
    
    # Initialize Stripe with API key
    stripe.api_key = stripe_api_key
    
    try:
        # Create Stripe checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': package["currency"],
                    'product_data': {
                        'name': f'{package["coins"]} Coins',
                        'description': f'Thrash Kan Kidz coin pack',
                    },
                    'unit_amount': int(package["price"] * 100),  # Stripe uses cents
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": user_id,
                "package_id": request.package_id,
                "coins_amount": str(total_coins),
                "base_coins": str(base_coins),
                "bonus_coins": str(bonus_coins),
                "is_first_purchase": str(is_first_purchase),
                "source": "thrashkan_app"
            }
        )
        
        # Create payment transaction record BEFORE redirecting to Stripe
        transaction = PaymentTransaction(
            user_id=user_id,
            session_id=session.id,
            package_id=request.package_id,
            amount=package["price"],
            currency=package["currency"],
            coins_amount=total_coins,  # Total including bonus
            payment_status="pending",
            status="initiated",
            metadata={
                "user_id": user_id,
                "package_id": request.package_id,
                "base_coins": str(base_coins),
                "bonus_coins": str(bonus_coins),
                "total_coins": str(total_coins),
                "is_first_purchase": str(is_first_purchase)
            }
        )
        await db.payment_transactions.insert_one(transaction.dict())
        
        return {
            "checkout_url": session.url,
            "session_id": session.id,
            "package": package,
            "is_first_purchase": is_first_purchase,
            "bonus_coins": bonus_coins,
            "total_coins": total_coins
        }
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")

# Google Play Billing verification endpoint
class GooglePlayPurchaseRequest(BaseModel):
    product_id: str
    purchase_token: str
    user_id: str

@api_router.post("/users/{user_id}/verify-google-purchase")
async def verify_google_play_purchase(user_id: str, request: GooglePlayPurchaseRequest):
    """Verify a Google Play in-app purchase and grant coins"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Map Google Play product ID to package
    package_id = GOOGLE_PLAY_PRODUCT_MAP.get(request.product_id)
    if not package_id:
        raise HTTPException(status_code=400, detail="Invalid product ID")
    
    package = COIN_PACKAGES[package_id]
    
    # Check for duplicate purchase token
    existing = await db.payment_transactions.find_one({
        "purchase_token": request.purchase_token,
        "payment_status": "paid"
    })
    if existing:
        raise HTTPException(status_code=400, detail="Purchase already processed")
    
    # Check first purchase bonus
    has_purchased = await db.payment_transactions.find_one({
        "user_id": user_id,
        "payment_status": "paid"
    })
    is_first_purchase = has_purchased is None
    
    base_coins = package["coins"]
    bonus_coins = int(base_coins * FIRST_PURCHASE_BONUS_PERCENTAGE / 100) if is_first_purchase else 0
    total_coins = base_coins + bonus_coins
    
    # Record transaction
    transaction = {
        "user_id": user_id,
        "package_id": package_id,
        "product_id": request.product_id,
        "purchase_token": request.purchase_token,
        "platform": "android",
        "payment_method": "google_play",
        "coins_amount": total_coins,
        "base_coins": base_coins,
        "bonus_coins": bonus_coins,
        "price": package["price"],
        "currency": package["currency"],
        "payment_status": "paid",
        "status": "completed",
        "is_first_purchase": is_first_purchase,
        "created_at": datetime.utcnow(),
    }
    await db.payment_transactions.insert_one(transaction)
    
    # Credit coins to user
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"coins": total_coins}}
    )
    
    logger.info(f"Google Play purchase verified: {total_coins} coins for user {user_id}")
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0})
    
    return {
        "success": True,
        "coins_granted": total_coins,
        "base_coins": base_coins,
        "bonus_coins": bonus_coins,
        "is_first_purchase": is_first_purchase,
        "new_balance": updated_user.get("coins", 0)
    }

@api_router.get("/payments/status/{session_id}")
async def get_payment_status(session_id: str):
    """Check the status of a payment session"""
    # Get transaction record
    transaction = await db.payment_transactions.find_one({"session_id": session_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Payment session not found")
    
    # If already completed, return immediately
    if transaction.get("payment_status") == "paid":
        return {
            "status": "completed",
            "payment_status": "paid",
            "coins_credited": transaction.get("coins_amount", 0),
            "already_processed": True
        }
    
    # Get Stripe API key
    stripe_api_key = os.environ.get("STRIPE_API_KEY")
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Payment service not configured")
    
    # Check with Stripe
    stripe.api_key = stripe_api_key
    
    try:
        # Retrieve session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        
        # Determine payment status
        payment_status = "paid" if session.payment_status == "paid" else session.payment_status
        
        # Update transaction status
        new_status = "completed" if payment_status == "paid" else transaction.get("status")
        
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {
                "payment_status": payment_status,
                "status": new_status,
                "updated_at": datetime.utcnow()
            }}
        )
        
        # If payment is successful and not already processed, credit coins
        coins_credited = 0
        if payment_status == "paid" and transaction.get("payment_status") != "paid":
            user_id = transaction.get("user_id")
            coins_amount = transaction.get("coins_amount", 0)
            
            # Credit coins to user
            await db.users.update_one(
                {"id": user_id},
                {"$inc": {"coins": coins_amount}}
            )
            coins_credited = coins_amount
            logger.info(f"Credited {coins_amount} coins to user {user_id} for session {session_id}")
        
        return {
            "status": new_status,
            "payment_status": payment_status,
            "amount_total": session.amount_total,
            "currency": session.currency,
            "coins_credited": coins_credited,
            "already_processed": transaction.get("payment_status") == "paid"
        }
    except Exception as e:
        logger.error(f"Error checking payment status: {e}")
        raise HTTPException(status_code=500, detail="Failed to check payment status")

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    stripe_api_key = os.environ.get("STRIPE_API_KEY")
    stripe_webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Payment service not configured")
    
    stripe.api_key = stripe_api_key
    
    try:
        body = await request.body()
        signature = request.headers.get("Stripe-Signature")
        
        # Verify webhook signature if secret is configured
        if stripe_webhook_secret and signature:
            try:
                event = stripe.Webhook.construct_event(body, signature, stripe_webhook_secret)
            except stripe.error.SignatureVerificationError:
                raise HTTPException(status_code=400, detail="Invalid signature")
        else:
            # Parse event without verification (not recommended for production)
            import json
            event = json.loads(body)
        
        # Process checkout.session.completed event
        if event.get("type") == "checkout.session.completed":
            session = event["data"]["object"]
            session_id = session["id"]
            payment_status = session.get("payment_status", "")
            
            if payment_status == "paid":
                # Find transaction and credit coins if not already done
                transaction = await db.payment_transactions.find_one({"session_id": session_id})
                if transaction and transaction.get("payment_status") != "paid":
                    user_id = transaction.get("user_id")
                    coins_amount = transaction.get("coins_amount", 0)
                    
                    # Credit coins
                    await db.users.update_one(
                        {"id": user_id},
                        {"$inc": {"coins": coins_amount}}
                    )
                    
                    # Update transaction
                    await db.payment_transactions.update_one(
                        {"session_id": session_id},
                        {"$set": {
                            "payment_status": "paid",
                            "status": "completed",
                            "updated_at": datetime.utcnow()
                        }}
                    )
                    logger.info(f"Webhook: Credited {coins_amount} coins to user {user_id}")
        
        return {"received": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@api_router.get("/users/{user_id}/payment-history")
async def get_payment_history(user_id: str):
    """Get user's payment transaction history"""
    transactions = await db.payment_transactions.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return transactions

# Static / metadata endpoints (root, health, downloads, privacy-policy,
# delete-account HTML) live in routers/static_pages.py.

# Mount modular routers (cards, static pages, feedback, friends).
# Must happen BEFORE include_router so endpoints register on api_router.
from routers import cards as cards_routes  # noqa: E402
from routers import static_pages as static_routes  # noqa: E402
from routers import feedback as feedback_routes  # noqa: E402
from routers import friends as friends_routes  # noqa: E402
from routers import mosh as mosh_routes  # noqa: E402
from routers import leaderboard as leaderboard_routes  # noqa: E402
from routers import app_version as app_version_routes  # noqa: E402
from routers import diagnostics as diagnostics_routes  # noqa: E402
api_router.include_router(cards_routes.router)
api_router.include_router(static_routes.router)
api_router.include_router(feedback_routes.router)
api_router.include_router(friends_routes.router)
api_router.include_router(mosh_routes.router)
api_router.include_router(leaderboard_routes.router)
api_router.include_router(app_version_routes.router)
api_router.include_router(diagnostics_routes.router)

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    await seed_database()
    # Load any persisted release-date overrides from MongoDB into the
    # series_config in-memory cache. After this awaits returns, the sync
    # release helpers (is_series_released, etc.) reflect the latest
    # admin-scheduled dates.
    await init_series_overrides(db)

    # One-time migration: when a new series launches, any user who had already
    # completed the prior series must get the new series added to
    # unlocked_series (the old completion handler hard-capped the unlock at
    # the previous max). Runs against `current_max_series()` so unreleased /
    # scheduled series are NOT auto-unlocked — they flip live the next time
    # the backend boots after their release_date has passed.
    max_visible = current_max_series()
    if max_visible > 1:
        backfill = await db.users.update_many(
            {
                "completed_series": max_visible - 1,
                "unlocked_series": {"$ne": max_visible},
            },
            {"$addToSet": {"unlocked_series": max_visible}},
        )
        if backfill.modified_count:
            logger.info(
                f"Series {max_visible} unlock backfill: {backfill.modified_count} user(s) updated"
            )

    # Series-reward backfill: grant the rare reward card to any user who owns
    # all required commons of a series but never received the reward (this can
    # happen when a series was added to SERIES_CONFIG *after* users already
    # completed it — e.g., Series 6).
    reward_grants = 0
    for series_num, cfg in SERIES_CONFIG.items():
        rare_reward_id = cfg.get("rare_reward")
        if not rare_reward_id:
            continue
        series_card_ids = await db.cards.distinct(
            "id", {"series": series_num, "rarity": "common"}
        )
        if not series_card_ids:
            continue
        # Pipeline: count distinct owned commons per user
        owners = await db.user_cards.aggregate([
            {"$match": {"card_id": {"$in": series_card_ids}}},
            {"$group": {"_id": "$user_id", "owned": {"$addToSet": "$card_id"}}},
            {"$match": {f"owned.{len(series_card_ids) - 1}": {"$exists": True}}},
        ]).to_list(10000)
        for o in owners:
            uid = o["_id"]
            existing_card = await db.user_cards.find_one(
                {"user_id": uid, "card_id": rare_reward_id}
            )
            user_doc = await db.users.find_one({"id": uid}, {"_id": 0, "unlocked_rare_cards": 1})
            already_unlocked = rare_reward_id in (
                user_doc.get("unlocked_rare_cards", []) if user_doc else []
            )
            if existing_card and already_unlocked:
                continue
            if not existing_card:
                user_card = UserCard(user_id=uid, card_id=rare_reward_id)
                await db.user_cards.insert_one(user_card.dict())
            await db.users.update_one(
                {"id": uid},
                {"$addToSet": {
                    "unlocked_rare_cards": rare_reward_id,
                    "completed_series": series_num,
                }},
            )
            reward_grants += 1
    if reward_grants:
        logger.info(f"Series-reward backfill: granted {reward_grants} missing reward(s)")

    # Epic-achievement backfill: historically the shop-unlock query only matched
    # `rarity: "rare"`, so epic cards with `achievement_required` (Sean
    # Kill-Again, Martin Generic Ain't, Nicklebag Darrell, Alien Dubin) never
    # unlocked despite players hitting the card-count threshold. Backfill any
    # qualifying users here so they don't have to wait for their next pack open.
    epic_unlock_grants = 0
    epic_achievement_cards = await db.cards.find(
        {"rarity": "epic", "achievement_required": {"$ne": None}},
        {"_id": 0, "id": 1, "name": 1, "achievement_required": 1},
    ).to_list(50)
    if epic_achievement_cards:
        # Per-user total card count, including duplicates.
        user_totals = await db.user_cards.aggregate([
            {"$group": {"_id": "$user_id", "total": {"$sum": "$quantity"}}},
        ]).to_list(10000)
        for ut in user_totals:
            for epic in epic_achievement_cards:
                if ut["total"] >= epic["achievement_required"]:
                    res = await db.users.update_one(
                        {"id": ut["_id"], "unlocked_rare_cards": {"$ne": epic["id"]}},
                        {"$addToSet": {"unlocked_rare_cards": epic["id"]}},
                    )
                    if res.modified_count:
                        epic_unlock_grants += 1
    if epic_unlock_grants:
        logger.info(
            f"Epic-achievement backfill: granted {epic_unlock_grants} shop-unlock(s)"
        )

    logger.info("Database seeded successfully")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

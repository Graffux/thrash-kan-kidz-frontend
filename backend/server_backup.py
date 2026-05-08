from fastapi import FastAPI, APIRouter, HTTPException, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timedelta
import base64
import random
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest

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
    created_at: datetime = Field(default_factory=datetime.utcnow)

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
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
    created_at: datetime = Field(default_factory=datetime.utcnow)

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
SPIN_COST = 50  # Coins per spin

# =====================
# Series Configuration
# =====================
# Each series has 16 cards (8 bands × 2 cards: A & B)
# Completing a series unlocks a rare card reward + next series
SERIES_CONFIG = {
    1: {
        "name": "Series 1",
        "cards_required": 16,
        "rare_reward": "card_kerry_the_king",  # Kerry the King is the Series 1 rare reward
        "description": "The Original Thrash Kan Kidz"
    },
    2: {
        "name": "Series 2", 
        "cards_required": 16,
        "rare_reward": "card_strap_on_taylor",  # Strap-On Taylor is the Series 2 rare reward
        "description": "More Mayhem"
    },
    3: {
        "name": "Series 3",
        "cards_required": 16,
        "rare_reward": "card_sean_kill_again",  # Sean Kill-Again is the Series 3 epic reward
        "description": "The Thrash Continues"
    }
}

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
        "name": "Starter Pack",
        "coins": 200,
        "price": 1.99,
        "currency": "usd",
        "description": "200 coins for new collectors",
        "coins_per_dollar": 100.5,  # 200 / 1.99
        "bonus_percentage": 0
    },
    "medium": {
        "id": "medium", 
        "name": "Collector Pack",
        "coins": 500,
        "price": 4.99,
        "currency": "usd",
        "description": "500 coins - Best for regular collectors",
        "coins_per_dollar": 100.2,  # 500 / 4.99
        "bonus_percentage": 0
    },
    "large": {
        "id": "large",
        "name": "Ultimate Pack",
        "coins": 1000,
        "price": 9.99,
        "currency": "usd",
        "description": "1000 coins - Best value!",
        "coins_per_dollar": 100.1,  # 1000 / 9.99
        "bonus_percentage": 0,
        "best_value": True
    }
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

INITIAL_CARDS = [
    # =====================
    # SERIES 1 - 8 bands, 16 cards (A & B for each band)
    # =====================
    # Band 1: $LAYA
    {
        "id": "card_tom_da_playa",
        "name": "Tom Da Playa",
        "description": "Tom Da Playa spends more time flossing gold chains than tuning his bass. Watch out—he'll sell you merch AND steal your girlfriend.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["tom_da_playa"],
        "back_image_url": CARD_BACK_IMAGE_URLS["tom_da_playa"],
        "coin_cost": 50,
        "available": True,
        "series": 1,
        "band": "$LAYA",
        "card_type": "A"
    },
    # Tom Da Playa Variants
    {
        "id": "card_tom_da_playa_toxic",
        "name": "Tom Da Playa (Toxic)",
        "description": "The Toxic variant of Tom Da Playa, dripping with radioactive slime. When he plays, the crowd glows green.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["tom_da_playa_toxic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_toxic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "$LAYA",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_tom_da_playa",
        "variant_name": "Toxic"
    },
    {
        "id": "card_tom_da_playa_electric",
        "name": "Tom Da Playa (Electric)",
        "description": "The Electric variant of Tom Da Playa, crackling with lightning energy. His bass lines are literally electrifying.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["tom_da_playa_electric"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_electric"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "$LAYA",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_tom_da_playa",
        "variant_name": "Electric"
    },
    {
        "id": "card_tom_da_playa_hellfire",
        "name": "Tom Da Playa (Hellfire)",
        "description": "The Hellfire variant of Tom Da Playa, engulfed in eternal flames. Born to burn, plays to destroy.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["tom_da_playa_hellfire"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_hellfire"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "$LAYA",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_tom_da_playa",
        "variant_name": "Hellfire"
    },
    {
        "id": "card_tom_da_playa_cosmic",
        "name": "Tom Da Playa (Cosmic)",
        "description": "The Cosmic variant of Tom Da Playa, cruising through galaxies. His grooves bend space and time.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["tom_da_playa_cosmic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_cosmic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "$LAYA",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_tom_da_playa",
        "variant_name": "Cosmic"
    },
    {
        "id": "card_chum_araya",
        "name": "Chum Araya",
        "description": "When Chum steps on stage, it smells Raining Blood. Watch yourself—he'll kick your face and eat all your pizza.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["chum_araya"],
        "back_image_url": CARD_BACK_IMAGE_URLS["chum_araya"],
        "coin_cost": 50,
        "available": True,
        "series": 1,
        "band": "$LAYA",
        "card_type": "B"
    },
    # Chum Araya Variants
    {
        "id": "card_chum_araya_toxic",
        "name": "Chum Araya (Toxic)",
        "description": "The Toxic variant of Chum Araya, oozing with radioactive fury. His bass lines are so contaminated they come with a hazmat warning.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["chum_araya_toxic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_toxic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "$LAYA",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_chum_araya",
        "variant_name": "Toxic"
    },
    {
        "id": "card_chum_araya_electric",
        "name": "Chum Araya (Electric)",
        "description": "The Electric variant of Chum Araya, crackling with high-voltage energy. Touch his bass and you'll be raining sparks.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["chum_araya_electric"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_electric"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "$LAYA",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_chum_araya",
        "variant_name": "Electric"
    },
    {
        "id": "card_chum_araya_hellfire",
        "name": "Chum Araya (Hellfire)",
        "description": "The Hellfire variant of Chum Araya, burning with demonic intensity. His bass solos summon flames from the underworld.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["chum_araya_hellfire"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_hellfire"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "$LAYA",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_chum_araya",
        "variant_name": "Hellfire"
    },
    {
        "id": "card_chum_araya_cosmic",
        "name": "Chum Araya (Cosmic)",
        "description": "The Cosmic variant of Chum Araya, transcending space and time. His grooves echo across galaxies.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["chum_araya_cosmic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_cosmic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "$LAYA",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_chum_araya",
        "variant_name": "Cosmic"
    },
    # Band 2: Megadef
    {
        "id": "card_musty_dave",
        "name": "Musty Dave",
        "description": "Musty Dave hasn't showered since the Cold War. He smells like rust, sweat, and bad ideas.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["musty_dave"],
        "back_image_url": CARD_BACK_IMAGE_URLS["musty_dave"],
        "coin_cost": 50,
        "available": True,
        "series": 1,
        "band": "Megadef",
        "card_type": "A"
    },
    {
        "id": "card_daves_mustang",
        "name": "Dave's Mustang",
        "description": "Dave's Mustang leaves a trail of tire smoke and broken eardrums. He drives like he solos: loud and a little out of control.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["daves_mustang"],
        "back_image_url": CARD_BACK_IMAGE_URLS["daves_mustang"],
        "coin_cost": 50,
        "available": True,
        "series": 1,
        "band": "Megadef",
        "card_type": "B"
    },
    # Dave's Mustang Variants
    {
        "id": "card_daves_mustang_toxic",
        "name": "Dave's Mustang (Toxic)",
        "description": "The Toxic variant of Dave's Mustang, dripping with radioactive slime. Nuclear waste and thrash metal don't mix well, but they sure look awesome.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["daves_mustang_toxic"],
        "back_image_url": CARD_IMAGE_URLS["daves_mustang_toxic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Megadef",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_daves_mustang",
        "variant_name": "Toxic"
    },
    {
        "id": "card_daves_mustang_electric",
        "name": "Dave's Mustang (Electric)",
        "description": "The Electric variant of Dave's Mustang, crackling with lightning energy. When Dave shreds, the sky literally splits open.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["daves_mustang_electric"],
        "back_image_url": CARD_IMAGE_URLS["daves_mustang_electric"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Megadef",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_daves_mustang",
        "variant_name": "Electric"
    },
    {
        "id": "card_daves_mustang_hellfire",
        "name": "Dave's Mustang (Hellfire)",
        "description": "The Hellfire variant of Dave's Mustang, engulfed in eternal flames. Straight from the depths of metal hell, this ride burns rubber and souls.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["daves_mustang_hellfire"],
        "back_image_url": CARD_IMAGE_URLS["daves_mustang_hellfire"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Megadef",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_daves_mustang",
        "variant_name": "Hellfire"
    },
    {
        "id": "card_daves_mustang_cosmic",
        "name": "Dave's Mustang (Cosmic)",
        "description": "The Cosmic variant of Dave's Mustang, cruising through galaxies. When the riffs are this heavy, even black holes can't escape.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["daves_mustang_cosmic"],
        "back_image_url": CARD_IMAGE_URLS["daves_mustang_cosmic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Megadef",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_daves_mustang",
        "variant_name": "Cosmic"
    },
    # Musty Dave Variants
    {
        "id": "card_musty_dave_toxic",
        "name": "Musty Dave (Toxic)",
        "description": "The Toxic variant of Musty Dave, oozing radioactive slime. His stench has evolved into a weaponized biohazard.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["musty_dave_toxic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_toxic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Megadef",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_musty_dave",
        "variant_name": "Toxic"
    },
    {
        "id": "card_musty_dave_electric",
        "name": "Musty Dave (Electric)",
        "description": "The Electric variant of Musty Dave, crackling with high voltage. His hair stands on end permanently from all the shocks.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["musty_dave_electric"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_electric"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Megadef",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_musty_dave",
        "variant_name": "Electric"
    },
    {
        "id": "card_musty_dave_hellfire",
        "name": "Musty Dave (Hellfire)",
        "description": "The Hellfire variant of Musty Dave, burning with demonic fury. His body odor has reached temperatures that melt steel.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["musty_dave_hellfire"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_hellfire"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Megadef",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_musty_dave",
        "variant_name": "Hellfire"
    },
    {
        "id": "card_musty_dave_cosmic",
        "name": "Musty Dave (Cosmic)",
        "description": "The Cosmic variant of Musty Dave, transcending reality. His funk has spread across galaxies, contaminating entire star systems.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["musty_dave_cosmic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_cosmic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Megadef",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_musty_dave",
        "variant_name": "Cosmic"
    },
    # Band 3: Sepulchura
    {
        "id": "card_maxi_pad",
        "name": "Maxi Pad",
        "description": "Maxi Pad is a walking snot rag, dripping sweat, slime, and blood. He uses his gross collection of filth for guitar solos that leave you queasy.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["maxi_pad"],
        "back_image_url": CARD_BACK_IMAGE_URLS["maxi_pad"],
        "coin_cost": 50,
        "available": True,
        "series": 1,
        "band": "Sepulchura",
        "card_type": "A"
    },
    {
        "id": "card_maximum",
        "name": "Maximum",
        "description": "Maximum is pissed off about everything – except the size of his ego. He's so angry that even his rage is loud enough to make your grandma cover her ears.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["maximum"],
        "back_image_url": CARD_BACK_IMAGE_URLS["maximum"],
        "coin_cost": 50,
        "available": True,
        "series": 1,
        "band": "Sepulchura",
        "card_type": "B"
    },
    # Maxi Pad Variants
    {
        "id": "card_maxi_pad_toxic",
        "name": "Maxi Pad (Toxic)",
        "description": "The Toxic variant of Maxi Pad, oozing radioactive goo. His sweat has mutated into something even more disgusting.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["maxi_pad_toxic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_toxic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Sepulchura",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_maxi_pad",
        "variant_name": "Toxic"
    },
    {
        "id": "card_maxi_pad_electric",
        "name": "Maxi Pad (Electric)",
        "description": "The Electric variant of Maxi Pad, crackling with shocking energy. His slime now conducts electricity.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["maxi_pad_electric"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_electric"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Sepulchura",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_maxi_pad",
        "variant_name": "Electric"
    },
    {
        "id": "card_maxi_pad_hellfire",
        "name": "Maxi Pad (Hellfire)",
        "description": "The Hellfire variant of Maxi Pad, engulfed in eternal flames. His gross collection has been incinerated but somehow smells worse.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["maxi_pad_hellfire"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_hellfire"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Sepulchura",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_maxi_pad",
        "variant_name": "Hellfire"
    },
    {
        "id": "card_maxi_pad_cosmic",
        "name": "Maxi Pad (Cosmic)",
        "description": "The Cosmic variant of Maxi Pad, spreading filth across the universe. Alien civilizations have quarantined entire galaxies.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["maxi_pad_cosmic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_cosmic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Sepulchura",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_maxi_pad",
        "variant_name": "Cosmic"
    },
    # Maximum Variants
    {
        "id": "card_maximum_toxic",
        "name": "Maximum (Toxic)",
        "description": "The Toxic variant of Maximum, his rage now radioactive. His fury contaminates everything within a 50-mile radius.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["maximum_toxic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_toxic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Sepulchura",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_maximum",
        "variant_name": "Toxic"
    },
    {
        "id": "card_maximum_electric",
        "name": "Maximum (Electric)",
        "description": "The Electric variant of Maximum, his anger now conducts lightning. His screams cause citywide blackouts.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["maximum_electric"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_electric"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Sepulchura",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_maximum",
        "variant_name": "Electric"
    },
    {
        "id": "card_maximum_hellfire",
        "name": "Maximum (Hellfire)",
        "description": "The Hellfire variant of Maximum, his ego now literally burns. Hell itself couldn't contain his fury.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["maximum_hellfire"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_hellfire"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Sepulchura",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_maximum",
        "variant_name": "Hellfire"
    },
    {
        "id": "card_maximum_cosmic",
        "name": "Maximum (Cosmic)",
        "description": "The Cosmic variant of Maximum, his rage echoes across the universe. Entire galaxies cower before his tantrums.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["maximum_cosmic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_cosmic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Sepulchura",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_maximum",
        "variant_name": "Cosmic"
    },
    # Band 4: Testyment
    {
        "id": "card_billy_chuck",
        "name": "Billy Chuck",
        "description": "Billy Chuck mumbles when he's sober, roars when he's hammered, and snorts when he's drunk.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["billy_chuck"],
        "back_image_url": CARD_BACK_IMAGE_URLS["billy_chuck"],
        "coin_cost": 50,
        "available": True,
        "series": 1,
        "band": "Testyment",
        "card_type": "A"
    },
    {
        "id": "card_chuck_roast",
        "name": "Chuck Roast",
        "description": "Chuck Roast eats mics for breakfast, burritos for lunch, and anything that looks remotely edible for dinner.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["chuck_roast"],
        "back_image_url": CARD_BACK_IMAGE_URLS["chuck_roast"],
        "coin_cost": 50,
        "available": True,
        "series": 1,
        "band": "Testyment",
        "card_type": "B"
    },
    # Billy Chuck Variants
    {
        "id": "card_billy_chuck_toxic",
        "name": "Billy Chuck (Toxic)",
        "description": "The Toxic variant of Billy Chuck, his moonshine now glows radioactive green. His pig mutated into something unspeakable.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["billy_chuck_toxic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_toxic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Testyment",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_billy_chuck",
        "variant_name": "Toxic"
    },
    {
        "id": "card_billy_chuck_electric",
        "name": "Billy Chuck (Electric)",
        "description": "The Electric variant of Billy Chuck, crackling with backwoods lightning. His overalls are charged with 10,000 volts of redneck energy.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["billy_chuck_electric"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_electric"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Testyment",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_billy_chuck",
        "variant_name": "Electric"
    },
    {
        "id": "card_billy_chuck_hellfire",
        "name": "Billy Chuck (Hellfire)",
        "description": "The Hellfire variant of Billy Chuck, straight from the devil's barnyard. His pitchfork is aflame and his moonshine burns eternal.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["billy_chuck_hellfire"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_hellfire"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Testyment",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_billy_chuck",
        "variant_name": "Hellfire"
    },
    {
        "id": "card_billy_chuck_cosmic",
        "name": "Billy Chuck (Cosmic)",
        "description": "The Cosmic variant of Billy Chuck, abducted by aliens and returned with interdimensional moonshine. His pig now floats.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["billy_chuck_cosmic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_cosmic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Testyment",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_billy_chuck",
        "variant_name": "Cosmic"
    },
    # Chuck Roast Variants
    {
        "id": "card_chuck_roast_toxic",
        "name": "Chuck Roast (Toxic)",
        "description": "The Toxic variant of Chuck Roast, marinated in radioactive juices. His meat has mutated into something unrecognizable.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["chuck_roast_toxic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_toxic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Testyment",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_chuck_roast",
        "variant_name": "Toxic"
    },
    {
        "id": "card_chuck_roast_electric",
        "name": "Chuck Roast (Electric)",
        "description": "The Electric variant of Chuck Roast, grilled by lightning. His drumsticks are charged with 50,000 volts.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["chuck_roast_electric"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_electric"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Testyment",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_chuck_roast",
        "variant_name": "Electric"
    },
    {
        "id": "card_chuck_roast_hellfire",
        "name": "Chuck Roast (Hellfire)",
        "description": "The Hellfire variant of Chuck Roast, slow-roasted in the flames of hell. Well done doesn't begin to describe it.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["chuck_roast_hellfire"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_hellfire"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Testyment",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_chuck_roast",
        "variant_name": "Hellfire"
    },
    {
        "id": "card_chuck_roast_cosmic",
        "name": "Chuck Roast (Cosmic)",
        "description": "The Cosmic variant of Chuck Roast, grilled on a dying star. His flavors transcend space and time.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["chuck_roast_cosmic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_cosmic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Testyment",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_chuck_roast",
        "variant_name": "Cosmic"
    },
    # Band 5: Metallikuh
    {
        "id": "card_cliff_diver",
        "name": "Cliff Diver",
        "description": "Cliff Diver dives headfirst off amps and lands on unlucky fans, puking out beer, pizza, and whiskey often as he goes. His stage dives are as epic as his hangovers.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["cliff_diver"],
        "back_image_url": CARD_BACK_IMAGE_URLS["cliff_diver"],
        "coin_cost": 50,
        "available": True,
        "series": 1,
        "band": "Metallikuh",
        "card_type": "A"
    },
    {
        "id": "card_cliff_burpin",
        "name": "Cliff Burpin",
        "description": "Cliff burps so hard it rattles the amps. Smells like beer, bass strings, and bad decisions.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["cliff_burpin"],
        "back_image_url": CARD_BACK_IMAGE_URLS["cliff_burpin"],
        "coin_cost": 50,
        "available": True,
        "series": 1,
        "band": "Metallikuh",
        "card_type": "B"
    },
    # Cliff Diver Variants
    {
        "id": "card_cliff_diver_toxic",
        "name": "Cliff Diver (Toxic)",
        "description": "The Toxic variant of Cliff Diver, his dive now leaves a radioactive splash. The ocean refuses to take him back.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["cliff_diver_toxic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_toxic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Metallikuh",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_cliff_diver",
        "variant_name": "Toxic"
    },
    {
        "id": "card_cliff_diver_electric",
        "name": "Cliff Diver (Electric)",
        "description": "The Electric variant of Cliff Diver, his body now crackles with lightning. Every dive creates a thunderstorm.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["cliff_diver_electric"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_electric"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Metallikuh",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_cliff_diver",
        "variant_name": "Electric"
    },
    {
        "id": "card_cliff_diver_hellfire",
        "name": "Cliff Diver (Hellfire)",
        "description": "The Hellfire variant of Cliff Diver, diving straight into the flames of hell. The water evaporates before he hits it.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["cliff_diver_hellfire"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_hellfire"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Metallikuh",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_cliff_diver",
        "variant_name": "Hellfire"
    },
    {
        "id": "card_cliff_diver_cosmic",
        "name": "Cliff Diver (Cosmic)",
        "description": "The Cosmic variant of Cliff Diver, diving through wormholes across the universe. He's not sure where he'll land.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["cliff_diver_cosmic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_cosmic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Metallikuh",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_cliff_diver",
        "variant_name": "Cosmic"
    },
    # Cliff Burpin Variants
    {
        "id": "card_cliff_burpin_toxic",
        "name": "Cliff Burpin (Toxic)",
        "description": "The Toxic variant of Cliff Burpin, his burps now release radioactive gases. One belch and the whole room evacuates.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["cliff_burpin_toxic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_toxic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Metallikuh",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_cliff_burpin",
        "variant_name": "Toxic"
    },
    {
        "id": "card_cliff_burpin_electric",
        "name": "Cliff Burpin (Electric)",
        "description": "The Electric variant of Cliff Burpin, his burps now spark with lightning. Stand too close and you'll get zapped.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["cliff_burpin_electric"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_electric"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Metallikuh",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_cliff_burpin",
        "variant_name": "Electric"
    },
    {
        "id": "card_cliff_burpin_hellfire",
        "name": "Cliff Burpin (Hellfire)",
        "description": "The Hellfire variant of Cliff Burpin, his burps erupt in demonic flames. Satan himself asks him to tone it down.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["cliff_burpin_hellfire"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_hellfire"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Metallikuh",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_cliff_burpin",
        "variant_name": "Hellfire"
    },
    {
        "id": "card_cliff_burpin_cosmic",
        "name": "Cliff Burpin (Cosmic)",
        "description": "The Cosmic variant of Cliff Burpin, his burps now ripple through spacetime. Astronomers track his digestive events.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["cliff_burpin_cosmic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_cosmic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Metallikuh",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_cliff_burpin",
        "variant_name": "Cosmic"
    },
    # Band 6: Anthrash
    {
        "id": "card_scotch_ian",
        "name": "Scotch Ian",
        "description": "Scotch Ian likes his whiskey, his kilt, and his guitar loud enough to strip the flesh right off yer ger bones. His solos are so strong they come with a hangover.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["scotch_ian"],
        "back_image_url": CARD_BACK_IMAGE_URLS["scotch_ian"],
        "coin_cost": 50,
        "available": True,
        "series": 1,
        "band": "Anthrash",
        "card_type": "A"
    },
    # Scotch Ian Variants
    {
        "id": "card_scotch_ian_toxic",
        "name": "Scotch Ian (Toxic)",
        "description": "The Toxic variant of Scotch Ian, his whiskey now glows radioactive green. One sip and you'll be belching nuclear fumes.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["scotch_ian_toxic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_toxic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Anthrash",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_scotch_ian",
        "variant_name": "Toxic"
    },
    {
        "id": "card_scotch_ian_electric",
        "name": "Scotch Ian (Electric)",
        "description": "The Electric variant of Scotch Ian, lightning crackles through his kilt. His solos now literally shock audiences.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["scotch_ian_electric"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_electric"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Anthrash",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_scotch_ian",
        "variant_name": "Electric"
    },
    {
        "id": "card_scotch_ian_hellfire",
        "name": "Scotch Ian (Hellfire)",
        "description": "The Hellfire variant of Scotch Ian, his whiskey burns with demonic flames. His breath could melt steel beams.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["scotch_ian_hellfire"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_hellfire"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Anthrash",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_scotch_ian",
        "variant_name": "Hellfire"
    },
    {
        "id": "card_scotch_ian_cosmic",
        "name": "Scotch Ian (Cosmic)",
        "description": "The Cosmic variant of Scotch Ian, his whiskey distilled from stardust. His hangovers span galaxies.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["scotch_ian_cosmic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_cosmic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Anthrash",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_scotch_ian",
        "variant_name": "Cosmic"
    },
    {
        "id": "card_scott_eaten",
        "name": "Scott Eaten",
        "description": "Scott Eaten uses his guitar to chomp anything in his way. Better lock up your food and your fingers when he's around.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["scott_eaten"],
        "back_image_url": CARD_BACK_IMAGE_URLS["scott_eaten"],
        "coin_cost": 50,
        "available": True,
        "series": 1,
        "band": "Anthrash",
        "card_type": "B"
    },
    # Scott Eaten Variants
    {
        "id": "card_scott_eaten_toxic",
        "name": "Scott Eaten (Toxic)",
        "description": "The Toxic variant of Scott Eaten, his appetite now extends to radioactive waste. One bite and he glows brighter than a nuclear meltdown.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["scott_eaten_toxic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_toxic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Anthrash",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_scott_eaten",
        "variant_name": "Toxic"
    },
    {
        "id": "card_scott_eaten_electric",
        "name": "Scott Eaten (Electric)",
        "description": "The Electric variant of Scott Eaten, lightning surges through his digestive system. Every bite creates a power surge.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["scott_eaten_electric"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_electric"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Anthrash",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_scott_eaten",
        "variant_name": "Electric"
    },
    {
        "id": "card_scott_eaten_hellfire",
        "name": "Scott Eaten (Hellfire)",
        "description": "The Hellfire variant of Scott Eaten, his stomach burns with demonic flames. He literally has fire in his belly.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["scott_eaten_hellfire"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_hellfire"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Anthrash",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_scott_eaten",
        "variant_name": "Hellfire"
    },
    {
        "id": "card_scott_eaten_cosmic",
        "name": "Scott Eaten (Cosmic)",
        "description": "The Cosmic variant of Scott Eaten, his appetite spans galaxies. He's eaten asteroids, comets, and a few unlucky space probes.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["scott_eaten_cosmic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_cosmic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Anthrash",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_scott_eaten",
        "variant_name": "Cosmic"
    },
    # Band 7: Kreaturd
    {
        "id": "card_silly_mille",
        "name": "Silly Mille",
        "description": "Kreaturd shreds noses as much as they shred riffs. Their shredding solos will turn your stomach and they're always ready to start a snotpocalypse.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["silly_mille"],
        "back_image_url": CARD_BACK_IMAGE_URLS["silly_mille"],
        "coin_cost": 50,
        "available": True,
        "series": 1,
        "band": "Kreaturd",
        "card_type": "A"
    },
    {
        "id": "card_mille_gorezza",
        "name": "Mille Gorezza",
        "description": "Mille Gorezza shreds bodies as much as he shreds guitar. His killer solos turn your stomach and he's always ready to start a moshpocalypse.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["mille_gorezza"],
        "back_image_url": CARD_BACK_IMAGE_URLS["mille_gorezza"],
        "coin_cost": 50,
        "available": True,
        "series": 1,
        "band": "Kreaturd",
        "card_type": "B"
    },
    # Silly Mille Variants
    {
        "id": "card_silly_mille_toxic",
        "name": "Silly Mille (Toxic)",
        "description": "The Toxic variant of Silly Mille, his boogers now glow radioactive green. Biohazard crews follow him on tour.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["silly_mille_toxic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_toxic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Kreaturd",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_silly_mille",
        "variant_name": "Toxic"
    },
    {
        "id": "card_silly_mille_electric",
        "name": "Silly Mille (Electric)",
        "description": "The Electric variant of Silly Mille, his snot now conducts lightning. Every sneeze causes a power surge.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["silly_mille_electric"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_electric"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Kreaturd",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_silly_mille",
        "variant_name": "Electric"
    },
    {
        "id": "card_silly_mille_hellfire",
        "name": "Silly Mille (Hellfire)",
        "description": "The Hellfire variant of Silly Mille, his mucus now burns with demonic fire. Hell's demons refuse to shake his hand.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["silly_mille_hellfire"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_hellfire"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Kreaturd",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_silly_mille",
        "variant_name": "Hellfire"
    },
    {
        "id": "card_silly_mille_cosmic",
        "name": "Silly Mille (Cosmic)",
        "description": "The Cosmic variant of Silly Mille, his snot transcends space and time. Alien civilizations have declared him a biohazard.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["silly_mille_cosmic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_cosmic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Kreaturd",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_silly_mille",
        "variant_name": "Cosmic"
    },
    # Mille Gorezza Variants
    {
        "id": "card_mille_gorezza_toxic",
        "name": "Mille Gorezza (Toxic)",
        "description": "The Toxic variant of Mille Gorezza, his pickled pizza now glows radioactive green. FDA has issued a permanent recall.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["mille_gorezza_toxic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_toxic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Kreaturd",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_mille_gorezza",
        "variant_name": "Toxic"
    },
    {
        "id": "card_mille_gorezza_electric",
        "name": "Mille Gorezza (Electric)",
        "description": "The Electric variant of Mille Gorezza, his pizza grease now conducts lightning. Every bite delivers 10,000 volts.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["mille_gorezza_electric"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_electric"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Kreaturd",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_mille_gorezza",
        "variant_name": "Electric"
    },
    {
        "id": "card_mille_gorezza_hellfire",
        "name": "Mille Gorezza (Hellfire)",
        "description": "The Hellfire variant of Mille Gorezza, his pizza burns with demonic flames. Satan himself asked for the recipe.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["mille_gorezza_hellfire"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_hellfire"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Kreaturd",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_mille_gorezza",
        "variant_name": "Hellfire"
    },
    {
        "id": "card_mille_gorezza_cosmic",
        "name": "Mille Gorezza (Cosmic)",
        "description": "The Cosmic variant of Mille Gorezza, his pizza toppings harvested from alien planets. The cheese bends spacetime.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["mille_gorezza_cosmic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_cosmic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Kreaturd",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_mille_gorezza",
        "variant_name": "Cosmic"
    },
    # Band 8: Eggsodus
    {
        "id": "card_paul_bawl_off",
        "name": "Paul Bawl Off",
        "description": "Paul Bawl Off cries like a spoiled toddler at the first sign of trouble. From tears to snot bubbles, he floods the stage until everyone looks like they just went for a swim.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["paul_bawl_off"],
        "back_image_url": CARD_BACK_IMAGE_URLS["paul_bawl_off"],
        "coin_cost": 50,
        "available": True,
        "series": 1,
        "band": "Eggsodus",
        "card_type": "A"
    },
    # Paul Bawl Off Variants
    {
        "id": "card_paul_bawl_off_toxic",
        "name": "Paul Bawl Off (Toxic)",
        "description": "The Toxic variant of Paul Bawl Off, his tears are now radioactive acid. One crying session creates a hazmat situation.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["paul_bawl_off_toxic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_toxic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Eggsodus",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_paul_bawl_off",
        "variant_name": "Toxic"
    },
    {
        "id": "card_paul_bawl_off_electric",
        "name": "Paul Bawl Off (Electric)",
        "description": "The Electric variant of Paul Bawl Off, his tears conduct pure electricity. Every sob sends sparks flying through the venue.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["paul_bawl_off_electric"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_electric"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Eggsodus",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_paul_bawl_off",
        "variant_name": "Electric"
    },
    {
        "id": "card_paul_bawl_off_hellfire",
        "name": "Paul Bawl Off (Hellfire)",
        "description": "The Hellfire variant of Paul Bawl Off, his tears burn with demonic flames. Each teardrop is a tiny fireball from the depths of Hell.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["paul_bawl_off_hellfire"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_hellfire"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Eggsodus",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_paul_bawl_off",
        "variant_name": "Hellfire"
    },
    {
        "id": "card_paul_bawl_off_cosmic",
        "name": "Paul Bawl Off (Cosmic)",
        "description": "The Cosmic variant of Paul Bawl Off, his tears contain entire galaxies. When he cries, nebulas form in the puddles.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["paul_bawl_off_cosmic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_cosmic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Eggsodus",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_paul_bawl_off",
        "variant_name": "Cosmic"
    },
    {
        "id": "card_blood_bonder",
        "name": "Blood Bonder",
        "description": "With all the blood he spews, you'll swear Blood Bonder has thrash flowing through his veins. He showers the crowd with plasma and laughs as he bathes in the gore.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["blood_bonder"],
        "back_image_url": CARD_BACK_IMAGE_URLS["blood_bonder"],
        "coin_cost": 50,
        "available": True,
        "series": 1,
        "band": "Eggsodus",
        "card_type": "B"
    },
    # Blood Bonder Variants
    {
        "id": "card_blood_bonder_toxic",
        "name": "Blood Bonder (Toxic)",
        "description": "The Toxic variant of Blood Bonder, his blood has mutated into radioactive sludge. Every drop burns through the stage floor.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["blood_bonder_toxic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_toxic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Eggsodus",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_blood_bonder",
        "variant_name": "Toxic"
    },
    {
        "id": "card_blood_bonder_electric",
        "name": "Blood Bonder (Electric)",
        "description": "The Electric variant of Blood Bonder, his blood conducts lightning. Every vein pulses with deadly voltage.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["blood_bonder_electric"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_electric"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Eggsodus",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_blood_bonder",
        "variant_name": "Electric"
    },
    {
        "id": "card_blood_bonder_hellfire",
        "name": "Blood Bonder (Hellfire)",
        "description": "The Hellfire variant of Blood Bonder, his blood burns with demonic flames. Each splatter ignites the mosh pit.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["blood_bonder_hellfire"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_hellfire"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Eggsodus",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_blood_bonder",
        "variant_name": "Hellfire"
    },
    {
        "id": "card_blood_bonder_cosmic",
        "name": "Blood Bonder (Cosmic)",
        "description": "The Cosmic variant of Blood Bonder, his blood contains stardust and nebulae. His veins flow with the power of supernovas.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["blood_bonder_cosmic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_cosmic"],
        "coin_cost": 0,
        "available": False,
        "series": 1,
        "band": "Eggsodus",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_blood_bonder",
        "variant_name": "Cosmic"
    },
    # =====================
    # SERIES 2 - 8 bands, 16 cards (A & B for each band)
    # =====================
    # Band 1: Construction
    {
        "id": "card_smeared_schmier",
        "name": "Smeared Schmier",
        "description": "Schmier sweats buckets of vulgar vomit, and muds his pants twice a day. This germ-ridden dirtbag is always smeared in slime and filth as a result of his rank stage dives.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["smeared_schmier"],
        "back_image_url": CARD_BACK_IMAGE_URLS["smeared_schmier"],
        "coin_cost": 50,
        "available": True,
        "series": 2,
        "band": "Construction",
        "card_type": "A"
    },
    # Smeared Schmier Variants
    {
        "id": "card_smeared_schmier_bloodbath",
        "name": "Smeared Schmier (Bloodbath)",
        "description": "The Bloodbath variant of Smeared Schmier. His smears are now pure crimson gore. Every stage dive leaves a trail of bloody devastation.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["smeared_schmier_bloodbath"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_bloodbath"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Construction",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_smeared_schmier",
        "variant_name": "Bloodbath"
    },
    {
        "id": "card_smeared_schmier_ice",
        "name": "Smeared Schmier (Ice)",
        "description": "The Ice variant of Smeared Schmier. His filth has frozen solid. Every dive shatters the frozen slime into icicles of pure disgust.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["smeared_schmier_ice"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_ice"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Construction",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_smeared_schmier",
        "variant_name": "Ice"
    },
    {
        "id": "card_smeared_schmier_psychedelic",
        "name": "Smeared Schmier (Psychedelic)",
        "description": "The Psychedelic variant of Smeared Schmier. His slime now glows with rainbow colors. Every smear is a kaleidoscopic nightmare.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["smeared_schmier_psychedelic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_psychedelic"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Construction",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_smeared_schmier",
        "variant_name": "Psychedelic"
    },
    {
        "id": "card_smeared_schmier_biomechanical",
        "name": "Smeared Schmier (Biomechanical)",
        "description": "The Biomechanical variant of Smeared Schmier. His cybernetic body now oozes machine oil and hydraulic fluid. Industrial-grade filth.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["smeared_schmier_biomechanical"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_biomechanical"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Construction",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_smeared_schmier",
        "variant_name": "Biomechanical"
    },
    {
        "id": "card_beer_schmier",
        "name": "Beer Schmier",
        "description": "After a dozen steins, Schmier spews foamy bile and drools thrash as he froths at the mouth. Just be prepared for a drunken shower when he drops from a beer-fueled bender into the front row.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["beer_schmier"],
        "back_image_url": CARD_BACK_IMAGE_URLS["beer_schmier"],
        "coin_cost": 50,
        "available": True,
        "series": 2,
        "band": "Construction",
        "card_type": "B"
    },
    # Beer Schmier Variants
    {
        "id": "card_beer_schmier_bloodbath",
        "name": "Beer Schmier (Bloodbath)",
        "description": "The Bloodbath variant of Beer Schmier. His beer is now blood-red and his vomit is pure crimson. The mosh pit runs red with his drunken carnage.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["beer_schmier_bloodbath"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_bloodbath"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Construction",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_beer_schmier",
        "variant_name": "Bloodbath"
    },
    {
        "id": "card_beer_schmier_ice",
        "name": "Beer Schmier (Ice)",
        "description": "The Ice variant of Beer Schmier. His beer has frozen solid but he still chugs it. Brain freeze is his permanent state of existence.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["beer_schmier_ice"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_ice"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Construction",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_beer_schmier",
        "variant_name": "Ice"
    },
    {
        "id": "card_beer_schmier_psychedelic",
        "name": "Beer Schmier (Psychedelic)",
        "description": "The Psychedelic variant of Beer Schmier. His beer is laced with something cosmic. Every sip takes him to rainbow dimensions of pure thrash.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["beer_schmier_psychedelic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_psychedelic"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Construction",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_beer_schmier",
        "variant_name": "Psychedelic"
    },
    {
        "id": "card_beer_schmier_biomechanical",
        "name": "Beer Schmier (Biomechanical)",
        "description": "The Biomechanical variant of Beer Schmier. His cybernetic liver processes beer at industrial speeds. The machine that never stops drinking.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["beer_schmier_biomechanical"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_biomechanical"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Construction",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_beer_schmier",
        "variant_name": "Biomechanical"
    },
    # Band 2: Voivodka
    {
        "id": "card_piggy_in_a_blanket",
        "name": "Piggy in a Blanket",
        "description": "Piggy never bathes and sweats pure Canadian bacon grease from his pores. His pits smell of hardboiled rot, and his diet is nothing but moldy bahn mi.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["piggy_in_a_blanket"],
        "back_image_url": CARD_BACK_IMAGE_URLS["piggy_in_a_blanket"],
        "coin_cost": 50,
        "available": True,
        "series": 2,
        "band": "Voivodka",
        "card_type": "A"
    },
    # Piggy in a Blanket Variants
    {
        "id": "card_piggy_in_a_blanket_bloodbath",
        "name": "Piggy in a Blanket (Bloodbath)",
        "description": "The Bloodbath variant of Piggy. His blanket is now soaked in crimson gore, and his screams echo through blood-drenched halls of horror.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["piggy_in_a_blanket_bloodbath"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_bloodbath"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Voivodka",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_piggy_in_a_blanket",
        "variant_name": "Bloodbath"
    },
    {
        "id": "card_piggy_in_a_blanket_ice",
        "name": "Piggy in a Blanket (Ice)",
        "description": "The Ice variant of Piggy. Frozen solid in his blanket, his screams now shatter like icicles in the frozen tundra.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["piggy_in_a_blanket_ice"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_ice"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Voivodka",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_piggy_in_a_blanket",
        "variant_name": "Ice"
    },
    {
        "id": "card_piggy_in_a_blanket_psychedelic",
        "name": "Piggy in a Blanket (Psychedelic)",
        "description": "The Psychedelic variant of Piggy. His blanket swirls with mind-bending colors, his screams are now trippy soundwaves from another dimension.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["piggy_in_a_blanket_psychedelic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_psychedelic"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Voivodka",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_piggy_in_a_blanket",
        "variant_name": "Psychedelic"
    },
    {
        "id": "card_piggy_in_a_blanket_biomechanical",
        "name": "Piggy in a Blanket (Biomechanical)",
        "description": "The Biomechanical variant of Piggy. His blanket is now cybernetic coils and cables, merging flesh with machine in unholy fusion.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["piggy_in_a_blanket_biomechanical"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_biomechanical"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Voivodka",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_piggy_in_a_blanket",
        "variant_name": "Biomechanical"
    },
    {
        "id": "card_rotting_away",
        "name": "Rotting Away",
        "description": "Away is the deadbeat drummer who sweats pure filth and decays as he plays the beats. The flies have to cover their ears during his maggot ridden solos.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["rotting_away"],
        "back_image_url": CARD_BACK_IMAGE_URLS["rotting_away"],
        "coin_cost": 50,
        "available": True,
        "series": 2,
        "band": "Voivodka",
        "card_type": "B"
    },
    # Rotting Away Variants
    {
        "id": "card_rotting_away_bloodbath",
        "name": "Rotting Away (Bloodbath)",
        "description": "The Bloodbath variant of Rotting Away. His decay now oozes crimson gore, and every drum beat splatters the crowd with blood.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["rotting_away_bloodbath"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_bloodbath"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Voivodka",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_rotting_away",
        "variant_name": "Bloodbath"
    },
    {
        "id": "card_rotting_away_ice",
        "name": "Rotting Away (Ice)",
        "description": "The Ice variant of Rotting Away. Frozen mid-decay, his maggots are now icicles and his screams echo through glacial halls.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["rotting_away_ice"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_ice"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Voivodka",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_rotting_away",
        "variant_name": "Ice"
    },
    {
        "id": "card_rotting_away_psychedelic",
        "name": "Rotting Away (Psychedelic)",
        "description": "The Psychedelic variant of Rotting Away. His rot now pulses with rainbow colors, his decay is a kaleidoscopic nightmare.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["rotting_away_psychedelic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_psychedelic"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Voivodka",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_rotting_away",
        "variant_name": "Psychedelic"
    },
    {
        "id": "card_rotting_away_biomechanical",
        "name": "Rotting Away (Biomechanical)",
        "description": "The Biomechanical variant of Rotting Away. Half-zombie, half-machine, his cybernetic implants fight against his endless decay.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["rotting_away_biomechanical"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_biomechanical"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Voivodka",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_rotting_away",
        "variant_name": "Biomechanical"
    },
    # Band 3: Hallows Heave
    {
        "id": "card_tommy_stewart",
        "name": "Tommy SteWART",
        "description": "Tommy's body is 90% skin, 10% wart, and 100% screaming. Every riff grows a new growth. Dermatologists fear him.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["tommy_stewart"],
        "back_image_url": CARD_BACK_IMAGE_URLS["tommy_stewart"],
        "coin_cost": 50,
        "available": True,
        "series": 2,
        "band": "Hallows Heave",
        "card_type": "A"
    },
    # Tommy Stewart Variants
    {
        "id": "card_tommy_stewart_bloodbath",
        "name": "Tommy SteWART (Bloodbath)",
        "description": "The Bloodbath variant of Tommy SteWART. His warts now bleed eternally, covering everything in a cascade of crimson horror.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["tommy_stewart_bloodbath"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_bloodbath"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Hallows Heave",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_tommy_stewart",
        "variant_name": "Bloodbath"
    },
    {
        "id": "card_tommy_stewart_ice",
        "name": "Tommy SteWART (Ice)",
        "description": "The Ice variant of Tommy SteWART. His frozen warts glisten like deadly icicles. Every scream shatters the cold.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["tommy_stewart_ice"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_ice"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Hallows Heave",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_tommy_stewart",
        "variant_name": "Ice"
    },
    {
        "id": "card_tommy_stewart_psychedelic",
        "name": "Tommy SteWART (Psychedelic)",
        "description": "The Psychedelic variant of Tommy SteWART. His rainbow warts pulse with cosmic energy. Every growth is a trip.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["tommy_stewart_psychedelic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_psychedelic"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Hallows Heave",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_tommy_stewart",
        "variant_name": "Psychedelic"
    },
    {
        "id": "card_tommy_stewart_biomechanical",
        "name": "Tommy SteWART (Biomechanical)",
        "description": "The Biomechanical variant of Tommy SteWART. His cybernetic warts are weapons of mass destruction. Machine meets disease.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["tommy_stewart_biomechanical"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_biomechanical"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Hallows Heave",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_tommy_stewart",
        "variant_name": "Biomechanical"
    },
    {
        "id": "card_tommy_spewart",
        "name": "Tommy SPEWart",
        "description": "Tommy's body is 90% skin, 10% wart, and 100% screaming. Every riff grows a new growth. Dermatologists fear him.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["tommy_spewart"],
        "back_image_url": CARD_BACK_IMAGE_URLS["tommy_spewart"],
        "coin_cost": 50,
        "available": True,
        "series": 2,
        "band": "Hallows Heave",
        "card_type": "B"
    },
    # Tommy Spewart Variants
    {
        "id": "card_tommy_spewart_bloodbath",
        "name": "Tommy SPEWart (Bloodbath)",
        "description": "The Bloodbath variant of Tommy SPEWart. His warts now bleed eternally. Every scream erupts in crimson glory.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["tommy_spewart_bloodbath"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_bloodbath"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Hallows Heave",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_tommy_spewart",
        "variant_name": "Bloodbath"
    },
    {
        "id": "card_tommy_spewart_ice",
        "name": "Tommy SPEWart (Ice)",
        "description": "The Ice variant of Tommy SPEWart. His warts are frozen solid but still growing. Frostbitten horror incarnate.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["tommy_spewart_ice"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_ice"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Hallows Heave",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_tommy_spewart",
        "variant_name": "Ice"
    },
    {
        "id": "card_tommy_spewart_psychedelic",
        "name": "Tommy SPEWart (Psychedelic)",
        "description": "The Psychedelic variant of Tommy SPEWart. His rainbow warts pulse with cosmic energy. Each growth is a window to another dimension.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["tommy_spewart_psychedelic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_psychedelic"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Hallows Heave",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_tommy_spewart",
        "variant_name": "Psychedelic"
    },
    {
        "id": "card_tommy_spewart_biomechanical",
        "name": "Tommy SPEWart (Biomechanical)",
        "description": "The Biomechanical variant of Tommy SPEWart. His warts are now cybernetic implants that keep multiplying. Even technology can't stop the growth.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["tommy_spewart_biomechanical"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_biomechanical"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Hallows Heave",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_tommy_spewart",
        "variant_name": "Biomechanical"
    },
    # Band 4: Pussessed
    {
        "id": "card_jeff_possess_ya_s2",
        "name": "Jeff Possess Ya",
        "description": "Jeff Becerra's brand of possessione is a full-body experience. Your head grows horns and your soul is doomed.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["jeff_possess_ya_s2"],
        "back_image_url": CARD_BACK_IMAGE_URLS["jeff_possess_ya_s2"],
        "coin_cost": 50,
        "available": True,
        "series": 2,
        "band": "Pussessed",
        "card_type": "A"
    },
    # Jeff Possess Ya Variants
    {
        "id": "card_jeff_possess_ya_s2_bloodbath",
        "name": "Jeff Possess Ya (Bloodbath)",
        "description": "The Bloodbath variant of Jeff Possess Ya. His possession ritual now involves bathing in fresh blood. The demon within demands crimson sacrifice.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["jeff_possess_ya_s2_bloodbath"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_bloodbath"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Pussessed",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_jeff_possess_ya_s2",
        "variant_name": "Bloodbath"
    },
    {
        "id": "card_jeff_possess_ya_s2_ice",
        "name": "Jeff Possess Ya (Ice)",
        "description": "The Ice variant of Jeff Possess Ya. Frozen in eternal possession, his icy demon has turned his victims to frost statues.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["jeff_possess_ya_s2_ice"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_ice"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Pussessed",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_jeff_possess_ya_s2",
        "variant_name": "Ice"
    },
    {
        "id": "card_jeff_possess_ya_s2_psychedelic",
        "name": "Jeff Possess Ya (Psychedelic)",
        "description": "The Psychedelic variant of Jeff Possess Ya. His possession trips through rainbow dimensions. The demon within is high on cosmic energy.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["jeff_possess_ya_s2_psychedelic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_psychedelic"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Pussessed",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_jeff_possess_ya_s2",
        "variant_name": "Psychedelic"
    },
    {
        "id": "card_jeff_possess_ya_s2_biomechanical",
        "name": "Jeff Possess Ya (Biomechanical)",
        "description": "The Biomechanical variant of Jeff Possess Ya. Half-man, half-machine, his cybernetic possession spreads like a digital virus.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["jeff_possess_ya_s2_biomechanical"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_biomechanical"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Pussessed",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_jeff_possess_ya_s2",
        "variant_name": "Biomechanical"
    },
    {
        "id": "card_chef_becerra",
        "name": "Chef Becerra",
        "description": "For his gourmet zombies, Chef Becerra puts the flesh in flesh-eating. This soup of the day is shredded limb-sine meat.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["chef_becerra"],
        "back_image_url": CARD_BACK_IMAGE_URLS["chef_becerra"],
        "coin_cost": 50,
        "available": True,
        "series": 2,
        "band": "Pussessed",
        "card_type": "B"
    },
    # Chef Becerra Variants
    {
        "id": "card_chef_becerra_bloodbath",
        "name": "Chef Becerra (Bloodbath)",
        "description": "The Bloodbath variant of Chef Becerra. His kitchen is now a slaughterhouse. Every dish comes with a side of fresh carnage.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["chef_becerra_bloodbath"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_bloodbath"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Pussessed",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_chef_becerra",
        "variant_name": "Bloodbath"
    },
    {
        "id": "card_chef_becerra_ice",
        "name": "Chef Becerra (Ice)",
        "description": "The Ice variant of Chef Becerra. His frozen cuisine keeps the meat fresh forever. Served ice cold, literally.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["chef_becerra_ice"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_ice"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Pussessed",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_chef_becerra",
        "variant_name": "Ice"
    },
    {
        "id": "card_chef_becerra_psychedelic",
        "name": "Chef Becerra (Psychedelic)",
        "description": "The Psychedelic variant of Chef Becerra. His rainbow soup takes you on a culinary trip to other dimensions.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["chef_becerra_psychedelic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_psychedelic"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Pussessed",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_chef_becerra",
        "variant_name": "Psychedelic"
    },
    {
        "id": "card_chef_becerra_biomechanical",
        "name": "Chef Becerra (Biomechanical)",
        "description": "The Biomechanical variant of Chef Becerra. His cybernetic arms chop and dice with machine precision. Industrial-strength cooking.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["chef_becerra_biomechanical"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_biomechanical"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Pussessed",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_chef_becerra",
        "variant_name": "Biomechanical"
    },
    # Band 5: S.T.D.
    {
        "id": "card_bully_milano",
        "name": "Bully Milano",
        "description": "Infecting others is Bully's idea of a good time—and he's got the drippy, crusty, itchy, paining symptoms to prove it. Be careful who you casual contact!",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["bully_milano"],
        "back_image_url": CARD_BACK_IMAGE_URLS["bully_milano"],
        "coin_cost": 50,
        "available": True,
        "series": 2,
        "band": "S.T.D.",
        "card_type": "A"
    },
    # Bully Milano Variants
    {
        "id": "card_bully_milano_bloodbath",
        "name": "Bully Milano (Bloodbath)",
        "description": "The Bloodbath variant of Bully Milano. His infections now come with a side of blood splatter. The mosh pit has never been more dangerous.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["bully_milano_bloodbath"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_bloodbath"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "S.T.D.",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_bully_milano",
        "variant_name": "Bloodbath"
    },
    {
        "id": "card_bully_milano_ice",
        "name": "Bully Milano (Ice)",
        "description": "The Ice variant of Bully Milano. Frozen solid with his cigar still lit. His infections now spread through ice crystals.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["bully_milano_ice"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_ice"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "S.T.D.",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_bully_milano",
        "variant_name": "Ice"
    },
    {
        "id": "card_bully_milano_psychedelic",
        "name": "Bully Milano (Psychedelic)",
        "description": "The Psychedelic variant of Bully Milano. His diseases now cause rainbow hallucinations. The trip of a lifetime... literally.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["bully_milano_psychedelic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_psychedelic"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "S.T.D.",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_bully_milano",
        "variant_name": "Psychedelic"
    },
    {
        "id": "card_bully_milano_biomechanical",
        "name": "Bully Milano (Biomechanical)",
        "description": "The Biomechanical variant of Bully Milano. His cybernetic implants spread digital viruses. Infection has gone high-tech.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["bully_milano_biomechanical"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_biomechanical"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "S.T.D.",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_bully_milano",
        "variant_name": "Biomechanical"
    },
    {
        "id": "card_billy_mylanta",
        "name": "Billy Mylanta",
        "description": "Back from the hospital and back on the throne. The only thing more explosive than Billy's on-stage aggression is his unpredictable digestive position!",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["billy_mylanta"],
        "back_image_url": CARD_BACK_IMAGE_URLS["billy_mylanta"],
        "coin_cost": 50,
        "available": True,
        "series": 2,
        "band": "S.T.D.",
        "card_type": "B"
    },
    # Billy Mylanta Variants
    {
        "id": "card_billy_mylanta_bloodbath",
        "name": "Billy Mylanta (Bloodbath)",
        "description": "The Bloodbath variant of Billy Mylanta. His bathroom breaks now involve crimson eruptions. The toilet has become a portal to hell.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["billy_mylanta_bloodbath"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_bloodbath"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "S.T.D.",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_billy_mylanta",
        "variant_name": "Bloodbath"
    },
    {
        "id": "card_billy_mylanta_ice",
        "name": "Billy Mylanta (Ice)",
        "description": "The Ice variant of Billy Mylanta. Frozen to the frozen toilet in a frozen bathroom. His gas attacks now create ice crystals.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["billy_mylanta_ice"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_ice"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "S.T.D.",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_billy_mylanta",
        "variant_name": "Ice"
    },
    {
        "id": "card_billy_mylanta_psychedelic",
        "name": "Billy Mylanta (Psychedelic)",
        "description": "The Psychedelic variant of Billy Mylanta. His bathroom trips are now interdimensional experiences. The tiles pulse with colors unknown to science.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["billy_mylanta_psychedelic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_psychedelic"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "S.T.D.",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_billy_mylanta",
        "variant_name": "Psychedelic"
    },
    {
        "id": "card_billy_mylanta_biomechanical",
        "name": "Billy Mylanta (Biomechanical)",
        "description": "The Biomechanical variant of Billy Mylanta. His cybernetic digestive system has turned the bathroom into a factory. Industrial-strength gas attacks.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["billy_mylanta_biomechanical"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_biomechanical"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "S.T.D.",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_billy_mylanta",
        "variant_name": "Biomechanical"
    },
    # Band 6: Sodumb
    {
        "id": "card_tom_angeltipper",
        "name": "Tom Angeltipper",
        "description": "Once a month, Tom Angeltipper drinks ten shots of Schnapps and tosses ten angels off clouds. Why do angels fall? Because they're easily led!...OFF LEDGES!",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["tom_angeltipper"],
        "back_image_url": CARD_BACK_IMAGE_URLS["tom_angeltipper"],
        "coin_cost": 50,
        "available": True,
        "series": 2,
        "band": "Sodumb",
        "card_type": "A"
    },
    # Tom Angeltipper Variants
    {
        "id": "card_tom_angeltipper_bloodbath",
        "name": "Tom Angeltipper (Bloodbath)",
        "description": "The Bloodbath variant of Tom Angeltipper. The angels aren't just falling now - they're bleeding. His Schnapps is 100 proof crimson.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["tom_angeltipper_bloodbath"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_bloodbath"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Sodumb",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_tom_angeltipper",
        "variant_name": "Bloodbath"
    },
    {
        "id": "card_tom_angeltipper_ice",
        "name": "Tom Angeltipper (Ice)",
        "description": "The Ice variant of Tom Angeltipper. He's tossing frozen angels into snowbanks. His Schnapps has turned to ice water.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["tom_angeltipper_ice"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_ice"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Sodumb",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_tom_angeltipper",
        "variant_name": "Ice"
    },
    {
        "id": "card_tom_angeltipper_psychedelic",
        "name": "Tom Angeltipper (Psychedelic)",
        "description": "The Psychedelic variant of Tom Angeltipper. The angels he tips are now neon-colored hallucinations. His Schnapps is laced with something otherworldly.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["tom_angeltipper_psychedelic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_psychedelic"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Sodumb",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_tom_angeltipper",
        "variant_name": "Psychedelic"
    },
    {
        "id": "card_tom_angeltipper_biomechanical",
        "name": "Tom Angeltipper (Biomechanical)",
        "description": "The Biomechanical variant of Tom Angeltipper. His cyborg arm tips mechanical angels. Even machines fear his monthly Schnapps ritual.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["tom_angeltipper_biomechanical"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_biomechanical"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Sodumb",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_tom_angeltipper",
        "variant_name": "Biomechanical"
    },
    {
        "id": "card_tom_angelflipper",
        "name": "Tom Angelflipper",
        "description": "Once a month, Tom Angel Flipper drinks ten shots of Schnapps and tosses ten angels off clouds. He's the reason angels had to sign a health waiver.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["tom_angelflipper"],
        "back_image_url": CARD_BACK_IMAGE_URLS["tom_angelflipper"],
        "coin_cost": 50,
        "available": True,
        "series": 2,
        "band": "Sodumb",
        "card_type": "B"
    },
    # Tom Angelflipper Variants
    {
        "id": "card_tom_angelflipper_bloodbath",
        "name": "Tom Angelflipper (Bloodbath)",
        "description": "The Bloodbath variant of Tom Angelflipper. His health waivers are now written in blood. The angels don't just fall - they splatter.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["tom_angelflipper_bloodbath"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_bloodbath"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Sodumb",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_tom_angelflipper",
        "variant_name": "Bloodbath"
    },
    {
        "id": "card_tom_angelflipper_ice",
        "name": "Tom Angelflipper (Ice)",
        "description": "The Ice variant of Tom Angelflipper. His frozen Schnapps turns angels into ice sculptures before they even hit the ground.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["tom_angelflipper_ice"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_ice"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Sodumb",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_tom_angelflipper",
        "variant_name": "Ice"
    },
    {
        "id": "card_tom_angelflipper_psychedelic",
        "name": "Tom Angelflipper (Psychedelic)",
        "description": "The Psychedelic variant of Tom Angelflipper. His angels trail rainbow contrails and his Schnapps glows with cosmic energy.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["tom_angelflipper_psychedelic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_psychedelic"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Sodumb",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_tom_angelflipper",
        "variant_name": "Psychedelic"
    },
    {
        "id": "card_tom_angelflipper_biomechanical",
        "name": "Tom Angelflipper (Biomechanical)",
        "description": "The Biomechanical variant of Tom Angelflipper. Half-man, half-machine, his cybernetic arm calculates the perfect angle for flipping robo-angels.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["tom_angelflipper_biomechanical"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_biomechanical"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Sodumb",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_tom_angelflipper",
        "variant_name": "Biomechanical"
    },
    # Band 7: Sacrud Ryche
    {
        "id": "card_philled_up",
        "name": "Philled Up",
        "description": "Phil never met a cheese pizza he didn't love, or finish. If a dinner is all-you-can-eat, he treats it like an Olympic sport.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["philled_up"],
        "back_image_url": CARD_BACK_IMAGE_URLS["philled_up"],
        "coin_cost": 50,
        "available": True,
        "series": 2,
        "band": "Sacrud Ryche",
        "card_type": "A"
    },
    # Philled Up Variants
    {
        "id": "card_philled_up_bloodbath",
        "name": "Philled Up (Bloodbath)",
        "description": "The Bloodbath variant of Philled Up. His all-you-can-eat buffet now serves gore galore. The ketchup isn't ketchup anymore.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["philled_up_bloodbath"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_bloodbath"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Sacrud Ryche",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_philled_up",
        "variant_name": "Bloodbath"
    },
    {
        "id": "card_philled_up_ice",
        "name": "Philled Up (Ice)",
        "description": "The Ice variant of Philled Up. He feasts on frozen treats in sub-zero temperatures. Brain freeze is his permanent state.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["philled_up_ice"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_ice"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Sacrud Ryche",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_philled_up",
        "variant_name": "Ice"
    },
    {
        "id": "card_philled_up_psychedelic",
        "name": "Philled Up (Psychedelic)",
        "description": "The Psychedelic variant of Philled Up. His food now glows in rainbow colors. Every bite is a trip to flavor dimensions unknown.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["philled_up_psychedelic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_psychedelic"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Sacrud Ryche",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_philled_up",
        "variant_name": "Psychedelic"
    },
    {
        "id": "card_philled_up_biomechanical",
        "name": "Philled Up (Biomechanical)",
        "description": "The Biomechanical variant of Philled Up. His cybernetic stomach has infinite capacity. He's the eating machine they always said he was.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["philled_up_biomechanical"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_biomechanical"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Sacrud Ryche",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_philled_up",
        "variant_name": "Biomechanical"
    },
    {
        "id": "card_phil_grind",
        "name": "Phil Grind",
        "description": "Phil is the mucky vokillist of Sacrud Ryche who clings to filth and grime like it was his first fan. He coughs up enough phlegm to check bags.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["phil_grind"],
        "back_image_url": CARD_BACK_IMAGE_URLS["phil_grind"],
        "coin_cost": 50,
        "available": True,
        "series": 2,
        "band": "Sacrud Ryche",
        "card_type": "B"
    },
    # Phil Grind Variants
    {
        "id": "card_phil_grind_bloodbath",
        "name": "Phil Grind (Bloodbath)",
        "description": "The Bloodbath variant of Phil Grind. His meat grinder now oozes crimson gore. The output? Pure bloody terror on a plate.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["phil_grind_bloodbath"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_bloodbath"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Sacrud Ryche",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_phil_grind",
        "variant_name": "Bloodbath"
    },
    {
        "id": "card_phil_grind_ice",
        "name": "Phil Grind (Ice)",
        "description": "The Ice variant of Phil Grind. His frozen meat grinder produces frost-bitten chunks. Even the skulls shiver in his arctic presence.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["phil_grind_ice"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_ice"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Sacrud Ryche",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_phil_grind",
        "variant_name": "Ice"
    },
    {
        "id": "card_phil_grind_psychedelic",
        "name": "Phil Grind (Psychedelic)",
        "description": "The Psychedelic variant of Phil Grind. His grinder produces rainbow-colored mystery meat. One bite sends you on a trip you'll never forget.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["phil_grind_psychedelic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_psychedelic"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Sacrud Ryche",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_phil_grind",
        "variant_name": "Psychedelic"
    },
    {
        "id": "card_phil_grind_biomechanical",
        "name": "Phil Grind (Biomechanical)",
        "description": "The Biomechanical variant of Phil Grind. Half-man, half-machine, his cybernetic grinder processes flesh and metal alike with terrifying efficiency.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["phil_grind_biomechanical"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_biomechanical"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Sacrud Ryche",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_phil_grind",
        "variant_name": "Biomechanical"
    },
    # Band 8: Dork Angel
    {
        "id": "card_don_doody",
        "name": "Don Doody",
        "description": "Don Doody brings an unflushable load of nerd stink. Rarely wipe their instruments clean. If the set goes over 20 minutes, consider letting the janitor open for them!",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["don_doody"],
        "back_image_url": CARD_BACK_IMAGE_URLS["don_doody"],
        "coin_cost": 50,
        "available": True,
        "series": 2,
        "band": "Dork Angel",
        "card_type": "A"
    },
    # Don Doody Variants
    {
        "id": "card_don_doody_bloodbath",
        "name": "Don Doody (Bloodbath)",
        "description": "The Bloodbath variant of Don Doody. His toilet throne is now soaked in crimson. The smell is indescribable, the mess is legendary.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["don_doody_bloodbath"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_bloodbath"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Dork Angel",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_don_doody",
        "variant_name": "Bloodbath"
    },
    {
        "id": "card_don_doody_ice",
        "name": "Don Doody (Ice)",
        "description": "The Ice variant of Don Doody. Frozen solid on his porcelain throne. The only thing colder than his stare is his frozen toilet paper.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["don_doody_ice"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_ice"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Dork Angel",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_don_doody",
        "variant_name": "Ice"
    },
    {
        "id": "card_don_doody_psychedelic",
        "name": "Don Doody (Psychedelic)",
        "description": "The Psychedelic variant of Don Doody. His bathroom experience transcends dimensions. Rainbow-colored chaos erupts from his throne.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["don_doody_psychedelic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_psychedelic"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Dork Angel",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_don_doody",
        "variant_name": "Psychedelic"
    },
    {
        "id": "card_don_doody_biomechanical",
        "name": "Don Doody (Biomechanical)",
        "description": "The Biomechanical variant of Don Doody. His cybernetic bowels process waste with mechanical precision. Half-man, half-toilet, all terror.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["don_doody_biomechanical"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_biomechanical"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Dork Angel",
        "card_type": "A",
        "is_variant": True,
        "base_card_id": "card_don_doody",
        "variant_name": "Biomechanical"
    },
    {
        "id": "card_don_rotty",
        "name": "Don Rotty",
        "description": "Don Rotty is the festering vokillist that never decomposes but throws giant festering fits. You can't stand the way he screams or the way he smells!",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["don_rotty"],
        "back_image_url": CARD_BACK_IMAGE_URLS["don_rotty"],
        "coin_cost": 50,
        "available": True,
        "series": 2,
        "band": "Dork Angel",
        "card_type": "B"
    },
    # Don Rotty Variants
    {
        "id": "card_don_rotty_bloodbath",
        "name": "Don Rotty (Bloodbath)",
        "description": "The Bloodbath variant of Don Rotty. His decomposing form now oozes fresh crimson gore. The stench of death mixes with the smell of fresh blood.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["don_rotty_bloodbath"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_bloodbath"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Dork Angel",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_don_rotty",
        "variant_name": "Bloodbath"
    },
    {
        "id": "card_don_rotty_ice",
        "name": "Don Rotty (Ice)",
        "description": "The Ice variant of Don Rotty. Frozen in eternal decay, his screams echo through glacial tombs. The cold has preserved his rot forever.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["don_rotty_ice"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_ice"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Dork Angel",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_don_rotty",
        "variant_name": "Ice"
    },
    {
        "id": "card_don_rotty_psychedelic",
        "name": "Don Rotty (Psychedelic)",
        "description": "The Psychedelic variant of Don Rotty. His decay now pulses with kaleidoscopic colors. Each rotting piece is a window to another dimension.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["don_rotty_psychedelic"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_psychedelic"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Dork Angel",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_don_rotty",
        "variant_name": "Psychedelic"
    },
    {
        "id": "card_don_rotty_biomechanical",
        "name": "Don Rotty (Biomechanical)",
        "description": "The Biomechanical variant of Don Rotty. Cybernetic implants fight against his endless decay. Half-zombie, half-machine, all nightmare.",
        "rarity": "variant",
        "front_image_url": CARD_IMAGE_URLS["don_rotty_biomechanical"],
        "back_image_url": CARD_BACK_IMAGE_URLS["variant_back_biomechanical"],
        "coin_cost": 0,
        "available": False,
        "series": 2,
        "band": "Dork Angel",
        "card_type": "B",
        "is_variant": True,
        "base_card_id": "card_don_rotty",
        "variant_name": "Biomechanical"
    },
    # =====================
    # RARE CARDS - Series completion rewards
    # =====================
    {
        "id": "card_kerry_the_king",
        "name": "Kerry The King",
        "description": "Kerry the King rules the stage with a monstrous ego and an even more monstrous scowl. He makes Slash look like Fred Rodgers when he thrashes out blistering solos while glaring daggers into the crowd.",
        "rarity": "rare",
        "front_image_url": CARD_IMAGE_URLS["kerry_the_king"],
        "back_image_url": CARD_BACK_IMAGE_URLS["kerry_the_king"],
        "coin_cost": 100,
        "available": False,
        "achievement_required": 16,  # Unlocks after completing Series 1
        "series_reward": 1,
        "band": "$LAYA"
    },
    {
        "id": "card_strap_on_taylor",
        "name": "Strap-On Taylor",
        "description": "Strap-on hot dog lensing into subject's brain during sustained screeching. Secondary splash exposure ensued. Head rig will need to be burned. Mic infested with maggots.",
        "rarity": "rare",
        "front_image_url": CARD_IMAGE_URLS["strap_on_taylor"],
        "back_image_url": CARD_BACK_IMAGE_URLS["strap_on_taylor"],
        "coin_cost": 100,
        "available": False,
        "achievement_required": 32,  # Unlocks after completing Series 2
        "series_reward": 2,
        "band": "Sucrilege B.J."
    },
    # =====================
    # SERIES 3 - 8 bands, 16 cards (A & B for each band)
    # =====================
    # Band 1: Underkill
    {
        "id": "card_nobby_blitz",
        "name": "Nobby Blitz",
        "description": "Nobby Blitz headbangs so hard his brain rattles like a maraca. He's got more neck problems than a giraffe in a lightning storm.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["nobby_blitz"],
        "back_image_url": CARD_BACK_IMAGE_URLS["nobby_blitz"],
        "coin_cost": 50,
        "available": True,
        "series": 3,
        "band": "Underkill",
        "card_type": "A"
    },
    {
        "id": "card_bobby_blitzed",
        "name": "Bobby Blitzed",
        "description": "Bobby Blitzed is perpetually three sheets to the wind. His solos are sloppy, his balance is worse, and his breath could melt steel.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["bobby_blitzed"],
        "back_image_url": CARD_BACK_IMAGE_URLS["bobby_blitzed"],
        "coin_cost": 50,
        "available": True,
        "series": 3,
        "band": "Underkill",
        "card_type": "B"
    },
    # Band 2: Meadow Church
    {
        "id": "card_david_whine",
        "name": "David Whine",
        "description": "David Whine complains about everything - the lighting, the sound, the catering. His vocals are 90% grievances set to music.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["david_whine"],
        "back_image_url": CARD_BACK_IMAGE_URLS["david_whine"],
        "coin_cost": 50,
        "available": True,
        "series": 3,
        "band": "Meadow Church",
        "card_type": "A"
    },
    {
        "id": "card_david_slayne",
        "name": "David Slayne",
        "description": "David Slayne murders riffs with ruthless precision. His guitar skills are killer, literally - several amps have died mid-show.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["david_slayne"],
        "back_image_url": CARD_BACK_IMAGE_URLS["david_slayne"],
        "coin_cost": 50,
        "available": True,
        "series": 3,
        "band": "Meadow Church",
        "card_type": "B"
    },
    # Band 3: Sabutt
    {
        "id": "card_martini_walkyier",
        "name": "Martini Walkyier",
        "description": "Martini Walkyier is half mystical shaman, half cocktail enthusiast. He summons spirits from the bar as often as from beyond.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["martini_walkyier"],
        "back_image_url": CARD_BACK_IMAGE_URLS["martini_walkyier"],
        "coin_cost": 50,
        "available": True,
        "series": 3,
        "band": "Sabutt",
        "card_type": "A"
    },
    {
        "id": "card_martin_wankyier",
        "name": "Martin Wankyier",
        "description": "Martin Wankyier's ego is bigger than his amp stack. He thinks he's a guitar god, but mostly he's just godawful loud.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["martin_wankyier"],
        "back_image_url": CARD_BACK_IMAGE_URLS["martin_wankyier"],
        "coin_cost": 50,
        "available": True,
        "series": 3,
        "band": "Sabutt",
        "card_type": "B"
    },
    # Band 4: Celtic Frosty
    {
        "id": "card_tom_g_worrier",
        "name": "Tom G. Worrier",
        "description": "Tom G. Worrier is perpetually anxious about everything - stage fright, string breaks, existential dread. His worried face is legendary.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["tom_g_worrier"],
        "back_image_url": CARD_BACK_IMAGE_URLS["tom_g_worrier"],
        "coin_cost": 50,
        "available": True,
        "series": 3,
        "band": "Celtic Frosty",
        "card_type": "A"
    },
    {
        "id": "card_tom_g_wore_out",
        "name": "Tom G. Wore Out",
        "description": "Tom G. Wore Out has been touring since the ice age. He's exhausted, grumpy, and his back hurts. But he still shreds.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["tom_g_wore_out"],
        "back_image_url": CARD_BACK_IMAGE_URLS["tom_g_wore_out"],
        "coin_cost": 50,
        "available": True,
        "series": 3,
        "band": "Celtic Frosty",
        "card_type": "B"
    },
    # Band 5: Venum
    {
        "id": "card_coronos",
        "name": "Coronos",
        "description": "Coronos spreads chaos wherever he goes. His presence is infectious, his riffs are viral, and his stage presence is pandemic.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["coronos"],
        "back_image_url": CARD_BACK_IMAGE_URLS["coronos"],
        "coin_cost": 50,
        "available": True,
        "series": 3,
        "band": "Venum",
        "card_type": "A"
    },
    {
        "id": "card_groanos",
        "name": "Groanos",
        "description": "Groanos makes sounds that shouldn't come from a human throat. His growls are so deep they register on seismographs.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["groanos"],
        "back_image_url": CARD_BACK_IMAGE_URLS["groanos"],
        "coin_cost": 50,
        "available": True,
        "series": 3,
        "band": "Venum",
        "card_type": "B"
    },
    # Band 6: Sadust
    {
        "id": "card_darren_travesty",
        "name": "Darren Travesty",
        "description": "Darren Travesty's performances are a disaster zone. Broken strings, failed pyrotechnics, wardrobe malfunctions - all in a day's work.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["darren_travesty"],
        "back_image_url": CARD_BACK_IMAGE_URLS["darren_travesty"],
        "coin_cost": 50,
        "available": True,
        "series": 3,
        "band": "Sadust",
        "card_type": "A"
    },
    {
        "id": "card_daring_travis",
        "name": "Daring Travis",
        "description": "Daring Travis attempts stunts that would make Evil Knievel nervous. Stage diving from the lighting rig is just Tuesday for him.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["daring_travis"],
        "back_image_url": CARD_BACK_IMAGE_URLS["daring_travis"],
        "coin_cost": 50,
        "available": True,
        "series": 3,
        "band": "Sadust",
        "card_type": "B"
    },
    # Band 7: High Racks
    {
        "id": "card_cretin_w_de_pena",
        "name": "Cretin W. De Pena",
        "description": "Cretin W. De Pena has the IQ of a drumstick but the rhythm of a metronome. Don't ask him to count past four.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["cretin_w_de_pena"],
        "back_image_url": CARD_BACK_IMAGE_URLS["cretin_w_de_pena"],
        "coin_cost": 50,
        "available": True,
        "series": 3,
        "band": "High Racks",
        "card_type": "A"
    },
    {
        "id": "card_katon_de_pain",
        "name": "Katon De Pain",
        "description": "Katon De Pain's vocals are so brutal they come with a health warning. Earplugs recommended, therapy optional.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["katon_de_pain"],
        "back_image_url": CARD_BACK_IMAGE_URLS["katon_de_pain"],
        "coin_cost": 50,
        "available": True,
        "series": 3,
        "band": "High Racks",
        "card_type": "B"
    },
    # Band 8: Suckrifice
    {
        "id": "card_rob_urinati",
        "name": "Rob Urinati",
        "description": "Rob Urinati marks his territory like a feral cat. Backstage areas beware - he's claimed more green rooms than he can remember.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["rob_urinati"],
        "back_image_url": CARD_BACK_IMAGE_URLS["rob_urinati"],
        "coin_cost": 50,
        "available": True,
        "series": 3,
        "band": "Suckrifice",
        "card_type": "A"
    },
    {
        "id": "card_slob_urbinati",
        "name": "Slob Urbinati",
        "description": "Slob Urbinati's personal hygiene is a biohazard. His crusty leather jacket has its own ecosystem and probably sentience.",
        "rarity": "common",
        "front_image_url": CARD_IMAGE_URLS["slob_urbinati"],
        "back_image_url": CARD_BACK_IMAGE_URLS["slob_urbinati"],
        "coin_cost": 50,
        "available": True,
        "series": 3,
        "band": "Suckrifice",
        "card_type": "B"
    },
    # =====================
    # EPIC CARD - Series 3 completion reward
    # =====================
    {
        "id": "card_sean_kill_again",
        "name": "Sean Kill-Again",
        "description": "Sean Kill-Again from Violents brings mayhem wherever he goes. His stage presence is so intense that security guards have resigned mid-show.",
        "rarity": "epic",
        "front_image_url": CARD_IMAGE_URLS["sean_kill_again"],
        "back_image_url": CARD_BACK_IMAGE_URLS["sean_kill_again"],
        "coin_cost": 150,
        "available": False,
        "achievement_required": 48,  # Unlocks after completing Series 3
        "series_reward": 3,
        "band": "Violents"
    },
]

INITIAL_GOALS = [
    {
        "id": "goal_daily_login_3",
        "title": "3 Day Streak",
        "description": "Log in for 3 consecutive days",
        "goal_type": "daily_login",
        "target_value": 3,
        "reward_coins": 50,
        "reward_card_id": None
    },
    {
        "id": "goal_daily_login_7",
        "title": "Week Warrior",
        "description": "Log in for 7 consecutive days",
        "goal_type": "daily_login",
        "target_value": 7,
        "reward_coins": 150,
        "reward_card_id": "card_silly_mille"
    },
    {
        "id": "goal_profile_complete",
        "title": "Complete Profile",
        "description": "Fill out your profile bio",
        "goal_type": "profile_complete",
        "target_value": 1,
        "reward_coins": 100,
        "reward_card_id": None
    },
    {
        "id": "goal_collect_coins_500",
        "title": "Coin Collector",
        "description": "Collect 500 coins",
        "goal_type": "collect_coins",
        "target_value": 500,
        "reward_coins": 100,
        "reward_card_id": None
    },
    {
        "id": "goal_collect_cards_3",
        "title": "Card Enthusiast",
        "description": "Collect a card from all 3 rarities (Common, Rare, Epic)",
        "goal_type": "collect_all_rarities",
        "target_value": 3,
        "reward_coins": 150,
        "reward_card_id": None
    },
    {
        "id": "goal_collect_all",
        "title": "Thrash Master",
        "description": "Collect 50 cards total",
        "goal_type": "collect_cards",
        "target_value": 50,
        "reward_coins": 250,
        "reward_card_id": None
    }
]

# =====================
# Database Initialization
# =====================

async def seed_database():
    """Seed the database with initial cards and goals"""
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

@api_router.get("/cards")
async def get_all_cards():
    """Get all available cards"""
    cards = await db.cards.find().to_list(500)
    return [Card(**card) for card in cards]

@api_router.get("/cards/rare")
async def get_rare_cards():
    """Get all rare achievement cards"""
    rare_cards = await db.cards.find({"rarity": "rare"}).to_list(100)
    return [Card(**rare_card) for rare_card in rare_cards]

@api_router.get("/cards/epic")
async def get_epic_cards():
    """Get all epic streak cards"""
    epic_cards = await db.cards.find({"rarity": "epic"}).to_list(100)
    return [Card(**epic_card) for epic_card in epic_cards]

@api_router.get("/cards/{card_id}")
async def get_card(card_id: str):
    """Get a specific card"""
    card = await db.cards.find_one({"id": card_id})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return Card(**card)

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
    
    user = User(username=request.username, coins=100)  # Start with 100 coins
    await db.users.insert_one(user.dict())
    
    # Initialize user goals
    goals = await db.goals.find().to_list(100)
    for goal in goals:
        user_goal = UserGoal(user_id=user.id, goal_id=goal["id"])
        await db.user_goals.insert_one(user_goal.dict())
    
    return user

@api_router.get("/users/{user_id}")
async def get_user(user_id: str):
    """Get user details"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return User(**user)

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

# =====================
# Daily Login & Coins
# =====================

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
    
    # Calculate bonus coins (more coins for longer streaks)
    bonus_coins = min(10 + (new_streak * 5), 50)  # Max 50 coins per day
    
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
    
    # Check coin collection goals
    await check_and_update_goals(user_id, "collect_coins", new_coins)
    
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
    user_cards = await db.user_cards.find({"user_id": user_id}).to_list(100)
    
    result = []
    for uc in user_cards:
        card = await db.cards.find_one({"id": uc["card_id"]})
        if card:
            result.append({
                "user_card_id": uc["id"],
                "card": Card(**card),
                "quantity": uc["quantity"],
                "acquired_at": uc["acquired_at"]
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

@api_router.get("/spin/config")
async def get_spin_config():
    """Get spin wheel configuration"""
    return {
        "spin_cost": SPIN_COST,
        "odds": {"common": 100}  # All cards in spin pool are common for Series 1
    }

@api_router.post("/users/{user_id}/spin")
async def spin_wheel(user_id: str):
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
    current_series = max(s for s in unlocked_series if s not in completed_series) if unlocked_series else 1
    
    # Get available cards for the spin (only from current series)
    series_cards = await db.cards.find({
        "series": current_series,
        "rarity": "common",
        "available": True,
        "engagement_milestone": None  # Exclude engagement milestone cards
    }).to_list(100)
    
    if not series_cards:
        raise HTTPException(status_code=400, detail="No cards available to spin in current series")
    
    # Pick a random card
    won_card = random.choice(series_cards)
    
    # Deduct coins and track spending
    new_coins = user.get("coins", 0) - SPIN_COST
    new_total_spent = user.get("total_spent_coins", 0) + SPIN_COST
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"coins": new_coins, "total_spent_coins": new_total_spent}}
    )
    
    # Add card to collection (or increase quantity if duplicate)
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
    
    # Check for series completion
    series_completion = await check_series_completion(user_id, current_series)
    
    # Check for achievements after spin
    unique_cards = await db.user_cards.count_documents({"user_id": user_id})
    await check_and_update_goals(user_id, "collect_cards", unique_cards)
    await check_all_rarities_goal(user_id)
    engagement_unlock = await check_engagement_milestones(user_id)
    
    return {
        "success": True,
        "won_card": Card(**won_card),
        "rarity": "common",
        "is_duplicate": is_duplicate,
        "remaining_coins": new_coins,
        "spin_cost": SPIN_COST,
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
    
    if owned_count >= required_count and series_num not in completed_series:
        # Series completed! Mark as complete
        completed_series.append(series_num)
        
        # Unlock next series
        unlocked_series = user.get("unlocked_series", [1])
        next_series = series_num + 1
        if next_series not in unlocked_series and next_series <= 4:
            unlocked_series.append(next_series)
        
        # Get rare reward card for this series
        series_config = SERIES_CONFIG.get(series_num, {})
        rare_reward_id = series_config.get("rare_reward")
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
            "next_series_unlocked": next_series if next_series <= 4 else None
        }
    
    return {
        "series_completed": None,
        "progress": owned_count,
        "required": required_count
    }

@api_router.get("/users/{user_id}/spin-pool")
async def get_spin_pool(user_id: str):
    """Get the cards available in the spin pool for this user's current series"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's unlocked series (default to series 1)
    unlocked_series = user.get("unlocked_series", [1])
    if not unlocked_series:
        unlocked_series = [1]
    
    # Get current series (the highest unlocked series that's not completed)
    completed_series = user.get("completed_series", [])
    current_series = max(s for s in unlocked_series if s not in completed_series) if [s for s in unlocked_series if s not in completed_series] else max(unlocked_series)
    
    # Get series config
    series_config = SERIES_CONFIG.get(current_series, {})
    
    # Get cards from current series only
    series_cards = await db.cards.find({
        "series": current_series,
        "rarity": "common",
        "available": True,
        "engagement_milestone": None
    }, {"_id": 0}).to_list(100)
    
    # Get user's owned cards from this series
    user_cards = await db.user_cards.find({"user_id": user_id}).to_list(1000)
    owned_card_ids = set(uc["card_id"] for uc in user_cards)
    
    # Mark which cards are owned
    for card in series_cards:
        card["owned"] = card["id"] in owned_card_ids
    
    # Get rare reward info for this series
    rare_reward = None
    if series_config.get("rare_reward"):
        rare_card = await db.cards.find_one({"id": series_config["rare_reward"]}, {"_id": 0})
        if rare_card:
            rare_reward = rare_card
    
    owned_count = sum(1 for c in series_cards if c["owned"])
    
    return {
        "current_series": current_series,
        "series_name": series_config.get("name", f"Series {current_series}"),
        "series_description": series_config.get("description", ""),
        "series_cards": series_cards,
        "owned_count": owned_count,
        "total_count": len(series_cards),
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
    for series_num in range(1, 5):
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
        
        all_series.append({
            "series_num": series_num,
            "name": series_config.get("name", f"Series {series_num}"),
            "description": series_config.get("description", ""),
            "unlocked": series_num in unlocked_series,
            "completed": series_num in completed_series,
            "owned_count": owned_in_series,
            "total_count": len(series_cards),
            "rare_reward": rare_reward
        })
    
    return {
        "series": all_series,
        "current_series": max(s for s in unlocked_series if s not in completed_series) if [s for s in unlocked_series if s not in completed_series] else max(unlocked_series)
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
    
    # Get all rare cards that require achievements
    rare_cards = await db.cards.find({"rarity": "rare", "achievement_required": {"$ne": None}}).to_list(100)
    
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
    
    # Get all rare cards and their status for this user
    rare_cards = await db.cards.find({"rarity": "rare"}).to_list(100)
    
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
    
    # Add variant to user's collection
    variant_user_card = UserCard(user_id=user_id, card_id=won_variant["id"])
    await db.user_cards.insert_one(variant_user_card.dict())
    
    logger.info(f"User {user_id} traded in 5x {base_card['name']} for variant: {won_variant['name']}")
    
    won_variant_copy = {k: v for k, v in won_variant.items() if k != "_id"}
    
    return {
        "success": True,
        "won_variant": Card(**won_variant_copy),
        "remaining_quantity": max(0, new_quantity),
        "variants_owned": len(owned_variant_ids) + 1,
        "variants_total": len(variants)
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
    """Get user's goal progress"""
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
    
    # Create webhook URL
    host_url = str(http_request.base_url).rstrip('/')
    webhook_url = f"{host_url}api/webhook/stripe"
    
    # Initialize Stripe checkout
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    
    # Create checkout session with server-defined amount
    checkout_request = CheckoutSessionRequest(
        amount=float(package["price"]),
        currency=package["currency"],
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
    
    try:
        session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(checkout_request)
        
        # Create payment transaction record BEFORE redirecting to Stripe
        transaction = PaymentTransaction(
            user_id=user_id,
            session_id=session.session_id,
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
            "session_id": session.session_id,
            "package": package,
            "is_first_purchase": is_first_purchase,
            "bonus_coins": bonus_coins,
            "total_coins": total_coins
        }
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")

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
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url="")
    
    try:
        checkout_status: CheckoutStatusResponse = await stripe_checkout.get_checkout_status(session_id)
        
        # Update transaction status
        new_status = "completed" if checkout_status.payment_status == "paid" else transaction.get("status")
        
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {
                "payment_status": checkout_status.payment_status,
                "status": new_status,
                "updated_at": datetime.utcnow()
            }}
        )
        
        # If payment is successful and not already processed, credit coins
        coins_credited = 0
        if checkout_status.payment_status == "paid" and transaction.get("payment_status") != "paid":
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
            "payment_status": checkout_status.payment_status,
            "amount_total": checkout_status.amount_total,
            "currency": checkout_status.currency,
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
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Payment service not configured")
    
    host_url = str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    
    try:
        body = await request.body()
        signature = request.headers.get("Stripe-Signature")
        
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        
        # Process based on event type
        if webhook_response.payment_status == "paid":
            session_id = webhook_response.session_id
            
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

@api_router.get("/")
async def root():
    return {"message": "Thrash Kan Kidz Card Collector API"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy"}

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
    logger.info("Database seeded successfully")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

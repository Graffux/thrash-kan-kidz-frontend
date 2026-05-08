"""
Database connection and initialization
"""
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
from dotenv import load_dotenv
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env', override=False)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Collection references
users_collection = db.users
cards_collection = db.cards
user_cards_collection = db.user_cards
goals_collection = db.goals
user_goals_collection = db.user_goals
trades_collection = db.trades
payments_collection = db.payments

async def close_db_connection():
    """Close database connection"""
    client.close()

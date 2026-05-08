"""
Application configuration and constants
"""
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Spin/Pack Configuration
SPIN_COST = 50  # Coins per spin

# Series Configuration
# Each series has 16 cards (8 bands x 2 cards: A & B)
# Completing a series unlocks a rare card reward + next series
SERIES_CONFIG = {
    1: {
        "name": "Series 1",
        "cards_required": 16,
        "rare_reward": "card_kerry_the_king",
        "description": "The Original Thrash Kan Kidz"
    },
    2: {
        "name": "Series 2", 
        "cards_required": 16,
        "rare_reward": "card_strap_on_taylor",
        "description": "More Mayhem"
    },
    3: {
        "name": "Series 3",
        "cards_required": 16,
        "rare_reward": "card_sean_kill_again",
        "description": "The Thrash Continues"
    }
}

# Coin Purchase Packages (Server-side defined - NEVER accept from frontend)
COIN_PACKAGES = {
    "small": {
        "id": "small",
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
        "name": "Collector Pack",
        "coins": 500,
        "price": 4.99,
        "currency": "usd",
        "description": "500 coins - Best value!",
        "coins_per_dollar": 100.2,
        "bonus_percentage": 0
    },
    "large": {
        "id": "large",
        "name": "Ultimate Pack",
        "coins": 1000,
        "price": 9.99,
        "currency": "usd",
        "description": "1000 coins for serious collectors",
        "coins_per_dollar": 100.1,
        "bonus_percentage": 0
    }
}

# First purchase bonus
FIRST_PURCHASE_BONUS_PERCENTAGE = 50

# Variant types per series
VARIANT_TYPES = {
    1: ["Toxic", "Electric", "Hellfire", "Cosmic"],
    2: ["Bloodbath", "Ice", "Psychedelic", "Biomechanical"]
}

# Variant back images
VARIANT_BACK_IMAGES = {
    1: {
        "Toxic": "https://i.ibb.co/Lh7HxBvn/Toxic-back.jpg",
        "Electric": "https://i.ibb.co/PZYQv4Zd/Electric-back.jpg",
        "Hellfire": "https://i.ibb.co/wFHZBdZ8/Hellfire-back.jpg",
        "Cosmic": "https://i.ibb.co/B5g1pccQ/Cosmic-back.jpg"
    },
    2: {
        "Bloodbath": "https://i.ibb.co/7JJ0BrrT/Bloodbath-back.jpg",
        "Ice": "https://i.ibb.co/0p39gfpn/Ice-back.jpg",
        "Psychedelic": "https://i.ibb.co/HfCz9t8J/Psychedelic-back.jpg",
        "Biomechanical": "https://i.ibb.co/HDqwjZ6K/Biomechanical-back.jpg"
    }
}

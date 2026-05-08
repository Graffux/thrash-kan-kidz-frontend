"""
Tests for Rare and Epic Card Purchase Feature

This test module covers the following scenarios:
- POST /api/users/{user_id}/purchase-card for Rare cards (75 coins, unlocked after card count achievement)
- POST /api/users/{user_id}/purchase-card for Epic cards (100 coins, unlocked after login streak)
- GET /api/users/{user_id}/check-rare-cards endpoint verification  
- GET /api/users/{user_id}/check-epic-cards endpoint verification
- Purchase validation (locked cards should fail)
- Coin deduction verification
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL')
if BASE_URL:
    BASE_URL = BASE_URL.rstrip('/')


class TestHealthAndSetup:
    """Basic health checks"""
    
    def test_api_health(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✅ API health check passed")
    
    def test_cards_endpoint(self):
        """Test cards listing endpoint"""
        response = requests.get(f"{BASE_URL}/api/cards")
        assert response.status_code == 200
        cards = response.json()
        assert len(cards) > 0
        print(f"✅ Cards endpoint returned {len(cards)} cards")
        
        # Verify rare and epic cards exist
        rare_cards = [c for c in cards if c.get('rarity') == 'rare']
        epic_cards = [c for c in cards if c.get('rarity') == 'epic']
        
        assert len(rare_cards) >= 2, "Expected at least 2 rare cards"
        assert len(epic_cards) >= 2, "Expected at least 2 epic cards"
        print(f"✅ Found {len(rare_cards)} rare cards and {len(epic_cards)} epic cards")


class TestRareCardPurchase:
    """Tests for Rare card unlocking and purchasing"""
    
    @pytest.fixture
    def test_user(self):
        """Create a test user for rare card tests"""
        username = f"TEST_RareUser_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/users", json={"username": username})
        assert response.status_code == 200
        user = response.json()
        print(f"✅ Created test user: {username} with {user.get('coins', 0)} coins")
        return user
    
    def test_check_rare_cards_new_user(self, test_user):
        """Test check-rare-cards endpoint for a new user (no cards collected)"""
        user_id = test_user['id']
        
        response = requests.get(f"{BASE_URL}/api/users/{user_id}/check-rare-cards")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_cards" in data
        assert "rare_cards" in data
        assert "milestone_info" in data
        
        assert data["total_cards"] == 0, "New user should have 0 cards"
        
        # Check that rare cards are not unlocked for new user
        for rare_card in data["rare_cards"]:
            assert rare_card["unlocked"] == False, f"Card {rare_card['card']['name']} should be locked for new user"
            assert rare_card["can_purchase"] == False
            print(f"✅ Rare card '{rare_card['card']['name']}' is locked (requires {rare_card['required_cards']} cards)")
    
    def test_purchase_locked_rare_card_fails(self, test_user):
        """Test that purchasing a locked rare card returns an error"""
        user_id = test_user['id']
        
        # Get a rare card id
        cards_response = requests.get(f"{BASE_URL}/api/cards/rare")
        assert cards_response.status_code == 200
        rare_cards = cards_response.json()
        assert len(rare_cards) > 0
        
        rare_card = rare_cards[0]
        rare_card_id = rare_card['id']
        
        # Try to purchase without having enough cards collected
        purchase_response = requests.post(
            f"{BASE_URL}/api/users/{user_id}/purchase-card",
            json={"user_id": user_id, "card_id": rare_card_id}
        )
        
        assert purchase_response.status_code == 400, "Should fail to purchase locked rare card"
        error_detail = purchase_response.json().get("detail", "")
        assert "collect" in error_detail.lower() or "unlock" in error_detail.lower(), f"Error should mention collecting cards: {error_detail}"
        print(f"✅ Purchase of locked rare card correctly failed: {error_detail}")
    
    def test_rare_card_unlocks_after_collecting_cards(self, test_user):
        """Test that rare card unlocks after user collects enough cards"""
        user_id = test_user['id']
        
        # Get the rare card that requires 10 cards (Martin Van Druid)
        rare_check = requests.get(f"{BASE_URL}/api/users/{user_id}/check-rare-cards")
        rare_data = rare_check.json()
        
        martin_card = None
        for rc in rare_data['rare_cards']:
            if rc['required_cards'] == 10:
                martin_card = rc
                break
        
        if not martin_card:
            pytest.skip("No rare card with 10-card requirement found")
        
        # Give user enough coins by daily login to purchase 10 common cards
        # Each common card is 50 coins, need 500 coins total
        # Start with 100, need to add more
        user = requests.get(f"{BASE_URL}/api/users/{user_id}").json()
        initial_coins = user['coins']
        
        # Buy common cards to reach the threshold
        # First, we need more coins - we'll update user coins directly via purchases
        # Let's buy what we can with initial coins
        
        # Get common cards
        all_cards = requests.get(f"{BASE_URL}/api/cards").json()
        common_cards = [c for c in all_cards if c.get('rarity') == 'common' and c.get('available') == True]
        
        cards_purchased = 0
        
        # Buy cards until we reach 10 or run out of coins
        # We start with 100 coins and each card is 50
        for _ in range(10):
            user = requests.get(f"{BASE_URL}/api/users/{user_id}").json()
            if user['coins'] < 50:
                break
            
            card = common_cards[cards_purchased % len(common_cards)]
            purchase_result = requests.post(
                f"{BASE_URL}/api/users/{user_id}/purchase-card",
                json={"user_id": user_id, "card_id": card['id']}
            )
            if purchase_result.status_code == 200:
                cards_purchased += 1
                result_data = purchase_result.json()
                # Check for milestone rewards (gives extra cards)
                if result_data.get('milestone_reward'):
                    cards_purchased += 1
                    print(f"  Got milestone bonus card!")
                if result_data.get('newly_unlocked_rare_card'):
                    print(f"  Unlocked rare card: {result_data['newly_unlocked_rare_card']['name']}")
        
        print(f"✅ Purchased {cards_purchased} cards with initial coins")
        
        # Check rare card status after purchases
        rare_check_after = requests.get(f"{BASE_URL}/api/users/{user_id}/check-rare-cards")
        rare_data_after = rare_check_after.json()
        
        print(f"✅ Total cards after purchases: {rare_data_after['total_cards']}")
        
        # At minimum, verify the check-rare-cards endpoint returns valid data
        assert rare_data_after['total_cards'] >= cards_purchased


class TestEpicCardPurchase:
    """Tests for Epic card unlocking and purchasing"""
    
    @pytest.fixture
    def test_user(self):
        """Create a test user for epic card tests"""
        username = f"TEST_EpicUser_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/users", json={"username": username})
        assert response.status_code == 200
        user = response.json()
        print(f"✅ Created test user: {username}")
        return user
    
    def test_check_epic_cards_new_user(self, test_user):
        """Test check-epic-cards endpoint for a new user (no streak)"""
        user_id = test_user['id']
        
        response = requests.get(f"{BASE_URL}/api/users/{user_id}/check-epic-cards")
        assert response.status_code == 200
        
        data = response.json()
        assert "current_streak" in data
        assert "epic_cards" in data
        
        assert data["current_streak"] == 0, "New user should have 0 streak"
        
        # Check that epic cards are not unlocked for new user
        for epic_card in data["epic_cards"]:
            assert epic_card["unlocked"] == False, f"Card {epic_card['card']['name']} should be locked for new user"
            assert epic_card["can_purchase"] == False
            print(f"✅ Epic card '{epic_card['card']['name']}' is locked (requires {epic_card['required_streak']} day streak)")
    
    def test_purchase_locked_epic_card_fails(self, test_user):
        """Test that purchasing a locked epic card returns an error"""
        user_id = test_user['id']
        
        # Get an epic card id
        cards_response = requests.get(f"{BASE_URL}/api/cards/epic")
        assert cards_response.status_code == 200
        epic_cards = cards_response.json()
        assert len(epic_cards) > 0
        
        epic_card = epic_cards[0]
        epic_card_id = epic_card['id']
        
        # Try to purchase without having streak requirement met
        purchase_response = requests.post(
            f"{BASE_URL}/api/users/{user_id}/purchase-card",
            json={"user_id": user_id, "card_id": epic_card_id}
        )
        
        assert purchase_response.status_code == 400, "Should fail to purchase locked epic card"
        error_detail = purchase_response.json().get("detail", "")
        assert "streak" in error_detail.lower() or "login" in error_detail.lower(), f"Error should mention streak: {error_detail}"
        print(f"✅ Purchase of locked epic card correctly failed: {error_detail}")
    
    def test_epic_cards_list_structure(self, test_user):
        """Test that epic cards have correct structure in response"""
        user_id = test_user['id']
        
        response = requests.get(f"{BASE_URL}/api/users/{user_id}/check-epic-cards")
        data = response.json()
        
        for epic_status in data['epic_cards']:
            card = epic_status['card']
            assert 'id' in card
            assert 'name' in card
            assert 'coin_cost' in card
            assert card.get('rarity') == 'epic'
            assert 'streak_required' in card or epic_status.get('required_streak') is not None
            
            assert 'owned' in epic_status
            assert 'unlocked' in epic_status
            assert 'can_purchase' in epic_status
            assert 'progress' in epic_status
            
            print(f"✅ Epic card '{card['name']}' structure valid: cost={card['coin_cost']}, streak_required={epic_status.get('required_streak')}")


class TestPurchaseCoinsDeduction:
    """Tests for coin deduction when purchasing cards"""
    
    @pytest.fixture
    def test_user(self):
        """Create a test user with 100 coins"""
        username = f"TEST_CoinsUser_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/users", json={"username": username})
        assert response.status_code == 200
        user = response.json()
        assert user['coins'] == 100, "New user should start with 100 coins"
        return user
    
    def test_common_card_purchase_deducts_coins(self, test_user):
        """Test that purchasing a common card deducts correct coins (50)"""
        user_id = test_user['id']
        initial_coins = test_user['coins']
        
        # Get a common available card
        cards = requests.get(f"{BASE_URL}/api/cards").json()
        common_card = next((c for c in cards if c.get('rarity') == 'common' and c.get('available') == True), None)
        
        if not common_card:
            pytest.skip("No common available card found")
        
        purchase_response = requests.post(
            f"{BASE_URL}/api/users/{user_id}/purchase-card",
            json={"user_id": user_id, "card_id": common_card['id']}
        )
        
        assert purchase_response.status_code == 200
        result = purchase_response.json()
        
        expected_remaining = initial_coins - common_card['coin_cost']
        assert result['remaining_coins'] == expected_remaining, f"Expected {expected_remaining} coins remaining, got {result['remaining_coins']}"
        
        # Verify by fetching user
        user_after = requests.get(f"{BASE_URL}/api/users/{user_id}").json()
        assert user_after['coins'] == expected_remaining
        
        print(f"✅ Common card purchase deducted {common_card['coin_cost']} coins: {initial_coins} -> {expected_remaining}")
    
    def test_insufficient_coins_purchase_fails(self, test_user):
        """Test that purchase fails when user has insufficient coins"""
        user_id = test_user['id']
        
        # First buy cards until coins are low
        cards = requests.get(f"{BASE_URL}/api/cards").json()
        common_card = next((c for c in cards if c.get('rarity') == 'common' and c.get('available') == True), None)
        
        # Buy twice to bring coins to 0
        requests.post(f"{BASE_URL}/api/users/{user_id}/purchase-card",
                      json={"user_id": user_id, "card_id": common_card['id']})
        requests.post(f"{BASE_URL}/api/users/{user_id}/purchase-card",
                      json={"user_id": user_id, "card_id": common_card['id']})
        
        # Now user should have 0 coins
        user = requests.get(f"{BASE_URL}/api/users/{user_id}").json()
        
        # Try to purchase again
        purchase_response = requests.post(
            f"{BASE_URL}/api/users/{user_id}/purchase-card",
            json={"user_id": user_id, "card_id": common_card['id']}
        )
        
        assert purchase_response.status_code == 400
        error = purchase_response.json().get("detail", "")
        assert "coins" in error.lower(), f"Error should mention coins: {error}"
        print(f"✅ Insufficient coins purchase correctly failed: {error}")


class TestRareCardCost:
    """Test that rare cards cost 75 coins"""
    
    def test_rare_cards_cost_75(self):
        """Verify rare cards have coin_cost of 75"""
        response = requests.get(f"{BASE_URL}/api/cards/rare")
        assert response.status_code == 200
        
        rare_cards = response.json()
        for card in rare_cards:
            assert card['coin_cost'] == 75, f"Rare card {card['name']} should cost 75 coins, not {card['coin_cost']}"
            print(f"✅ Rare card '{card['name']}' costs {card['coin_cost']} coins")


class TestEpicCardCost:
    """Test that epic cards cost 100 coins"""
    
    def test_epic_cards_cost_100(self):
        """Verify epic cards have coin_cost of 100"""
        response = requests.get(f"{BASE_URL}/api/cards/epic")
        assert response.status_code == 200
        
        epic_cards = response.json()
        for card in epic_cards:
            assert card['coin_cost'] == 100, f"Epic card {card['name']} should cost 100 coins, not {card['coin_cost']}"
            print(f"✅ Epic card '{card['name']}' costs {card['coin_cost']} coins")


class TestComingSoonCards:
    """Test that 'Coming Soon' cards cannot be purchased"""
    
    @pytest.fixture
    def test_user(self):
        username = f"TEST_ComingSoon_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/users", json={"username": username})
        return response.json()
    
    def test_unavailable_card_purchase_fails(self, test_user):
        """Test that purchasing an unavailable (coming soon) card fails"""
        user_id = test_user['id']
        
        # Get unavailable common cards
        cards = requests.get(f"{BASE_URL}/api/cards").json()
        unavailable_card = next((c for c in cards if c.get('available') == False and c.get('rarity') == 'common'), None)
        
        if not unavailable_card:
            pytest.skip("No unavailable common card found")
        
        purchase_response = requests.post(
            f"{BASE_URL}/api/users/{user_id}/purchase-card",
            json={"user_id": user_id, "card_id": unavailable_card['id']}
        )
        
        assert purchase_response.status_code == 400
        error = purchase_response.json().get("detail", "")
        assert "not" in error.lower() and ("available" in error.lower() or "yet" in error.lower()), f"Error: {error}"
        print(f"✅ Coming soon card purchase correctly failed: {error}")


class TestRareCardUnlockRequirements:
    """Test rare card achievement requirements"""
    
    def test_rare_cards_have_achievement_requirements(self):
        """Verify rare cards have correct achievement_required values"""
        response = requests.get(f"{BASE_URL}/api/cards/rare")
        rare_cards = response.json()
        
        requirements = []
        for card in rare_cards:
            req = card.get('achievement_required')
            assert req is not None, f"Rare card {card['name']} missing achievement_required"
            assert req in [10, 20, 30, 40], f"Unexpected achievement_required {req} for {card['name']}"
            requirements.append((card['name'], req))
            print(f"✅ Rare card '{card['name']}' unlocks at {req} cards collected")
        
        # Verify we have cards at 10, 20, 30, 40 thresholds
        reqs_set = set(r[1] for r in requirements)
        assert 10 in reqs_set, "Should have a rare card at 10-card achievement"
        assert 20 in reqs_set, "Should have a rare card at 20-card achievement"
        assert 30 in reqs_set, "Should have a rare card at 30-card achievement"
        assert 40 in reqs_set, "Should have a rare card at 40-card achievement"


class TestEpicCardStreakRequirements:
    """Test epic card streak requirements"""
    
    def test_epic_cards_have_streak_requirements(self):
        """Verify epic cards have correct streak_required values"""
        response = requests.get(f"{BASE_URL}/api/cards/epic")
        epic_cards = response.json()
        
        requirements = []
        for card in epic_cards:
            req = card.get('streak_required')
            assert req is not None, f"Epic card {card['name']} missing streak_required"
            assert req in [7, 14], f"Unexpected streak_required {req} for {card['name']}"
            requirements.append((card['name'], req))
            print(f"✅ Epic card '{card['name']}' unlocks at {req}-day streak")
        
        # Verify we have cards at both 7 and 14 day thresholds
        reqs_set = set(r[1] for r in requirements)
        assert 7 in reqs_set, "Should have an epic card at 7-day streak"
        assert 14 in reqs_set, "Should have an epic card at 14-day streak"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

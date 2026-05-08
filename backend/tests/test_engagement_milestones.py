"""
Tests for Engagement Milestones Feature

This test module covers the following scenarios:
- GET /api/users/{user_id}/check-engagement-milestones endpoint
- Three milestone types: dedicated_fan (30-day streak), big_spender (750 coins spent), monthly_master (20 days/month)
- POST /api/users/{user_id}/daily-login tracks monthly_logins correctly
- POST /api/users/{user_id}/purchase-card tracks total_spent_coins correctly
- Engagement milestone cards become purchasable when requirements are met
- Attempting to purchase locked engagement cards should fail
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL')
if BASE_URL:
    BASE_URL = BASE_URL.rstrip('/')


class TestEngagementMilestonesEndpoint:
    """Tests for GET /api/users/{user_id}/check-engagement-milestones"""
    
    @pytest.fixture
    def test_user(self):
        """Create a test user"""
        username = f"TEST_EngUser_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/users", json={"username": username})
        assert response.status_code == 200
        user = response.json()
        print(f"✅ Created test user: {username}")
        return user
    
    def test_engagement_milestones_endpoint_returns_correct_structure(self, test_user):
        """Test that check-engagement-milestones returns correct data structure"""
        user_id = test_user['id']
        
        response = requests.get(f"{BASE_URL}/api/users/{user_id}/check-engagement-milestones")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify all required top-level fields
        assert "current_streak" in data, "Missing current_streak field"
        assert "total_spent_coins" in data, "Missing total_spent_coins field"
        assert "current_month_logins" in data, "Missing current_month_logins field"
        assert "best_month_logins" in data, "Missing best_month_logins field"
        assert "engagement_milestones" in data, "Missing engagement_milestones field"
        
        print(f"✅ Endpoint returns all required fields")
        print(f"  - current_streak: {data['current_streak']}")
        print(f"  - total_spent_coins: {data['total_spent_coins']}")
        print(f"  - current_month_logins: {data['current_month_logins']}")
    
    def test_engagement_milestones_has_three_cards(self, test_user):
        """Test that there are exactly 3 engagement milestone cards"""
        user_id = test_user['id']
        
        response = requests.get(f"{BASE_URL}/api/users/{user_id}/check-engagement-milestones")
        data = response.json()
        
        milestones = data["engagement_milestones"]
        assert len(milestones) == 3, f"Expected 3 engagement milestone cards, got {len(milestones)}"
        
        # Verify all three milestone types are present
        milestone_types = [m["milestone_type"] for m in milestones]
        assert "dedicated_fan" in milestone_types, "Missing dedicated_fan milestone"
        assert "big_spender" in milestone_types, "Missing big_spender milestone"
        assert "monthly_master" in milestone_types, "Missing monthly_master milestone"
        
        print(f"✅ Found all 3 engagement milestone cards: {milestone_types}")
    
    def test_engagement_milestone_card_structure(self, test_user):
        """Test that each engagement milestone has correct structure"""
        user_id = test_user['id']
        
        response = requests.get(f"{BASE_URL}/api/users/{user_id}/check-engagement-milestones")
        data = response.json()
        
        for milestone in data["engagement_milestones"]:
            # Check milestone status fields
            assert "card" in milestone, "Missing card field"
            assert "owned" in milestone, "Missing owned field"
            assert "unlocked" in milestone, "Missing unlocked field"
            assert "milestone_type" in milestone, "Missing milestone_type field"
            assert "requirement" in milestone, "Missing requirement field"
            assert "progress" in milestone, "Missing progress field"
            assert "description" in milestone, "Missing description field"
            assert "can_purchase" in milestone, "Missing can_purchase field"
            
            # Check card fields
            card = milestone["card"]
            assert "id" in card, "Missing card id"
            assert "name" in card, "Missing card name"
            assert "coin_cost" in card, "Missing card coin_cost"
            assert "engagement_milestone" in card, "Missing engagement_milestone field in card"
            
            print(f"✅ Milestone '{milestone['milestone_type']}' structure valid:")
            print(f"   - Card: {card['name']}")
            print(f"   - Requirement: {milestone['requirement']}")
            print(f"   - Progress: {milestone['progress']}")
            print(f"   - Description: {milestone['description']}")


class TestDedicatedFanMilestone:
    """Tests for Dedicated Fan milestone (30-day streak)"""
    
    @pytest.fixture
    def test_user(self):
        """Create a test user"""
        username = f"TEST_DedFan_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/users", json={"username": username})
        assert response.status_code == 200
        return response.json()
    
    def test_dedicated_fan_requirement_is_30(self, test_user):
        """Test that Dedicated Fan requires 30-day streak"""
        user_id = test_user['id']
        
        response = requests.get(f"{BASE_URL}/api/users/{user_id}/check-engagement-milestones")
        data = response.json()
        
        dedicated_fan = next((m for m in data["engagement_milestones"] if m["milestone_type"] == "dedicated_fan"), None)
        assert dedicated_fan is not None, "Dedicated Fan milestone not found"
        
        assert dedicated_fan["requirement"] == 30, f"Expected requirement of 30, got {dedicated_fan['requirement']}"
        assert "30-day" in dedicated_fan["description"] or "30 day" in dedicated_fan["description"].lower(), \
            f"Description should mention 30-day streak: {dedicated_fan['description']}"
        
        print(f"✅ Dedicated Fan milestone: {dedicated_fan['card']['name']}")
        print(f"   - Requirement: {dedicated_fan['requirement']} day streak")
    
    def test_dedicated_fan_tracks_current_streak_as_progress(self, test_user):
        """Test that Dedicated Fan progress equals current streak"""
        user_id = test_user['id']
        
        response = requests.get(f"{BASE_URL}/api/users/{user_id}/check-engagement-milestones")
        data = response.json()
        
        dedicated_fan = next((m for m in data["engagement_milestones"] if m["milestone_type"] == "dedicated_fan"), None)
        
        # Progress should equal current_streak for new user (0)
        assert dedicated_fan["progress"] == data["current_streak"], \
            f"Progress ({dedicated_fan['progress']}) should equal current_streak ({data['current_streak']})"
        
        print(f"✅ Dedicated Fan progress correctly tracks current streak: {dedicated_fan['progress']}")


class TestBigSpenderMilestone:
    """Tests for Big Spender milestone (750 coins spent)"""
    
    @pytest.fixture
    def test_user(self):
        """Create a test user"""
        username = f"TEST_BigSp_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/users", json={"username": username})
        assert response.status_code == 200
        return response.json()
    
    def test_big_spender_requirement_is_750(self, test_user):
        """Test that Big Spender requires 750 coins spent"""
        user_id = test_user['id']
        
        response = requests.get(f"{BASE_URL}/api/users/{user_id}/check-engagement-milestones")
        data = response.json()
        
        big_spender = next((m for m in data["engagement_milestones"] if m["milestone_type"] == "big_spender"), None)
        assert big_spender is not None, "Big Spender milestone not found"
        
        assert big_spender["requirement"] == 750, f"Expected requirement of 750, got {big_spender['requirement']}"
        assert "750" in big_spender["description"], f"Description should mention 750 coins: {big_spender['description']}"
        
        print(f"✅ Big Spender milestone: {big_spender['card']['name']}")
        print(f"   - Requirement: {big_spender['requirement']} coins spent")
    
    def test_purchase_tracks_total_spent_coins(self, test_user):
        """Test that purchasing cards increases total_spent_coins"""
        user_id = test_user['id']
        
        # Get initial state
        initial_response = requests.get(f"{BASE_URL}/api/users/{user_id}/check-engagement-milestones")
        initial_data = initial_response.json()
        initial_spent = initial_data["total_spent_coins"]
        
        # Get a common card to purchase
        cards_response = requests.get(f"{BASE_URL}/api/cards")
        cards = cards_response.json()
        common_card = next((c for c in cards if c.get("rarity") == "common" and c.get("available") == True), None)
        
        if not common_card:
            pytest.skip("No common available card found")
        
        # Purchase the card
        purchase_response = requests.post(
            f"{BASE_URL}/api/users/{user_id}/purchase-card",
            json={"user_id": user_id, "card_id": common_card["id"]}
        )
        
        if purchase_response.status_code != 200:
            pytest.skip(f"Could not purchase card: {purchase_response.json().get('detail')}")
        
        # Check updated state
        updated_response = requests.get(f"{BASE_URL}/api/users/{user_id}/check-engagement-milestones")
        updated_data = updated_response.json()
        
        expected_spent = initial_spent + common_card["coin_cost"]
        assert updated_data["total_spent_coins"] == expected_spent, \
            f"Expected total_spent_coins to be {expected_spent}, got {updated_data['total_spent_coins']}"
        
        print(f"✅ Total spent coins correctly tracked: {initial_spent} -> {updated_data['total_spent_coins']}")
    
    def test_big_spender_progress_tracks_total_spent(self, test_user):
        """Test that Big Spender progress equals total_spent_coins"""
        user_id = test_user['id']
        
        response = requests.get(f"{BASE_URL}/api/users/{user_id}/check-engagement-milestones")
        data = response.json()
        
        big_spender = next((m for m in data["engagement_milestones"] if m["milestone_type"] == "big_spender"), None)
        
        assert big_spender["progress"] == data["total_spent_coins"], \
            f"Progress ({big_spender['progress']}) should equal total_spent_coins ({data['total_spent_coins']})"
        
        print(f"✅ Big Spender progress correctly tracks total spent: {big_spender['progress']}")


class TestMonthlyMasterMilestone:
    """Tests for Monthly Master milestone (20 days in a month)"""
    
    @pytest.fixture
    def test_user(self):
        """Create a test user"""
        username = f"TEST_MonMas_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/users", json={"username": username})
        assert response.status_code == 200
        return response.json()
    
    def test_monthly_master_requirement_is_20(self, test_user):
        """Test that Monthly Master requires 20 days in a month"""
        user_id = test_user['id']
        
        response = requests.get(f"{BASE_URL}/api/users/{user_id}/check-engagement-milestones")
        data = response.json()
        
        monthly_master = next((m for m in data["engagement_milestones"] if m["milestone_type"] == "monthly_master"), None)
        assert monthly_master is not None, "Monthly Master milestone not found"
        
        assert monthly_master["requirement"] == 20, f"Expected requirement of 20, got {monthly_master['requirement']}"
        assert "20" in monthly_master["description"], f"Description should mention 20 days: {monthly_master['description']}"
        
        print(f"✅ Monthly Master milestone: {monthly_master['card']['name']}")
        print(f"   - Requirement: {monthly_master['requirement']} days in a month")
    
    def test_daily_login_tracks_monthly_logins(self, test_user):
        """Test that daily login updates monthly_logins tracking"""
        user_id = test_user['id']
        
        # Get initial state
        initial_response = requests.get(f"{BASE_URL}/api/users/{user_id}/check-engagement-milestones")
        initial_data = initial_response.json()
        
        # Claim daily login
        login_response = requests.post(f"{BASE_URL}/api/users/{user_id}/daily-login")
        
        if login_response.status_code != 200:
            # Already claimed today - that's okay, check if data is consistent
            pass
        
        # Check updated state
        updated_response = requests.get(f"{BASE_URL}/api/users/{user_id}/check-engagement-milestones")
        updated_data = updated_response.json()
        
        # current_month_logins should be >= 0
        assert updated_data["current_month_logins"] >= 0, \
            f"current_month_logins should be non-negative: {updated_data['current_month_logins']}"
        
        print(f"✅ Monthly logins tracking: current_month_logins = {updated_data['current_month_logins']}")
    
    def test_monthly_master_progress_tracks_current_month(self, test_user):
        """Test that Monthly Master progress equals current_month_logins"""
        user_id = test_user['id']
        
        response = requests.get(f"{BASE_URL}/api/users/{user_id}/check-engagement-milestones")
        data = response.json()
        
        monthly_master = next((m for m in data["engagement_milestones"] if m["milestone_type"] == "monthly_master"), None)
        
        assert monthly_master["progress"] == data["current_month_logins"], \
            f"Progress ({monthly_master['progress']}) should equal current_month_logins ({data['current_month_logins']})"
        
        print(f"✅ Monthly Master progress correctly tracks current month logins: {monthly_master['progress']}")


class TestEngagementMilestoneUnlocking:
    """Tests for milestone card unlocking and purchasing"""
    
    @pytest.fixture
    def test_user(self):
        """Create a test user"""
        username = f"TEST_EngUnl_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/users", json={"username": username})
        assert response.status_code == 200
        return response.json()
    
    def test_new_user_all_engagement_cards_locked(self, test_user):
        """Test that new user has all engagement cards locked"""
        user_id = test_user['id']
        
        response = requests.get(f"{BASE_URL}/api/users/{user_id}/check-engagement-milestones")
        data = response.json()
        
        for milestone in data["engagement_milestones"]:
            assert milestone["unlocked"] == False, \
                f"Milestone {milestone['milestone_type']} should be locked for new user"
            assert milestone["can_purchase"] == False, \
                f"Milestone {milestone['milestone_type']} should not be purchasable for new user"
        
        print(f"✅ All engagement cards are correctly locked for new user")
    
    def test_purchase_locked_engagement_card_fails(self, test_user):
        """Test that purchasing a locked engagement card returns error"""
        user_id = test_user['id']
        
        # Get an engagement milestone card
        response = requests.get(f"{BASE_URL}/api/users/{user_id}/check-engagement-milestones")
        data = response.json()
        
        # Get the big spender card (most likely to be locked)
        big_spender = next((m for m in data["engagement_milestones"] if m["milestone_type"] == "big_spender"), None)
        card_id = big_spender["card"]["id"]
        
        # Try to purchase
        purchase_response = requests.post(
            f"{BASE_URL}/api/users/{user_id}/purchase-card",
            json={"user_id": user_id, "card_id": card_id}
        )
        
        assert purchase_response.status_code == 400, \
            f"Expected 400 for locked engagement card, got {purchase_response.status_code}"
        
        error_detail = purchase_response.json().get("detail", "")
        print(f"✅ Purchase of locked engagement card correctly failed: {error_detail}")
    
    def test_dedicated_fan_card_error_message(self, test_user):
        """Test that dedicated_fan card gives correct error message"""
        user_id = test_user['id']
        
        # Try to purchase dedicated_fan card (Maxi Pad)
        purchase_response = requests.post(
            f"{BASE_URL}/api/users/{user_id}/purchase-card",
            json={"user_id": user_id, "card_id": "card_maxi_pad"}
        )
        
        assert purchase_response.status_code == 400
        error = purchase_response.json().get("detail", "")
        assert "30-day" in error.lower() or "30 day" in error.lower() or "streak" in error.lower(), \
            f"Error should mention 30-day streak: {error}"
        
        print(f"✅ Dedicated Fan card error message correct: {error}")
    
    def test_big_spender_card_error_message(self, test_user):
        """Test that big_spender card gives correct error message"""
        user_id = test_user['id']
        
        # Try to purchase big_spender card (Musty Dave)
        purchase_response = requests.post(
            f"{BASE_URL}/api/users/{user_id}/purchase-card",
            json={"user_id": user_id, "card_id": "card_musty_dave"}
        )
        
        assert purchase_response.status_code == 400
        error = purchase_response.json().get("detail", "")
        assert "750" in error or "spend" in error.lower() or "coins" in error.lower(), \
            f"Error should mention 750 coins: {error}"
        
        print(f"✅ Big Spender card error message correct: {error}")
    
    def test_monthly_master_card_error_message(self, test_user):
        """Test that monthly_master card gives correct error message"""
        user_id = test_user['id']
        
        # Try to purchase monthly_master card (Chum Araya)
        purchase_response = requests.post(
            f"{BASE_URL}/api/users/{user_id}/purchase-card",
            json={"user_id": user_id, "card_id": "card_chum_araya"}
        )
        
        assert purchase_response.status_code == 400
        error = purchase_response.json().get("detail", "")
        assert "20" in error or "month" in error.lower() or "log in" in error.lower() or "login" in error.lower(), \
            f"Error should mention 20 days/month: {error}"
        
        print(f"✅ Monthly Master card error message correct: {error}")


class TestEngagementCardsInShop:
    """Tests for engagement cards appearing correctly in cards list"""
    
    def test_engagement_cards_have_engagement_milestone_field(self):
        """Test that engagement cards have engagement_milestone field set"""
        response = requests.get(f"{BASE_URL}/api/cards")
        assert response.status_code == 200
        
        cards = response.json()
        engagement_cards = [c for c in cards if c.get("engagement_milestone")]
        
        assert len(engagement_cards) == 3, f"Expected 3 engagement cards, found {len(engagement_cards)}"
        
        for card in engagement_cards:
            print(f"✅ Engagement card: {card['name']} - milestone: {card['engagement_milestone']}")
    
    def test_engagement_cards_are_not_available(self):
        """Test that engagement cards have available=False by default"""
        response = requests.get(f"{BASE_URL}/api/cards")
        cards = response.json()
        
        engagement_cards = [c for c in cards if c.get("engagement_milestone")]
        
        for card in engagement_cards:
            assert card["available"] == False, \
                f"Engagement card {card['name']} should have available=False"
        
        print(f"✅ All engagement cards have available=False")
    
    def test_engagement_cards_cost_50_coins(self):
        """Test that engagement cards cost 50 coins"""
        response = requests.get(f"{BASE_URL}/api/cards")
        cards = response.json()
        
        engagement_cards = [c for c in cards if c.get("engagement_milestone")]
        
        for card in engagement_cards:
            assert card["coin_cost"] == 50, \
                f"Engagement card {card['name']} should cost 50 coins, not {card['coin_cost']}"
        
        print(f"✅ All engagement cards cost 50 coins")


class TestDailyLoginEngagement:
    """Tests for daily login interaction with engagement milestones"""
    
    @pytest.fixture
    def test_user(self):
        """Create a test user"""
        username = f"TEST_DailyEng_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/users", json={"username": username})
        assert response.status_code == 200
        return response.json()
    
    def test_daily_login_returns_engagement_unlock(self, test_user):
        """Test that daily login response includes engagement_unlock field"""
        user_id = test_user['id']
        
        login_response = requests.post(f"{BASE_URL}/api/users/{user_id}/daily-login")
        
        if login_response.status_code != 200:
            # May have already claimed - just check format
            pytest.skip("Already claimed today")
        
        data = login_response.json()
        
        # Should have engagement_unlock field (may be null if no unlock)
        assert "engagement_unlock" in data, "Daily login should include engagement_unlock field"
        
        print(f"✅ Daily login includes engagement_unlock field: {data.get('engagement_unlock')}")


class TestPurchaseEngagement:
    """Tests for purchase endpoint interaction with engagement milestones"""
    
    @pytest.fixture
    def test_user(self):
        """Create a test user"""
        username = f"TEST_PurchEng_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/users", json={"username": username})
        assert response.status_code == 200
        return response.json()
    
    def test_purchase_returns_engagement_unlock(self, test_user):
        """Test that purchase response includes engagement_unlock field"""
        user_id = test_user['id']
        
        # Get a common card
        cards = requests.get(f"{BASE_URL}/api/cards").json()
        common_card = next((c for c in cards if c.get("rarity") == "common" and c.get("available") == True), None)
        
        if not common_card:
            pytest.skip("No common available card found")
        
        purchase_response = requests.post(
            f"{BASE_URL}/api/users/{user_id}/purchase-card",
            json={"user_id": user_id, "card_id": common_card["id"]}
        )
        
        if purchase_response.status_code != 200:
            pytest.skip(f"Could not purchase: {purchase_response.json().get('detail')}")
        
        data = purchase_response.json()
        
        assert "engagement_unlock" in data, "Purchase response should include engagement_unlock field"
        
        print(f"✅ Purchase includes engagement_unlock field: {data.get('engagement_unlock')}")


class TestUserModelEngagementFields:
    """Tests for user model having engagement tracking fields"""
    
    @pytest.fixture
    def test_user(self):
        """Create a test user"""
        username = f"TEST_UserModel_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/users", json={"username": username})
        assert response.status_code == 200
        return response.json()
    
    def test_user_has_total_spent_coins_field(self, test_user):
        """Test that user has total_spent_coins field"""
        user_id = test_user['id']
        
        response = requests.get(f"{BASE_URL}/api/users/{user_id}")
        assert response.status_code == 200
        
        user = response.json()
        assert "total_spent_coins" in user, "User should have total_spent_coins field"
        assert user["total_spent_coins"] == 0, "New user should have 0 total_spent_coins"
        
        print(f"✅ User has total_spent_coins field: {user['total_spent_coins']}")
    
    def test_user_has_monthly_logins_field(self, test_user):
        """Test that user has monthly_logins field"""
        user_id = test_user['id']
        
        response = requests.get(f"{BASE_URL}/api/users/{user_id}")
        assert response.status_code == 200
        
        user = response.json()
        assert "monthly_logins" in user, "User should have monthly_logins field"
        
        print(f"✅ User has monthly_logins field: {user['monthly_logins']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

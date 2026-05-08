#!/usr/bin/env python3
"""
Rare Card Achievement System Test Suite
Tests the new rare card achievement APIs
"""

import requests
import json
import sys
from datetime import datetime

# Backend URL configuration
BACKEND_URL = "https://thrash-kan-kidz-1.preview.emergentagent.com/api"

class RareCardTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.test_results = []
        self.test_user_id = "87d119b4-edd6-4f8a-897c-9d93dafbd1ca"  # Provided user ID
        
    def log_test(self, test_name, success, details=""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL" 
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
    
    def create_test_user_if_needed(self):
        """Create or verify test user exists"""
        try:
            # First check if user already exists
            response = requests.get(f"{self.base_url}/users/{self.test_user_id}", timeout=10)
            if response.status_code == 200:
                user = response.json()
                self.log_test("Test User - User already exists", True, f"Username: {user.get('username', 'Unknown')}")
                return user
            
            # User doesn't exist, create new one with that ID or create new user
            user_data = {"username": "RareCardTester2024"}
            response = requests.post(f"{self.base_url}/users", json=user_data, timeout=10)
            
            if response.status_code == 200:
                user = response.json()
                self.test_user_id = user['id']  # Update to use the actual created user ID
                self.log_test("Test User - Created new user", True, f"User ID: {self.test_user_id}")
                return user
            else:
                self.log_test("Test User - Failed to create user", False, f"Status {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log_test("Test User - Connection error", False, str(e))
            return None
    
    def test_rare_cards_api(self):
        """Test GET /api/cards/rare endpoint"""
        print("\n=== Testing GET /api/cards/rare ===")
        
        try:
            response = requests.get(f"{self.base_url}/cards/rare", timeout=10)
            
            if response.status_code == 200:
                rare_cards = response.json()
                
                if len(rare_cards) == 2:
                    # Check for expected rare cards
                    card_names = [card['name'] for card in rare_cards]
                    expected_cards = ["Martin Van Druid", "Tardy Donald"]
                    
                    found_martin = "Martin Van Druid" in card_names
                    found_tardy = "Tardy Donald" in card_names
                    
                    if found_martin and found_tardy:
                        # Check achievement requirements
                        martin_card = next((c for c in rare_cards if c['name'] == "Martin Van Druid"), None)
                        tardy_card = next((c for c in rare_cards if c['name'] == "Tardy Donald"), None)
                        
                        martin_req = martin_card.get('achievement_required')
                        tardy_req = tardy_card.get('achievement_required')
                        
                        if martin_req == 10 and tardy_req == 20:
                            self.log_test("GET /api/cards/rare - Returns 2 rare cards with correct requirements", True, 
                                         f"Martin Van Druid: {martin_req} cards, Tardy Donald: {tardy_req} cards")
                            return rare_cards
                        else:
                            self.log_test("GET /api/cards/rare - Wrong achievement requirements", False, 
                                         f"Martin: {martin_req} (expected 10), Tardy: {tardy_req} (expected 20)")
                    else:
                        self.log_test("GET /api/cards/rare - Missing expected rare cards", False, 
                                     f"Found: {card_names}, Expected: {expected_cards}")
                else:
                    self.log_test("GET /api/cards/rare - Wrong number of rare cards", False, 
                                 f"Expected 2, got {len(rare_cards)}")
            else:
                self.log_test("GET /api/cards/rare - API Error", False, 
                             f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("GET /api/cards/rare - Connection Error", False, str(e))
            
        return None
    
    def test_check_rare_cards_api(self, user):
        """Test GET /api/users/{user_id}/check-rare-cards endpoint"""
        print("\n=== Testing GET /api/users/{user_id}/check-rare-cards ===")
        
        if not user:
            self.log_test("Check Rare Cards - No user provided", False, "Cannot test without user")
            return None
            
        try:
            response = requests.get(f"{self.base_url}/users/{self.test_user_id}/check-rare-cards", timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                
                # Check required fields
                required_fields = ['total_cards', 'rare_cards', 'newly_unlocked']
                missing_fields = [field for field in required_fields if field not in result]
                
                if not missing_fields:
                    total_cards = result['total_cards']
                    rare_cards = result['rare_cards']
                    newly_unlocked = result['newly_unlocked']
                    
                    # Validate rare_cards array structure
                    if isinstance(rare_cards, list) and len(rare_cards) == 2:
                        # Check structure of rare cards
                        card_fields = ['card', 'owned', 'required_cards', 'progress', 'can_unlock']
                        
                        valid_structure = True
                        for rare_card in rare_cards:
                            missing_card_fields = [field for field in card_fields if field not in rare_card]
                            if missing_card_fields:
                                valid_structure = False
                                break
                        
                        if valid_structure:
                            self.log_test("GET /api/users/{user_id}/check-rare-cards - Returns correct structure", True,
                                         f"Total cards: {total_cards}, Newly unlocked: {newly_unlocked is not None}")
                            return result
                        else:
                            self.log_test("GET /api/users/{user_id}/check-rare-cards - Invalid rare card structure", False,
                                         "Missing required fields in rare cards array")
                    else:
                        self.log_test("GET /api/users/{user_id}/check-rare-cards - Invalid rare_cards array", False,
                                     f"Expected array of 2, got {type(rare_cards)} with length {len(rare_cards) if isinstance(rare_cards, list) else 'N/A'}")
                else:
                    self.log_test("GET /api/users/{user_id}/check-rare-cards - Missing required fields", False,
                                 f"Missing: {missing_fields}")
            else:
                self.log_test("GET /api/users/{user_id}/check-rare-cards - API Error", False,
                             f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("GET /api/users/{user_id}/check-rare-cards - Connection Error", False, str(e))
            
        return None
    
    def give_user_coins_via_daily_login(self, user):
        """Give user enough coins to purchase cards by claiming daily login"""
        try:
            # Multiple daily logins to get enough coins (need to purchase many cards)
            for i in range(5):  # Try multiple times in case of streak bonuses
                response = requests.post(f"{self.base_url}/users/{self.test_user_id}/daily-login", timeout=10)
                if response.status_code == 400:  # Already claimed today
                    break
                elif response.status_code == 200:
                    result = response.json()
                    print(f"   Daily login successful: +{result.get('bonus_coins', 0)} coins")
            
            # Check final coin balance
            response = requests.get(f"{self.base_url}/users/{self.test_user_id}", timeout=10)
            if response.status_code == 200:
                updated_user = response.json()
                self.log_test("Daily Login - Get coins for testing", True, 
                             f"User now has {updated_user.get('coins', 0)} coins")
                return updated_user
            else:
                self.log_test("Daily Login - Cannot get updated user", False)
                return user
                
        except Exception as e:
            self.log_test("Daily Login - Error", False, str(e))
            return user
    
    def purchase_cards_to_test_achievements(self, user):
        """Purchase cards to test rare card achievements"""
        print("\n=== Purchasing Cards to Test Achievements ===")
        
        if not user:
            self.log_test("Purchase Cards - No user provided", False)
            return user
        
        try:
            # Get all available cards first
            response = requests.get(f"{self.base_url}/cards", timeout=10)
            if response.status_code != 200:
                self.log_test("Purchase Cards - Cannot get cards list", False)
                return user
            
            all_cards = response.json()
            # Filter for purchasable cards (available = True)
            purchasable_cards = [card for card in all_cards if card.get('available', False)]
            
            cards_purchased = 0
            target_cards = 12  # Purchase enough to unlock Martin Van Druid (10 cards) and test progress
            
            for i in range(target_cards):
                if cards_purchased >= len(purchasable_cards):
                    # We've bought all types, buy duplicates
                    card_to_buy = purchasable_cards[i % len(purchasable_cards)]
                else:
                    card_to_buy = purchasable_cards[i % len(purchasable_cards)]
                
                purchase_data = {
                    "user_id": self.test_user_id,
                    "card_id": card_to_buy['id']
                }
                
                response = requests.post(f"{self.base_url}/users/{self.test_user_id}/purchase-card", 
                                       json=purchase_data, timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    cards_purchased += 1
                    
                    # Check if newly_unlocked_rare_card is in response
                    newly_unlocked = result.get('newly_unlocked_rare_card')
                    if newly_unlocked:
                        print(f"   ✨ RARE CARD UNLOCKED: {newly_unlocked.get('name', 'Unknown')}")
                        
                    print(f"   Purchased {card_to_buy['name']} (#{cards_purchased}) - Remaining coins: {result.get('remaining_coins', 0)}")
                    
                    if cards_purchased >= 10:
                        # Should have unlocked Martin Van Druid
                        break
                else:
                    if response.status_code == 400 and "Not enough coins" in response.text:
                        print(f"   Ran out of coins after purchasing {cards_purchased} cards")
                        break
                    else:
                        print(f"   Error purchasing card: {response.status_code} - {response.text}")
                        break
            
            self.log_test("Purchase Cards - Bought cards for testing", True, 
                         f"Purchased {cards_purchased} cards")
            
            # Get updated user
            response = requests.get(f"{self.base_url}/users/{self.test_user_id}", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                return user
                
        except Exception as e:
            self.log_test("Purchase Cards - Error", False, str(e))
            return user
    
    def test_purchase_with_rare_unlock(self, user):
        """Test that purchase endpoint returns newly_unlocked_rare_card field"""
        print("\n=== Testing Purchase Endpoint Rare Card Field ===")
        
        try:
            # Get purchasable cards
            response = requests.get(f"{self.base_url}/cards", timeout=10)
            if response.status_code != 200:
                self.log_test("Purchase Test - Cannot get cards", False)
                return
            
            cards = response.json()
            purchasable_card = None
            for card in cards:
                if card.get('available', False):
                    purchasable_card = card
                    break
            
            if not purchasable_card:
                self.log_test("Purchase Test - No purchasable cards found", False)
                return
            
            # Make a purchase
            purchase_data = {
                "user_id": self.test_user_id,
                "card_id": purchasable_card['id']
            }
            
            response = requests.post(f"{self.base_url}/users/{self.test_user_id}/purchase-card", 
                                   json=purchase_data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                
                # Check for required fields including newly_unlocked_rare_card
                required_fields = ['success', 'remaining_coins', 'card', 'newly_unlocked_rare_card']
                missing_fields = [field for field in required_fields if field not in result]
                
                if not missing_fields:
                    newly_unlocked = result['newly_unlocked_rare_card']
                    self.log_test("POST /api/users/{user_id}/purchase-card - Returns newly_unlocked_rare_card field", True,
                                 f"Newly unlocked: {newly_unlocked.get('name') if newly_unlocked else None}")
                else:
                    self.log_test("POST /api/users/{user_id}/purchase-card - Missing required fields", False,
                                 f"Missing: {missing_fields}")
            else:
                self.log_test("POST /api/users/{user_id}/purchase-card - API Error", False,
                             f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("POST /api/users/{user_id}/purchase-card - Error", False, str(e))
    
    def run_rare_card_tests(self):
        """Run all rare card achievement tests"""
        print("🏆 Starting Rare Card Achievement System Test Suite")
        print(f"Testing backend at: {self.base_url}")
        print(f"Using user ID: {self.test_user_id}")
        
        # Test 1: Create/verify test user
        user = self.create_test_user_if_needed()
        
        # Test 2: GET /api/cards/rare
        rare_cards = self.test_rare_cards_api()
        
        # Test 3: Give user coins for purchasing cards  
        if user:
            user = self.give_user_coins_via_daily_login(user)
        
        # Test 4: Test check rare cards API (initial state)
        if user:
            initial_check = self.test_check_rare_cards_api(user)
        
        # Test 5: Purchase cards to trigger achievements
        if user:
            user = self.purchase_cards_to_test_achievements(user)
        
        # Test 6: Test check rare cards API (after purchases)
        if user:
            final_check = self.test_check_rare_cards_api(user)
        
        # Test 7: Test purchase endpoint returns rare card field
        if user:
            self.test_purchase_with_rare_unlock(user)
        
        # Summary
        print("\n" + "="*60)
        print("🏆 RARE CARD TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total*100):.1f}%" if total > 0 else "No tests run")
        
        # Show failed tests
        failed_tests = [result for result in self.test_results if not result['success']]
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   - {test['test']}")
                if test['details']:
                    print(f"     {test['details']}")
        else:
            print("\n🎉 ALL RARE CARD TESTS PASSED!")
        
        print(f"\nTest completed at: {datetime.now()}")
        
        return len(failed_tests) == 0

if __name__ == "__main__":
    tester = RareCardTester()
    success = tester.run_rare_card_tests()
    sys.exit(0 if success else 1)
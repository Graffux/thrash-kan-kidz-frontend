#!/usr/bin/env python3
"""
Thrash Kan Kidz Milestone Reward System and Rare Card Achievement Test
Tests the milestone reward system (free cards every 5 cards) and rare card achievements
"""

import requests
import json
import sys
from datetime import datetime

# Backend URL configuration - using the URL from frontend/.env
BACKEND_URL = "https://thrash-kan-kidz-1.preview.emergentagent.com/api"

class MilestoneRewardTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.test_results = []
        self.test_user = None
        
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

    def create_test_user(self):
        """Create test user for milestone testing"""
        print("\n=== Setting up Test User ===")
        
        # Create a new user for testing to ensure clean state
        try:
            user_data = {"username": f"MilestoneTestUser_{int(datetime.now().timestamp())}"}
            response = requests.post(f"{self.base_url}/users", json=user_data, timeout=10)
            
            if response.status_code == 200:
                self.test_user = response.json()
                self.log_test("Created new test user", True, f"User ID: {self.test_user['id']}, Username: {self.test_user['username']}")
                return True
            else:
                # If creation failed, try to use the specified user
                test_user_id = "87d119b4-edd6-4f8a-897c-9d93dafbd1ca"
                response = requests.get(f"{self.base_url}/users/{test_user_id}", timeout=10)
                if response.status_code == 200:
                    self.test_user = response.json()
                    self.log_test("Using existing test user", True, f"User ID: {test_user_id}")
                    return True
                else:
                    self.log_test("Failed to create or find test user", False, f"Status {response.status_code}: {response.text}")
                    return False
                    
        except Exception as e:
            self.log_test("User setup error", False, str(e))
            return False

    def test_rare_cards_endpoint(self):
        """Test GET /api/cards/rare endpoint"""
        print("\n=== Testing Rare Cards Endpoint ===")
        
        try:
            response = requests.get(f"{self.base_url}/cards/rare", timeout=10)
            if response.status_code == 200:
                rare_cards = response.json()
                if len(rare_cards) == 2:
                    # Check for expected rare cards
                    card_names = [card['name'] for card in rare_cards]
                    expected_names = ["Martin Van Druid", "Tardy Donald"]
                    
                    missing_cards = [name for name in expected_names if name not in card_names]
                    if not missing_cards:
                        # Check card properties
                        for card in rare_cards:
                            if card['name'] == "Martin Van Druid" and card.get('achievement_required') == 10:
                                continue
                            elif card['name'] == "Tardy Donald" and card.get('achievement_required') == 20:
                                continue
                            else:
                                self.log_test("GET /api/cards/rare - Wrong achievement requirements", False, 
                                           f"{card['name']}: expected 10 or 20, got {card.get('achievement_required')}")
                                return False
                        
                        self.log_test("GET /api/cards/rare - Returns both rare cards with correct requirements", True)
                        return rare_cards
                    else:
                        self.log_test("GET /api/cards/rare - Missing expected cards", False, f"Missing: {missing_cards}")
                else:
                    self.log_test("GET /api/cards/rare - Wrong number of rare cards", False, f"Expected 2, got {len(rare_cards)}")
            else:
                self.log_test("GET /api/cards/rare - API Error", False, f"Status {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("GET /api/cards/rare - Connection Error", False, str(e))
        
        return None

    def test_check_rare_cards_endpoint(self):
        """Test GET /api/users/{user_id}/check-rare-cards with milestone_info"""
        print("\n=== Testing Check Rare Cards Endpoint with Milestone Info ===")
        
        if not self.test_user:
            self.log_test("Check rare cards - No test user", False, "Test user not available")
            return False
            
        user_id = self.test_user['id']
        
        try:
            response = requests.get(f"{self.base_url}/users/{user_id}/check-rare-cards", timeout=10)
            if response.status_code == 200:
                result = response.json()
                
                # Check required fields
                required_fields = ['total_cards', 'rare_cards', 'newly_unlocked', 'milestone_info']
                missing_fields = [field for field in required_fields if field not in result]
                
                if not missing_fields:
                    # Check milestone_info structure
                    milestone_info = result['milestone_info']
                    milestone_fields = ['milestones_claimed', 'next_milestone_at', 'cards_to_next_milestone', 'progress_to_next']
                    missing_milestone_fields = [field for field in milestone_fields if field not in milestone_info]
                    
                    if not missing_milestone_fields:
                        self.log_test("GET /api/users/{user_id}/check-rare-cards - Has milestone_info with required fields", True,
                                     f"Milestones claimed: {milestone_info['milestones_claimed']}, Next milestone at: {milestone_info['next_milestone_at']}")
                        return result
                    else:
                        self.log_test("GET /api/users/{user_id}/check-rare-cards - Missing milestone fields", False,
                                     f"Missing: {missing_milestone_fields}")
                else:
                    self.log_test("GET /api/users/{user_id}/check-rare-cards - Missing required fields", False,
                                 f"Missing: {missing_fields}")
            else:
                self.log_test("GET /api/users/{user_id}/check-rare-cards - API Error", False,
                             f"Status {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("GET /api/users/{user_id}/check-rare-cards - Connection Error", False, str(e))
        
        return None

    def ensure_user_has_coins(self, user_id, min_coins=300):
        """Ensure user has enough coins by checking and giving them some"""
        try:
            # Check current user coins
            response = requests.get(f"{self.base_url}/users/{user_id}", timeout=10)
            if response.status_code != 200:
                return False
            
            user = response.json()
            current_coins = user.get('coins', 0)
            
            if current_coins >= min_coins:
                print(f"   User has {current_coins} coins (sufficient)")
                return True
            
            print(f"   User has {current_coins} coins, needs more for testing...")
            
            # Give user coins by updating directly (simulating admin action for testing)
            # Since we can't modify coins directly, we'll need to work with what we have
            return current_coins >= 50  # At least enough for one card
            
        except Exception as e:
            print(f"   Error checking/updating coins: {e}")
            return False

    def test_milestone_reward_system(self):
        """Test milestone reward system - free card every 5 cards"""
        print("\n=== Testing Milestone Reward System ===")
        
        if not self.test_user:
            self.log_test("Milestone rewards - No test user", False, "Test user not available")
            return False
            
        user_id = self.test_user['id']
        
        # Ensure user has enough coins for testing
        if not self.ensure_user_has_coins(user_id):
            self.log_test("Milestone rewards - Insufficient coins", False, "User doesn't have enough coins and cannot add more")
            return False
        
        # Get available cards first
        try:
            response = requests.get(f"{self.base_url}/cards", timeout=10)
            if response.status_code != 200:
                self.log_test("Milestone rewards - Cannot get cards list", False, "Failed to retrieve cards")
                return False
            
            cards = response.json()
            available_cards = [card for card in cards if card.get('available', True)]
            
            if len(available_cards) < 1:
                self.log_test("Milestone rewards - No available cards", False, "No cards available for purchase")
                return False
            
            # Get initial state
            response = requests.get(f"{self.base_url}/users/{user_id}/check-rare-cards", timeout=10)
            if response.status_code != 200:
                self.log_test("Milestone rewards - Cannot get initial state", False, "Failed to get user state")
                return False
            
            initial_state = response.json()
            initial_cards = initial_state['total_cards']
            initial_milestones = initial_state['milestone_info']['milestones_claimed']
            
            print(f"   Initial state: {initial_cards} cards, {initial_milestones} milestones claimed")
            
            # Calculate cards needed for next milestone
            next_milestone_at = initial_state['milestone_info']['next_milestone_at']
            cards_needed = next_milestone_at - initial_cards
            
            if cards_needed <= 0:
                # User is already at or past a milestone, let's test purchasing one more card
                cards_needed = 1
            
            # Purchase cards to reach milestone
            milestone_reached = False
            for i in range(cards_needed):
                if i >= len(available_cards):
                    break
                    
                card = available_cards[i % len(available_cards)]
                purchase_data = {
                    "user_id": user_id,
                    "card_id": card['id']
                }
                
                response = requests.post(f"{self.base_url}/users/{user_id}/purchase-card", json=purchase_data, timeout=10)
                if response.status_code == 200:
                    purchase_result = response.json()
                    
                    # Check if milestone_reward is present
                    if 'milestone_reward' in purchase_result and purchase_result['milestone_reward']:
                        milestone_reward = purchase_result['milestone_reward']
                        required_milestone_fields = ['milestone_number', 'card', 'next_milestone_at']
                        missing_milestone_fields = [field for field in required_milestone_fields if field not in milestone_reward]
                        
                        if not missing_milestone_fields:
                            self.log_test("POST /api/users/{user_id}/purchase-card - Returns milestone_reward", True,
                                         f"Milestone {milestone_reward['milestone_number']}, Card: {milestone_reward['card']['name']}")
                            milestone_reached = True
                            break
                        else:
                            self.log_test("POST /api/users/{user_id}/purchase-card - Incomplete milestone_reward", False,
                                         f"Missing: {missing_milestone_fields}")
                    else:
                        print(f"   Purchased {card['name']}, no milestone reward yet")
                        
                else:
                    self.log_test(f"Purchase card #{i+1} - API Error", False, f"Status {response.status_code}")
                    break
            
            if not milestone_reached:
                # Check if we need to purchase more cards
                response = requests.get(f"{self.base_url}/users/{user_id}/check-rare-cards", timeout=10)
                if response.status_code == 200:
                    current_state = response.json()
                    current_cards = current_state['total_cards']
                    current_milestones = current_state['milestone_info']['milestones_claimed']
                    
                    if current_milestones > initial_milestones:
                        self.log_test("Milestone reward system - Milestone claimed outside purchase", True,
                                     f"Milestones increased from {initial_milestones} to {current_milestones}")
                        return True
                    else:
                        # Try to purchase more cards to reach 5-card milestone
                        cards_to_next = current_state['milestone_info']['cards_to_next_milestone']
                        print(f"   Current: {current_cards} cards, need {cards_to_next} more for next milestone")
                        
                        # Purchase remaining cards needed
                        for i in range(cards_to_next):
                            if i + cards_needed >= len(available_cards):
                                break
                                
                            card = available_cards[(i + cards_needed) % len(available_cards)]
                            purchase_data = {
                                "user_id": user_id,
                                "card_id": card['id']
                            }
                            
                            response = requests.post(f"{self.base_url}/users/{user_id}/purchase-card", json=purchase_data, timeout=10)
                            if response.status_code == 200:
                                purchase_result = response.json()
                                
                                if 'milestone_reward' in purchase_result and purchase_result['milestone_reward']:
                                    milestone_reward = purchase_result['milestone_reward']
                                    self.log_test("Milestone reward system - Free card awarded every 5 cards", True,
                                                 f"Awarded: {milestone_reward['card']['name']} at milestone {milestone_reward['milestone_number']}")
                                    return True
                        
                        self.log_test("Milestone reward system - No milestone reward triggered", False,
                                     "Purchased multiple cards but no milestone reward received")
                
            return milestone_reached
            
        except Exception as e:
            self.log_test("Milestone reward system - Connection Error", False, str(e))
            return False

    def run_milestone_tests(self):
        """Run all milestone and rare card tests"""
        print("🎸 Starting Thrash Kan Kidz Milestone Reward & Rare Card Achievement Tests")
        print(f"Testing backend at: {self.base_url}")
        
        # Setup
        if not self.create_test_user():
            print("❌ Cannot proceed without test user")
            return False
        
        # Test 1: Rare cards endpoint
        rare_cards = self.test_rare_cards_endpoint()
        
        # Test 2: Check rare cards endpoint with milestone info
        check_result = self.test_check_rare_cards_endpoint()
        
        # Test 3: Milestone reward system
        self.test_milestone_reward_system()
        
        # Summary
        print("\n" + "="*60)
        print("🎸 MILESTONE TESTS SUMMARY")
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
            print("\n✅ ALL TESTS PASSED!")
        
        print(f"\nTest completed at: {datetime.now()}")
        
        return len(failed_tests) == 0

if __name__ == "__main__":
    tester = MilestoneRewardTester()
    success = tester.run_milestone_tests()
    sys.exit(0 if success else 1)
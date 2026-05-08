#!/usr/bin/env python3
"""
Thrash Kan Kidz Backend API Test Suite
Tests all backend endpoints following the complete user flow
"""

import requests
import json
import sys
from datetime import datetime, timedelta

# Backend URL configuration
BACKEND_URL = "https://thrash-kan-kidz-1.preview.emergentagent.com/api"

class APITester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.test_users = []
        self.test_results = []
        
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
        
    def test_cards_api(self):
        """Test Cards API endpoints"""
        print("\n=== Testing Cards API ===")
        
        # Test GET /api/cards
        try:
            response = requests.get(f"{self.base_url}/cards", timeout=10)
            if response.status_code == 200:
                cards = response.json()
                if len(cards) == 5:
                    # Check required cards exist
                    card_names = [card['name'] for card in cards]
                    expected_cards = ["Silly Mille", "Cliff Burpin", "Scotch Ian", "Chuck Roast", "Scott Eaten"]
                    
                    missing_cards = [name for name in expected_cards if name not in card_names]
                    if not missing_cards:
                        # Check card structure
                        card = cards[0]
                        required_fields = ['id', 'name', 'description', 'rarity', 'front_image_url', 'coin_cost']
                        missing_fields = [field for field in required_fields if field not in card]
                        
                        if not missing_fields:
                            # Check rarities
                            rarities = {card['name']: card['rarity'] for card in cards}
                            expected_rarities = {
                                "Silly Mille": "common",
                                "Cliff Burpin": "common", 
                                "Scotch Ian": "rare",
                                "Chuck Roast": "rare",
                                "Scott Eaten": "epic"
                            }
                            
                            wrong_rarities = []
                            for name, expected_rarity in expected_rarities.items():
                                if rarities.get(name) != expected_rarity:
                                    wrong_rarities.append(f"{name}: expected {expected_rarity}, got {rarities.get(name)}")
                            
                            if not wrong_rarities:
                                self.log_test("GET /api/cards - Returns 5 cards with correct structure and rarities", True)
                                return cards
                            else:
                                self.log_test("GET /api/cards - Wrong rarities", False, f"Wrong rarities: {wrong_rarities}")
                        else:
                            self.log_test("GET /api/cards - Missing required fields", False, f"Missing: {missing_fields}")
                    else:
                        self.log_test("GET /api/cards - Missing expected cards", False, f"Missing: {missing_cards}")
                else:
                    self.log_test("GET /api/cards - Wrong number of cards", False, f"Expected 5, got {len(cards)}")
            else:
                self.log_test("GET /api/cards - API Error", False, f"Status {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("GET /api/cards - Connection Error", False, str(e))
            return None
            
        return None
    
    def test_user_management(self):
        """Test User Management API"""
        print("\n=== Testing User Management API ===")
        
        # Create test user 1
        try:
            user_data = {"username": "MetalHead2024"}
            response = requests.post(f"{self.base_url}/users", json=user_data, timeout=10)
            
            if response.status_code == 200:
                user1 = response.json()
                if user1.get('username') == "MetalHead2024" and 'id' in user1:
                    self.test_users.append(user1)
                    self.log_test("POST /api/users - Create user", True, f"Created user: {user1['username']}")
                    
                    # Test GET /api/users/{user_id}
                    user_id = user1['id']
                    response = requests.get(f"{self.base_url}/users/{user_id}", timeout=10)
                    if response.status_code == 200:
                        retrieved_user = response.json()
                        if retrieved_user['id'] == user_id:
                            self.log_test("GET /api/users/{user_id} - Get user by ID", True)
                        else:
                            self.log_test("GET /api/users/{user_id} - Wrong user returned", False)
                    else:
                        self.log_test("GET /api/users/{user_id} - API Error", False, f"Status {response.status_code}")
                    
                    # Test GET /api/users/username/{username}
                    response = requests.get(f"{self.base_url}/users/username/MetalHead2024", timeout=10)
                    if response.status_code == 200:
                        retrieved_user = response.json()
                        if retrieved_user['username'] == "MetalHead2024":
                            self.log_test("GET /api/users/username/{username} - Get user by username", True)
                        else:
                            self.log_test("GET /api/users/username/{username} - Wrong user returned", False)
                    else:
                        self.log_test("GET /api/users/username/{username} - API Error", False, f"Status {response.status_code}")
                    
                    # Test PUT /api/users/{user_id}/profile
                    profile_data = {"bio": "I love collecting thrash metal cards!"}
                    response = requests.put(f"{self.base_url}/users/{user_id}/profile", json=profile_data, timeout=10)
                    if response.status_code == 200:
                        updated_user = response.json()
                        if updated_user.get('bio') == "I love collecting thrash metal cards!":
                            self.log_test("PUT /api/users/{user_id}/profile - Update profile", True)
                            return user1
                        else:
                            self.log_test("PUT /api/users/{user_id}/profile - Bio not updated", False)
                    else:
                        self.log_test("PUT /api/users/{user_id}/profile - API Error", False, f"Status {response.status_code}")
                    
                else:
                    self.log_test("POST /api/users - Invalid user data", False, "Missing username or id in response")
            else:
                self.log_test("POST /api/users - API Error", False, f"Status {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("POST /api/users - Connection Error", False, str(e))
            
        return None
    
    def test_daily_login_system(self, user):
        """Test Daily Login System"""
        print("\n=== Testing Daily Login System ===")
        
        if not user:
            self.log_test("Daily Login - No user provided", False, "Cannot test without user")
            return
            
        user_id = user['id']
        
        # Test first daily login
        try:
            response = requests.post(f"{self.base_url}/users/{user_id}/daily-login", timeout=10)
            if response.status_code == 200:
                login_result = response.json()
                required_fields = ['streak', 'bonus_coins', 'total_coins', 'message']
                missing_fields = [field for field in required_fields if field not in login_result]
                
                if not missing_fields:
                    if login_result['streak'] >= 1 and login_result['bonus_coins'] > 0:
                        self.log_test("POST /api/users/{user_id}/daily-login - First claim", True, 
                                     f"Streak: {login_result['streak']}, Coins: +{login_result['bonus_coins']}")
                        
                        # Test claiming again same day (should fail)
                        response = requests.post(f"{self.base_url}/users/{user_id}/daily-login", timeout=10)
                        if response.status_code == 400:
                            error_msg = response.json().get('detail', '')
                            if "Already claimed today" in error_msg:
                                self.log_test("POST /api/users/{user_id}/daily-login - Duplicate claim prevention", True)
                                return True
                            else:
                                self.log_test("POST /api/users/{user_id}/daily-login - Wrong error message", False, error_msg)
                        else:
                            self.log_test("POST /api/users/{user_id}/daily-login - Should prevent duplicate claim", False, 
                                         f"Expected 400, got {response.status_code}")
                    else:
                        self.log_test("POST /api/users/{user_id}/daily-login - Invalid values", False, 
                                     f"Streak: {login_result['streak']}, Coins: {login_result['bonus_coins']}")
                else:
                    self.log_test("POST /api/users/{user_id}/daily-login - Missing fields", False, f"Missing: {missing_fields}")
            else:
                self.log_test("POST /api/users/{user_id}/daily-login - API Error", False, f"Status {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("POST /api/users/{user_id}/daily-login - Connection Error", False, str(e))
            
        return False
    
    def test_card_purchase(self, user, cards):
        """Test Card Purchase System"""
        print("\n=== Testing Card Purchase System ===")
        
        if not user or not cards:
            self.log_test("Card Purchase - Missing prerequisites", False, "Need user and cards data")
            return False
            
        user_id = user['id']
        # Test purchasing Silly Mille (should be 50 coins)
        silly_mille_card = None
        for card in cards:
            if card['name'] == "Silly Mille":
                silly_mille_card = card
                break
                
        if not silly_mille_card:
            self.log_test("Card Purchase - Silly Mille card not found", False)
            return False
            
        # Test purchase
        try:
            purchase_data = {
                "user_id": user_id,
                "card_id": silly_mille_card['id']
            }
            response = requests.post(f"{self.base_url}/users/{user_id}/purchase-card", json=purchase_data, timeout=10)
            
            if response.status_code == 200:
                purchase_result = response.json()
                required_fields = ['success', 'remaining_coins', 'card']
                missing_fields = [field for field in required_fields if field not in purchase_result]
                
                if not missing_fields:
                    if purchase_result['success'] and purchase_result['card']['name'] == "Silly Mille":
                        self.log_test("POST /api/users/{user_id}/purchase-card - Purchase Silly Mille", True,
                                     f"Remaining coins: {purchase_result['remaining_coins']}")
                        
                        # Test GET /api/users/{user_id}/cards
                        response = requests.get(f"{self.base_url}/users/{user_id}/cards", timeout=10)
                        if response.status_code == 200:
                            user_cards = response.json()
                            if len(user_cards) > 0:
                                found_card = False
                                for user_card in user_cards:
                                    if user_card['card']['name'] == "Silly Mille":
                                        found_card = True
                                        break
                                
                                if found_card:
                                    self.log_test("GET /api/users/{user_id}/cards - Shows purchased card", True)
                                    return True
                                else:
                                    self.log_test("GET /api/users/{user_id}/cards - Purchased card not in collection", False)
                            else:
                                self.log_test("GET /api/users/{user_id}/cards - Empty collection after purchase", False)
                        else:
                            self.log_test("GET /api/users/{user_id}/cards - API Error", False, f"Status {response.status_code}")
                    else:
                        self.log_test("POST /api/users/{user_id}/purchase-card - Invalid response", False, "Success false or wrong card")
                else:
                    self.log_test("POST /api/users/{user_id}/purchase-card - Missing fields", False, f"Missing: {missing_fields}")
            else:
                self.log_test("POST /api/users/{user_id}/purchase-card - API Error", False, f"Status {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("POST /api/users/{user_id}/purchase-card - Connection Error", False, str(e))
            
        return False
    
    def test_goals_system(self, user):
        """Test Goals System"""
        print("\n=== Testing Goals System ===")
        
        # Test GET /api/goals
        try:
            response = requests.get(f"{self.base_url}/goals", timeout=10)
            if response.status_code == 200:
                goals = response.json()
                if len(goals) == 6:
                    self.log_test("GET /api/goals - Returns 6 goals", True)
                    
                    # Test GET /api/users/{user_id}/goals
                    if user:
                        user_id = user['id']
                        response = requests.get(f"{self.base_url}/users/{user_id}/goals", timeout=10)
                        if response.status_code == 200:
                            user_goals = response.json()
                            if len(user_goals) > 0:
                                # Check structure
                                user_goal = user_goals[0]
                                if 'user_goal' in user_goal and 'goal' in user_goal:
                                    self.log_test("GET /api/users/{user_id}/goals - Returns user goal progress", True,
                                                 f"Found {len(user_goals)} user goals")
                                    return True
                                else:
                                    self.log_test("GET /api/users/{user_id}/goals - Invalid structure", False, "Missing user_goal or goal fields")
                            else:
                                self.log_test("GET /api/users/{user_id}/goals - Empty user goals", False)
                        else:
                            self.log_test("GET /api/users/{user_id}/goals - API Error", False, f"Status {response.status_code}")
                    else:
                        self.log_test("GET /api/users/{user_id}/goals - No user provided", False)
                else:
                    self.log_test("GET /api/goals - Wrong number of goals", False, f"Expected 6, got {len(goals)}")
            else:
                self.log_test("GET /api/goals - API Error", False, f"Status {response.status_code}: {response.text}")
        except Exception as e:
            self.log_test("GET /api/goals - Connection Error", False, str(e))
            
        return False
    
    def test_trading_system(self, cards):
        """Test Trading System"""
        print("\n=== Testing Trading System ===")
        
        # Create second user for trading
        try:
            user2_data = {"username": "ThrashCollector2024"}
            response = requests.post(f"{self.base_url}/users", json=user2_data, timeout=10)
            
            if response.status_code != 200:
                self.log_test("Trading - Cannot create second user", False, f"Status {response.status_code}")
                return False
                
            user2 = response.json()
            self.test_users.append(user2)
            
            # Both users need cards to trade
            if len(self.test_users) < 2 or not cards:
                self.log_test("Trading - Insufficient test data", False, "Need 2 users and cards")
                return False
                
            user1 = self.test_users[0]
            user1_id = user1['id']
            user2_id = user2['id']
            
            # Give user2 some cards to trade (buy Cliff Burpin)
            cliff_card = None
            for card in cards:
                if card['name'] == "Cliff Burpin":
                    cliff_card = card
                    break
                    
            if not cliff_card:
                self.log_test("Trading - Cliff Burpin card not found", False)
                return False
                
            # User2 buys Cliff Burpin 
            purchase_data = {"user_id": user2_id, "card_id": cliff_card['id']}
            response = requests.post(f"{self.base_url}/users/{user2_id}/purchase-card", json=purchase_data, timeout=10)
            if response.status_code != 200:
                self.log_test("Trading - User2 cannot purchase card", False, f"Status {response.status_code}")
                return False
            
            # Create trade: User1 offers Silly Mille for User2's Cliff Burpin
            silly_card = None
            for card in cards:
                if card['name'] == "Silly Mille":
                    silly_card = card
                    break
                    
            if not silly_card:
                self.log_test("Trading - Silly Mille card not found", False)
                return False
                
            trade_data = {
                "from_user_id": user1_id,
                "to_user_id": user2_id,
                "offered_card_ids": [silly_card['id']],
                "requested_card_ids": [cliff_card['id']]
            }
            
            response = requests.post(f"{self.base_url}/trades", json=trade_data, timeout=10)
            if response.status_code == 200:
                trade = response.json()
                if 'id' in trade and trade.get('status') == 'pending':
                    self.log_test("POST /api/trades - Create trade offer", True, f"Trade ID: {trade['id']}")
                    
                    # Test trade acceptance
                    trade_id = trade['id']
                    action_data = {
                        "trade_id": trade_id,
                        "user_id": user2_id,
                        "action": "accept"
                    }
                    
                    response = requests.post(f"{self.base_url}/trades/{trade_id}/action", json=action_data, timeout=10)
                    if response.status_code == 200:
                        action_result = response.json()
                        if action_result.get('success') and "completed" in action_result.get('message', '').lower():
                            self.log_test("POST /api/trades/{trade_id}/action - Accept trade", True)
                            return True
                        else:
                            self.log_test("POST /api/trades/{trade_id}/action - Trade not completed", False, action_result.get('message'))
                    else:
                        self.log_test("POST /api/trades/{trade_id}/action - API Error", False, f"Status {response.status_code}: {response.text}")
                else:
                    self.log_test("POST /api/trades - Invalid trade response", False, "Missing ID or wrong status")
            else:
                self.log_test("POST /api/trades - API Error", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Trading System - Connection Error", False, str(e))
            
        return False
    
    def run_all_tests(self):
        """Run the complete test suite following user flow"""
        print("🎸 Starting Thrash Kan Kidz Backend API Test Suite")
        print(f"Testing backend at: {self.base_url}")
        
        # Test 1: Cards API
        cards = self.test_cards_api()
        
        # Test 2: User Management
        user = self.test_user_management()
        
        # Test 3: Daily Login System
        if user:
            self.test_daily_login_system(user)
        
        # Test 4: Card Purchase
        if user and cards:
            self.test_card_purchase(user, cards)
        
        # Test 5: Goals System  
        self.test_goals_system(user)
        
        # Test 6: Trading System
        if cards:
            self.test_trading_system(cards)
        
        # Summary
        print("\n" + "="*60)
        print("🎸 TEST SUMMARY")
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
        
        print(f"\nTest completed at: {datetime.now()}")
        
        return len(failed_tests) == 0

if __name__ == "__main__":
    tester = APITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
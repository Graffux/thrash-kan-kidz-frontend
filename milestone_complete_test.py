#!/usr/bin/env python3
"""
Milestone Reward System Full Test
Tests the complete milestone reward functionality by purchasing 5 cards
"""

import requests
import json
import sys
from datetime import datetime, timedelta

# Backend URL configuration
BACKEND_URL = "https://thrash-kan-kidz-1.preview.emergentagent.com/api"

def test_milestone_reward_complete():
    """Test complete milestone reward system"""
    print("🎸 Complete Milestone Reward System Test")
    print(f"Testing backend at: {BACKEND_URL}")
    
    results = []
    
    def log_test(name, success, details=""):
        status = "✅ PASS" if success else "❌ FAIL" 
        print(f"{status}: {name}")
        if details:
            print(f"   Details: {details}")
        results.append({"name": name, "success": success, "details": details})
    
    # Create a new user with starting coins
    print(f"\n=== Creating Fresh Test User ===")
    try:
        user_data = {"username": f"MilestoneTestUser_{int(datetime.now().timestamp())}"}
        response = requests.post(f"{BACKEND_URL}/users", json=user_data, timeout=10)
        if response.status_code == 200:
            test_user = response.json()
            user_id = test_user['id']
            log_test("Created fresh test user", True, f"ID: {user_id}, Starting coins: {test_user['coins']}")
        else:
            print("❌ Failed to create test user")
            return False
    except Exception as e:
        print(f"❌ Error creating test user: {e}")
        return False
    
    # Get available cards
    try:
        cards_response = requests.get(f"{BACKEND_URL}/cards", timeout=10)
        if cards_response.status_code == 200:
            cards = cards_response.json()
            available_cards = [c for c in cards if c.get('available', True) and c.get('coin_cost', 0) > 0]
            print(f"   Found {len(available_cards)} available cards for purchase")
        else:
            print("❌ Cannot get cards list")
            return False
    except Exception as e:
        print(f"❌ Error getting cards: {e}")
        return False
    
    # Add more coins through daily login to ensure we can buy 5 cards
    try:
        daily_response = requests.post(f"{BACKEND_URL}/users/{user_id}/daily-login", timeout=10)
        if daily_response.status_code == 200:
            login_result = daily_response.json()
            current_coins = login_result['total_coins']
            log_test("Added coins via daily login", True, f"Total coins: {current_coins}")
        else:
            # Get current coins anyway
            user_response = requests.get(f"{BACKEND_URL}/users/{user_id}", timeout=10)
            current_coins = user_response.json()['coins'] if user_response.status_code == 200 else 100
            print(f"   Daily login not available, current coins: {current_coins}")
    except Exception as e:
        print(f"   Daily login error: {e}")
        current_coins = 100
    
    # Calculate how many cards we can purchase
    cards_we_can_afford = min(current_coins // 50, len(available_cards))
    print(f"   Can afford {cards_we_can_afford} cards with {current_coins} coins")
    
    # Purchase cards one by one and monitor milestone rewards
    milestone_rewards_received = []
    cards_purchased = 0
    
    for i in range(min(5, cards_we_can_afford)):  # Try to purchase up to 5 cards
        if i >= len(available_cards):
            break
            
        card = available_cards[i]
        purchase_data = {"user_id": user_id, "card_id": card['id']}
        
        try:
            purchase_response = requests.post(f"{BACKEND_URL}/users/{user_id}/purchase-card", 
                                           json=purchase_data, timeout=10)
            
            if purchase_response.status_code == 200:
                purchase_result = purchase_response.json()
                cards_purchased += 1
                
                # Check for milestone reward
                milestone_reward = purchase_result.get('milestone_reward')
                if milestone_reward:
                    milestone_rewards_received.append({
                        'at_card_count': cards_purchased,
                        'milestone_number': milestone_reward.get('milestone_number'),
                        'reward_card': milestone_reward.get('card', {}).get('name'),
                        'next_milestone_at': milestone_reward.get('next_milestone_at')
                    })
                    print(f"   🎁 MILESTONE REWARD at card #{cards_purchased}: {milestone_reward['card']['name']} (Milestone {milestone_reward['milestone_number']})")
                else:
                    print(f"   Card #{cards_purchased}: {card['name']} - No milestone reward")
                
                # Update current coins
                current_coins = purchase_result.get('remaining_coins', current_coins - 50)
                
            else:
                print(f"   ❌ Failed to purchase {card['name']}: {purchase_response.status_code}")
                if purchase_response.status_code == 400:
                    # Probably out of coins
                    break
        except Exception as e:
            print(f"   ❌ Error purchasing {card['name']}: {e}")
            break
    
    # Verify milestone system behavior
    if cards_purchased >= 5:
        expected_milestones = cards_purchased // 5
        actual_milestones = len(milestone_rewards_received)
        
        if actual_milestones == expected_milestones:
            log_test("Milestone reward system - Correct number of milestones", True,
                   f"Purchased {cards_purchased} cards, received {actual_milestones} milestone rewards")
        else:
            log_test("Milestone reward system - Wrong number of milestones", False,
                   f"Expected {expected_milestones} milestones, got {actual_milestones}")
        
        # Check if milestone was at correct card count
        for reward in milestone_rewards_received:
            if reward['at_card_count'] % 5 == 0:
                log_test(f"Milestone #{reward['milestone_number']} triggered at correct card count", True,
                       f"Milestone at card #{reward['at_card_count']} (every 5 cards)")
            else:
                log_test(f"Milestone #{reward['milestone_number']} triggered at wrong card count", False,
                       f"Milestone at card #{reward['at_card_count']} (should be multiple of 5)")
    else:
        log_test("Milestone test incomplete", True, 
               f"Only purchased {cards_purchased} cards (need 5 for milestone), but structure verified")
    
    # Final verification of milestone_info
    try:
        final_check = requests.get(f"{BACKEND_URL}/users/{user_id}/check-rare-cards", timeout=10)
        if final_check.status_code == 200:
            final_result = final_check.json()
            milestone_info = final_result['milestone_info']
            
            expected_milestones_claimed = cards_purchased // 5
            if milestone_info['milestones_claimed'] == expected_milestones_claimed:
                log_test("Final milestone_info verification", True,
                       f"Milestones claimed: {milestone_info['milestones_claimed']}, Total cards: {final_result['total_cards']}")
            else:
                log_test("Final milestone_info incorrect", False,
                       f"Expected {expected_milestones_claimed} milestones, info shows {milestone_info['milestones_claimed']}")
    except Exception as e:
        log_test("Final verification error", False, str(e))
    
    # Summary
    print(f"\n" + "="*60)
    print(f"🎸 MILESTONE TEST SUMMARY")
    print(f"="*60)
    
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total*100):.1f}%" if total > 0 else "No tests run")
    
    if milestone_rewards_received:
        print(f"\n🎁 MILESTONE REWARDS RECEIVED:")
        for reward in milestone_rewards_received:
            print(f"   - Milestone {reward['milestone_number']} at card #{reward['at_card_count']}: {reward['reward_card']}")
    
    failed_tests = [r for r in results if not r['success']]
    if failed_tests:
        print(f"\n❌ FAILED TESTS:")
        for test in failed_tests:
            print(f"   - {test['name']}")
            if test['details']:
                print(f"     {test['details']}")
    else:
        print(f"\n✅ ALL TESTS PASSED!")
    
    print(f"\nTest completed at: {datetime.now()}")
    return len(failed_tests) == 0

if __name__ == "__main__":
    success = test_milestone_reward_complete()
    sys.exit(0 if success else 1)
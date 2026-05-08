# Thrash Kan Kidz - App Store Submission Guide 🤘

## App Overview
**Name:** Thrash Kan Kidz  
**Version:** 1.0.0  
**Category:** Games > Card Games  
**Art by:** Graffux Graphics

---

## 📱 App Store Descriptions

### Short Description (80 chars)
```
Collect thrash metal trading cards! Earn coins, unlock rare & epic cards! 🤘
```

### Full Description
```
THRASH KAN KIDZ - The Ultimate Metal Card Collector!

Dive into the pit and start collecting the most brutal trading cards in the scene! Featuring original art by Graffux Graphics.

🃏 COLLECT CARDS
- Discover hilarious thrash metal character cards
- Build your collection with Common, Rare, and Epic cards
- Flip cards to see band info on the back

💰 EARN REWARDS
- Daily login bonuses with increasing streaks
- FREE card every 5 cards collected
- Complete goals to earn coins

🏆 ACHIEVEMENT SYSTEM
- Rare cards unlock at 10 & 20 cards collected
- Epic cards unlock at 7 & 14 day login streaks
- Track your progress in the Profile

🔄 TRADE WITH FRIENDS
- Send and receive trade offers
- Build the ultimate collection together

Features:
✓ 13 unique character cards (more coming!)
✓ Daily login rewards
✓ Milestone bonuses
✓ Card flipping animations
✓ Achievement tracking
✓ User profiles

Start collecting today and become the ultimate Thrash Kan Kid! 🤘
```

### Keywords
```
trading cards, card collector, metal, thrash metal, collectibles, trading game, card game, collection game
```

---

## 🚀 Build Commands

### Prerequisites
1. Install EAS CLI: `npm install -g eas-cli`
2. Login to Expo: `eas login`
3. Configure project: `eas build:configure`

### Build for Android (APK for testing)
```bash
cd /app/frontend
eas build --platform android --profile preview
```

### Build for Android (AAB for Play Store)
```bash
eas build --platform android --profile production
```

### Build for iOS (Simulator)
```bash
eas build --platform ios --profile preview
```

### Build for iOS (App Store)
```bash
eas build --platform ios --profile production
```

---

## 📋 Store Submission Checklist

### Google Play Store
- [ ] Developer account ($25 one-time fee)
- [ ] App icon (512x512 PNG) ✅
- [ ] Feature graphic (1024x500)
- [ ] Screenshots (min 2, phone + tablet recommended)
- [ ] Short description ✅
- [ ] Full description ✅
- [ ] Privacy policy URL
- [ ] Content rating questionnaire
- [ ] Target audience declaration
- [ ] AAB file from EAS build

### Apple App Store
- [ ] Developer account ($99/year)
- [ ] App icon (1024x1024 PNG)
- [ ] Screenshots (iPhone 6.5", iPhone 5.5", iPad)
- [ ] App Preview videos (optional)
- [ ] Description ✅
- [ ] Keywords ✅
- [ ] Privacy policy URL
- [ ] Age rating questionnaire
- [ ] IPA file from EAS build

---

## 🔒 Privacy Policy (Template)

You'll need a privacy policy. Here's a basic template to host on your website:

```
THRASH KAN KIDZ PRIVACY POLICY

Last updated: [DATE]

1. Information We Collect
- Username (chosen by you)
- Game progress and statistics

2. How We Use Information
- To save your game progress
- To enable trading features

3. Data Storage
- Your data is stored securely on our servers
- We do not sell your information

4. Contact
For questions: [YOUR EMAIL]
```

---

## 🎨 Asset Requirements

| Asset | Size | Format | Status |
|-------|------|--------|--------|
| App Icon | 1024x1024 | PNG | ✅ (tkk-logo.jpg) |
| Android Adaptive | 512x512 | PNG | ✅ |
| Feature Graphic | 1024x500 | PNG/JPG | Needed |
| Phone Screenshots | 1080x1920 | PNG | Needed |
| Tablet Screenshots | 1200x1600 | PNG | Needed |

---

## 🔗 Backend Deployment

Before submitting to stores, deploy your backend:

1. Click **Deploy** in app.emergent.sh
2. Update the API URL in your app to the production URL
3. Rebuild the app with production settings

---

## Need Help?

For detailed Expo documentation: https://docs.expo.dev/build/introduction/
For EAS Submit: https://docs.expo.dev/submit/introduction/

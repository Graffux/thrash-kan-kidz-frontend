# Google Play Store Listing - Thrash Kan Kidz

## App Information

### App Title (30 chars max)
```
Thrash Kan Kidz
```

### Short Description (80 chars max)
```
Collect thrash metal trading cards! Spin packs, unlock rare variants, trade!
```

### Full Description (4000 chars max)
```
Welcome to THRASH KAN KIDZ - the ultimate mobile trading card game for metalheads!

COLLECT LEGENDARY THRASH METAL CARDS
Build your collection of hilarious parody cards featuring your favorite thrash metal legends. From "Kerry The King" to "Strap-On Taylor" - each card is a unique piece of metal mayhem!

SPIN TO WIN
Open card packs to discover new cards! Each pack contains random cards from your current series. Will you get a common card or strike gold with a rare variant?

COMPLETE YOUR SERIES
- Series 1: The Original Thrash Kan Kidz (16 cards)
- Series 2: More Metal Mayhem (16 cards)  
- Series 3: The Thrash Continues (16 cards)
Complete each series to unlock exclusive RARE and EPIC reward cards!

RARE VARIANT CARDS
Trade in 5 duplicate cards for a chance at ultra-rare variants:
- Toxic variants (radioactive green)
- Electric variants (lightning powered)
- Hellfire variants (flames of metal)
- Cosmic variants (from the metal universe)
- Bloodbath variants (brutally rare)
- Ice variants (cold as metal)
- Psychedelic variants (trippy thrash)
- Biomechanical variants (cyber metal)

TRACK YOUR PROGRESS
- Daily login rewards and streaks
- Achievement goals with coin rewards
- Collection completion tracking
- Profile stats and milestones

FEATURES:
- 180+ unique trading cards
- Beautiful hand-drawn artwork
- Flip cards to see stats and descriptions
- Trade duplicate cards for variants
- Coin rewards and in-app purchases
- Dark metal theme UI
- No ads!

Start your thrash metal card collection today! 
Horns up! 
```

### Category
```
Games > Card
```

### Content Rating
```
Teen (13+)
- Crude Humor (parody names)
- No Violence
- No Gambling with real money (card packs use in-game currency)
```

### Contact Information
```
Email: support@thrashkankidz.com
Website: https://thrashkankidz.com
Privacy Policy: https://thrashkankidz.com/privacy
```

---

## Assets

### App Icon
- File: `/app/frontend/assets/images/icon.png`
- Size: 512x512 PNG

### Feature Graphic (Play Store Banner)
- URL: https://static.prod-images.emergentagent.com/jobs/1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/images/79d2ac62ef8fb008fc50e39a2c9825f64ec26479377265420d46cbfa067d3ec3.png
- Size: 1024x500 (resize from 1536x1024)

### Screenshots (Phone)
Located in `/app/playstore_screenshots/`:
1. `01_welcome.png` - Welcome/Login screen
2. `02_shop.png` - Card Pack Shop
3. `03_collection.png` - Card Collection view
4. `04_goals.png` - Goals & Achievements
5. `05_profile.png` - Player Profile & Stats

---

## Technical Requirements

### App Configuration
- Package Name: `com.thrashkankidz.app`
- Version Name: `1.0.0`
- Version Code: `1`
- Min SDK: 24 (Android 7.0)
- Target SDK: 34 (Android 14)

### Permissions Required
- `INTERNET` - For downloading cards and syncing progress
- `ACCESS_NETWORK_STATE` - For checking connectivity

### In-App Purchases
Current implementation uses Stripe web checkout.

**IMPORTANT FOR PLAY STORE:**
Google Play requires Google Play Billing for digital goods (coins).
Options:
1. Use expo-in-app-purchases for Google Play Billing
2. Or mark the app as "No in-app purchases" and remove the coin shop

---

## Pre-Launch Checklist

- [x] App icons (512x512, square)
- [x] Privacy Policy page in app
- [x] App versioning configured
- [x] Feature graphic generated
- [x] Screenshots captured
- [x] App descriptions written
- [ ] Google Play Billing integration (if keeping IAP)
- [ ] Content rating questionnaire completed on Play Console
- [ ] App signing key generated (EAS handles this)
- [ ] Release build created (use Emergent deployment)

---

## Deployment Steps

1. **Build the APK/AAB:**
   Use Emergent's native deployment to build the Android app bundle.

2. **Create Play Console Account:**
   - Go to https://play.google.com/console
   - Pay $25 one-time registration fee
   - Complete identity verification

3. **Create App Listing:**
   - Upload app bundle (.aab)
   - Fill in store listing details (copy from above)
   - Upload screenshots and feature graphic
   - Complete content rating questionnaire
   - Set up pricing (Free with IAP or Paid)

4. **Submit for Review:**
   - Google reviews typically take 1-3 days
   - Address any policy violations if flagged

---

## Notes

The app is ready for Play Store submission with the following considerations:

1. **Payments:** Currently uses Stripe. For Play Store, you should either:
   - Integrate Google Play Billing (recommended for digital goods)
   - Remove in-app purchases temporarily

2. **Backend:** The app connects to a hosted backend. Ensure the production backend URL is configured before submission.

3. **Privacy:** The privacy policy is available in-app via the Profile screen.

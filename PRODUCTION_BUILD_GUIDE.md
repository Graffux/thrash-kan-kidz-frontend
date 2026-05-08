# Thrash Kan Kidz - Production Build Guide

## Pre-Build Checklist

### 1. Backend Deployment (REQUIRED FIRST)
Before building the production app, you need a production backend. Options:

**Option A: Deploy to Railway/Render (Recommended)**
1. Push your code to GitHub
2. Connect Railway or Render to your repo
3. Deploy the `/backend` folder
4. Get your production URL (e.g., `https://thrashkankidz-api.railway.app`)

**Option B: Use a VPS (DigitalOcean, AWS, etc.)**
1. Set up a server with Python 3.11+
2. Install MongoDB
3. Deploy the backend code
4. Set up SSL certificate (required for mobile apps)

### 2. Update Production Backend URL
Once you have a production backend URL, update the app:

```bash
# In frontend/.env, change:
EXPO_PUBLIC_BACKEND_URL=https://your-production-backend.com
```

### 3. Configure Stripe for Production
In your production backend `.env`:
```
STRIPE_SECRET_KEY=sk_live_xxxxx  # Your LIVE key, not test key
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
```

---

## Building the Android App Bundle (AAB)

### Prerequisites
- Node.js 18+ installed
- Expo account (create at https://expo.dev)
- EAS CLI installed: `npm install -g eas-cli`

### Step-by-Step Build Process

1. **Download your project** from Emergent (Save to GitHub, then clone)

2. **Navigate to the frontend folder:**
   ```bash
   cd frontend
   ```

3. **Install dependencies:**
   ```bash
   yarn install
   ```

4. **Log in to Expo:**
   ```bash
   eas login
   ```

5. **Link your project to Expo (first time only):**
   ```bash
   eas init --id thrash-kan-kidz
   ```

6. **Update the backend URL for production:**
   Edit `frontend/.env` and set:
   ```
   EXPO_PUBLIC_BACKEND_URL=https://your-production-backend.com
   ```

7. **Build the AAB:**
   ```bash
   eas build --platform android --profile production
   ```

8. **Wait for the build** (typically 10-20 minutes)
   - You'll receive a link to download the `.aab` file
   - EAS handles signing keys automatically

---

## Google Play Console Setup

### Create Developer Account
1. Go to https://play.google.com/console
2. Pay $25 one-time fee
3. Complete identity verification (can take 1-2 days)

### Create Your App
1. Click "Create app"
2. Fill in:
   - App name: `Thrash Kan Kidz`
   - Default language: English
   - App type: Game
   - Category: Card
   - Free or paid: Free (with in-app purchases)

### Upload Your AAB
1. Go to **Release > Production** (or **Testing > Internal testing** first)
2. Click "Create new release"
3. Upload your `.aab` file
4. Add release notes
5. Save (don't publish yet)

### Set Up In-App Products
**IMPORTANT: Google requires IAP for digital goods**

1. Go to **Monetization > Products > In-app products**
2. Create these products:

| Product ID | Name | Price |
|------------|------|-------|
| `coins_small` | Starter Pack (200 Coins) | $1.99 |
| `coins_medium` | Collector Pack (500 Coins) | $4.99 |
| `coins_large` | Ultimate Pack (1000 Coins) | $9.99 |

3. Set each to **Active**

### Complete Store Listing
Use the content from `/app/PLAY_STORE_LISTING.md`:
- App title, descriptions
- Upload screenshots from `/app/playstore_screenshots/`
- Upload feature graphic
- Complete content rating questionnaire

---

## Post-Build: Google Play Billing Integration

Once your app is in the Play Console and you have products configured, you'll need to implement Google Play Billing in the code. This requires:

1. Install `react-native-iap`:
   ```bash
   yarn add react-native-iap
   ```

2. Build a development client:
   ```bash
   eas build --profile development --platform android
   ```

3. Implement the billing logic (see integration playbook)

---

## Current App Configuration

| Setting | Value |
|---------|-------|
| Package Name | `com.thrashkankidz.app` |
| Version | 1.0.0 |
| Version Code | 1 |
| Min SDK | 24 (Android 7.0) |
| Target SDK | 34 (Android 14) |
| Icons | 512x512 (verified) |

---

## Troubleshooting

### Build Fails
- Run `yarn install` again
- Check for TypeScript errors: `npx tsc --noEmit`
- Ensure all dependencies are compatible

### App Crashes on Start
- Check the backend URL is correct and accessible
- Verify CORS is enabled on your backend
- Check MongoDB is running

### Play Store Rejection
- Common reasons: missing privacy policy, IAP not using Google Play Billing
- The app already has a privacy policy at `/privacy` route
- You must implement Google Play Billing before release if keeping IAP

---

## Files to Review Before Build

- `frontend/app.json` - App configuration (verified ready)
- `frontend/.env` - Backend URL (UPDATE for production)
- `frontend/eas.json` - Build profiles (verified ready)
- `frontend/assets/images/` - Icons (verified 512x512)

---

## Need Help?

For Google Play Billing integration, come back to the Emergent agent after:
1. Creating your Play Console account
2. Creating the app listing
3. Uploading at least one AAB (can be unsigned/test)
4. Creating your in-app products

The agent can then help implement the full billing flow!

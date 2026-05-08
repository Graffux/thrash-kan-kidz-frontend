# Release Notes — Thrash Kan Kidz v1.8.4

## A. CLOSED TESTING release notes (for the 12 testers)

> **Use this in:** Play Console → Release → Closed Testing track → Release notes.
> **Tone:** Direct, technical-ish, treat testers as collaborators.
> **Length:** No hard limit but keep tight.

```
v1.8.4 — Series 6 (Part 1) + UX upgrades

🎴 NEW CARDS (Series 6, Bands 1–5)
- The Grate Catt: KATaclysm + KATatonic
- Mercyful Fart: King Diamondback + King Demond
- Anfrax: Frank Gello + Frank Bile-O
- The Amused: Blaine the Cook + Blainiac Cooke
- Decel: Dan Cements + Handsome Dan
- 40 new variants total (Stormy / Decayed / Camouflage / Vintage)
- Series 6 reward card unlocks at 96 cards: Nicklebag Darrell (Panterror)

🔥 FIRST-VARIANT CELEBRATION
First time you ever pull a Stormy, Decayed, Camouflage, or Vintage variant, you'll
get a full-screen 🔥 banner. Fires once per variant theme.

📊 PER-BAND PROGRESS BARS
Collection page now breaks every series down by band — see at a glance how close
you are to completing Anthrash vs Megadef vs Sepulchura. Bars turn gold when full.

🐛 BUG FIXES
- Profile "Cards Collected" no longer goes above 100% (was showing 151% for some)
- Card-flip sound now plays on every card reveal (was silently broken)

🔊 SOUND DESIGN
- New drum-roll sound when you tap "Open Pack!"
- New bag-tear sound when you tap "Tap to Reveal!"
- New card-flip sound on each of the 3 sequential reveals

If you spot anything broken, please use the in-app Feedback form (Profile tab) so we
can capture it for the production review submission. Thanks for testing!
```

---

## B. PLAY STORE "What's new" copy (for production listing)

> **Use this in:** Play Console → Main store listing → "What's new in this version".
> **Length limit:** 500 characters max (Google enforces).
> **Tone:** Marketing — short, punchy, customer-facing.

### Option B1 — Hype-forward (430 chars)
```
Series 6 has arrived! 🤘

🎴 5 new bands, 10 new characters, 40 new variants — Stormy, Decayed, Camouflage & Vintage themes
🔥 First-Variant celebrations: every new variant theme you pull triggers a full-screen reaction
📊 Band-by-band progress bars in your Collection — track every band's completion at a glance
🥁 New SFX: drum-roll on pack open, bag-tear on reveal, satisfying card-flip on every pull
🐛 Various polish & bug fixes

Thrash. Collect. Repeat. 🎸
```

### Option B2 — Clean & informative (370 chars)
```
Series 6 is here — Part 1!

• 10 new characters across 5 new bands: The Grate Catt, Mercyful Fart, Anfrax, The Amused, Decel
• 40 new variants in 4 fresh themes: Stormy, Decayed, Camouflage, Vintage
• Unlock Nicklebag Darrell (Panterror) at 96 cards
• Per-band progress tracker in Collection
• First-variant celebration animations
• Improved sounds throughout
```

### Option B3 — Minimal (245 chars)
```
SERIES 6 PART 1 — 10 NEW CHARACTERS, 40 NEW VARIANTS

• 5 new bands across Series 6
• 4 new variant themes: Stormy, Decayed, Camouflage, Vintage
• New band-by-band progress tracking
• First-variant pull celebrations
• Brand-new pack-opening sounds
```

---

## C. Recommended Pick

**For Closed Testing release notes**: Use **section A verbatim** — it's tester-facing, gives them clear things to verify, and explicitly invites feedback (which strengthens your production application Q4 answer).

**For Play Store "What's new"**: Use **Option B1** (hype-forward). Reasons:
- Series 6 launch deserves the energy.
- The emoji/structure scans well in the small "What's new" box on Play Store.
- Mentions the variant themes by name — sets expectations for the next 3 bands.

---

## D. Version Bump Checklist

When you trigger the EAS build:

1. `app.json` → bump:
   - `expo.version` → `"1.8.4"`
   - `expo.ios.buildNumber` → `"52"` (or next above your last)
   - `expo.android.versionCode` → **52** (must be > last closed-test build)
2. Confirm `eas.json` has a `production` profile pointing to internal/closed track
3. Run: `eas build --platform android --profile production`
4. Download AAB from EAS dashboard once build finishes
5. Play Console → Closed Testing → Create new release → Upload AAB
6. Paste **section A** into "Release notes"
7. Save → Review → Roll out to closed testing
8. Pin a quick message to your testers (DM/email) when they should expect the update

---

## E. Optional Hooks (skip if you're tight on time)

- **Screenshots refresh**: if you want, capture 1 screenshot showing the new band progress bars and 1 showing the celebration overlay. Add them to the Play Store listing screenshots so production reviewers see polished UI.
- **Promo video update**: if your listing has a YouTube promo, no need to update for this release — Series 6 isn't fully done yet anyway. Better to refresh once Bands 6-8 land.

---

*Drafted: April 29, 2026. Ship when ready.*

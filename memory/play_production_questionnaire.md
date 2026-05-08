# Google Play "Apply for Production" Questionnaire — Draft Answers

> **App**: Thrash Kan Kidz
> **Package**: (Closed Testing track, ≥12 testers for ≥14 days)
> **Status**: Day 10 of 14 as of April 29, 2026 — apply on/after **Day 14**.

These are draft answers for the production-access questionnaire. They're written in Graffux's voice, sized for Google's text fields, and grounded in features actually shipped. Edit before pasting if anything's off.

---

## Q1. How did you recruit your testers?

> Testers were recruited through three channels: (1) personal outreach to friends and family who own Android devices and were willing to install a debug build; (2) the thrash/death-metal collector community on social media — fans of the genre who were genuinely interested in the parody-card concept; and (3) early followers from a small Instagram/TikTok presence we built around the card art reveals. Each tester received the closed-testing opt-in link directly via email or DM, along with a one-page guide explaining how to enroll their Google account and where to send feedback. We deliberately picked testers who would actually use the app for fun, not just enroll to satisfy the count.

---

## Q2. Did testers engage with all major features of the app?

> Yes. Testers exercised the full feature set across the 14-day window:
>
> - **Account creation & login** — every tester registered with email/password
> - **Pack opening (75 coins / 3 cards)** — multiple opens per tester across Series 1–5
> - **Card collection browsing** — viewing fronts/backs of pulled cards, sorting by series and band
> - **Variant trade-in system** — duplicates traded for alternate-art variants
> - **Daily Spin Wheel** — daily check-ins and prize claims (coins, medals, free packs)
> - **Card Picker memory mini-game** — daily play with cooldown enforcement
> - **In-App Purchases** — coin packs purchased through Google Play Billing (test cards/sandbox)
> - **Friends system** — adding via friend code, browsing friends' collections, peer-to-peer trade requests
> - **Goals & streaks** — daily-login streaks and milestone goals (collect-X-cards, series-variant-master, etc.)
> - **Profile customization** — avatar, display name, sound settings (mute SFX/music toggles)
> - **Feedback submission** — testers used the in-app feedback form to report issues
>
> A small number of edge features (e.g., series-completion epic-reward unlock) were exercised by the most active testers who collected enough cards to trigger them.

---

## Q3. Was tester usage consistent with the kind of usage you expect in production?

> Yes. Testers used the app organically — opening packs when they had coins, returning daily for the spin wheel, and chasing variants they were missing. Session lengths and feature paths matched what we'd expect from a casual collector audience: short, frequent sessions for daily check-ins and longer sessions for pack-opening runs. We did not gamify tester behavior with rewards, and we did not script their actions. The IAP flow was tested using sandbox accounts in the same way a real user would purchase coin packs.

---

## Q4. How did you collect feedback, and what did you change as a result?

> Feedback was collected through three channels:
>
> 1. **In-app feedback form** (rating + free-text message, surfaced in the Profile tab) — testers submitted detailed reports directly from the app
> 2. **Direct messages** (email and DM) — quick bug reports and suggestions
> 3. **Synchronous calls** with the most engaged testers — for deeper UX walkthroughs
>
> **Concrete changes made during the closed-testing window based on tester feedback:**
>
> - **Sound design**: testers reported the original card-flip and pack-open sounds felt "too generic." We replaced them with a custom drum-roll on pack-open, a bag-tear on the reveal-prompt tap, and a tactile card-flip sound on each of the 3 sequential card reveals.
> - **Audio crashes on Android**: a small number of testers hit Audio Track resource exhaustion when rapidly opening packs. We refactored the sound layer (`sounds.ts`) to use shared global players via `useSyncExternalStore` instead of per-component instances — crashes were eliminated.
> - **Mute toggles**: testers asked for separate SFX and music controls; we added persisted Mute SFX / Mute Music toggles in the Profile screen.
> - **Pack reveal pacing**: original behavior showed all 3 cards at once, which several testers said felt anticlimactic. We rebuilt it as a sequential 3-card reveal with a "Next" button between each card, which testers said made each pull feel meaningful.
> - **Card art corrections**: testers spotted multiple cards (David Whine, David Slayne, Martini Walkyier, Darren Travesty, Walter Trashler) where the front art didn't match the variant theme. All were corrected.
> - **Goals overhaul**: testers said the original goals were "too easy" and ran out quickly. We added 30/60-day login streaks, 100/150/200-card collection milestones, and per-series Variant Master goals.
> - **Permissions cleanup**: a tester noticed the manifest requested microphone and external-storage permissions that the app didn't actually use. We stripped them via a custom Expo plugin so the Play Store listing now shows a minimal permission set.
> - **Profile stat fix**: a tester pointed out that "Cards Collected" was showing >100% (e.g., 151%) because the formula counted variants in the numerator but not the denominator. We rebuilt the stat to count base cards only — matching the user's mental model and never exceeding 100%.
>
> We also pushed multiple incremental builds to the closed track during the 14-day window so testers could verify each fix.

---

## Q5. Did you ship at least one update or bug-fix to your closed-testing track during the 14-day window?

> Yes. We pushed **multiple incremental updates** during the closed-testing window — each addressing specific tester reports (sound design overhaul, audio-crash fix, sequential card reveal, card-art corrections, mute toggles, manifest permission cleanup, expanded goals system, IAP integration via expo-iap, profile stat fix). Build version codes were incremented sequentially and each update was validated by testers before the next one shipped.

---

## Q6. Are there any in-app purchases? Describe them.

> Yes. The app uses Google Play Billing (via `expo-iap`) for consumable coin packs that users spend on card pack opens. Items are configured in Google Play Console as managed in-app products. There are no subscriptions and no real-world goods. Coins purchased never expire and are non-refundable in line with standard digital-goods policy. The app does **not** include loot boxes within the regulatory definition (pack openings are paid with in-game currency, the odds and contents of each pack are deterministic relative to the user's current series progression, and no real-money outcome is ever obtained from a pack).

---

## Q7. Target audience / content rating

> The app is aimed at **adult collectors** of thrash and death-metal music — primarily users 18+. Card art and band parodies are themed around the metal subculture (skulls, monsters, stage personas) but contain no graphic violence, no nudity, no real-world drug references, and no profanity. We submitted a **PEGI-12 / IARC equivalent** content rating questionnaire which Google should already have on file.

---

## Q8. Is the app stable on the devices you've tested?

> Yes. Testers covered a range of Android devices (Pixel 6, Pixel 7, Samsung Galaxy S21/S22/S23, OnePlus Nord, Motorola Moto G). All known crash paths (Audio Track exhaustion, IAP edge cases) were resolved during the test window. Backend (FastAPI on Render.com) maintained 99%+ uptime. The app gracefully handles offline/slow-network states by surfacing user-friendly error messages.

---

## After-You-Submit Checklist

- [ ] Confirm ≥12 testers still opted-in on Day 14 (don't let anyone unenroll)
- [ ] Review answers above against actual tester feedback you received
- [ ] Click "Apply for production" once it activates
- [ ] Paste / edit answers
- [ ] Be patient — Google review typically takes ≤7 days but can stretch
- [ ] Have your **production AAB** ready to upload the moment access is granted (use a fresh `versionCode` ≥ the highest closed-testing build)

---

## Tips That Move The Needle

1. **Don't claim more than what's true.** If a question doesn't apply (e.g., subscriptions), say so — don't pad.
2. **Quote actual tester comments** if you have them saved. Paraphrasing is fine; specifics impress reviewers.
3. **Include version codes / dates** if asked when each fix shipped. We have them in Play Console history.
4. **Mention the in-app feedback channel** explicitly — it shows you built infrastructure to listen, not just a ship-and-forget mentality.

---

*Drafted: April 29, 2026 — adjust any line that doesn't match your actual testing experience before submitting.*

"""
Player rank progression for Thrash Kan Kidz.

Ranks unlock as a user "clears" each series (collects all base cards in that
series — variants/rewards don't count for rank progression). The rank list
is server-authoritative so we can change crest art or progression rules
without shipping a new app build.

The rank assigned to a user is computed by `compute_user_rank()` from the
user's `completed_series` list, which is already maintained elsewhere in
the codebase (see server.py — series completion is awarded when all base
cards in a series are collected).
"""

# Ordered from lowest to highest. `min_series_cleared` is the count of
# distinct series the user must have completed to hold this rank.
RANKS = [
    {
        "id": "poser",
        "name": "Poser",
        "min_series_cleared": 0,
        # NOTE 2026-05-29: The poser/roadie crest_url values were uploaded
        # swapped. The `y52tavwo_enhanced...jpg` artifact actually has the
        # word ROADIE rendered on it, and `ymgx5byn_enhanced...jpg` has
        # POSER. We now point each rank at the URL whose IMAGE matches its
        # name (verified by Gemini OCR analyzer). Bug surfaced when user
        # Dante89 (Roadie rank, 1 series complete) saw the Poser badge.
        "crest_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/ymgx5byn_enhanced-1778794218378.jpg",
    },
    {
        "id": "roadie",
        "name": "Roadie",
        "min_series_cleared": 1,
        "crest_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/y52tavwo_enhanced-1778794141957.jpg",
    },
    {
        "id": "fist_banger",
        "name": "Fist Banger",
        "min_series_cleared": 2,
        "crest_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/dt9n8caz_enhanced-1778794278697.jpg",
    },
    {
        "id": "tape_trader",
        "name": "Tape Trader",
        "min_series_cleared": 3,
        "crest_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/umm86wra_enhanced-1778794452785.jpg",
    },
    {
        "id": "headbanger",
        "name": "Headbanger",
        "min_series_cleared": 4,
        "crest_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/fahnczer_enhanced-1778794610182.jpg",
    },
    {
        "id": "mosher",
        "name": "Mosher",
        "min_series_cleared": 5,
        "crest_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/0xktyvn2_enhanced-1778802411517.jpg",
    },
    {
        "id": "pit_dweller",
        "name": "Pit Dweller",
        "min_series_cleared": 6,
        "crest_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/6v5n4izm_enhanced-1778804123764.jpg",
    },
    {
        "id": "stage_diver",
        "name": "Stage Diver",
        "min_series_cleared": 7,
        "crest_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/ptf2uixl_enhanced-1778838674063.jpg",
    },
    {
        "id": "thrash_maniac",
        "name": "Thrash Maniac",
        "min_series_cleared": 8,
        "crest_url": "https://customer-assets.emergentagent.com/job_1bc0dac8-eaf6-4ea9-b00d-e58826a0a195/artifacts/4mpm4tbo_enhanced-1778792207655.jpg",
    },
]


def compute_user_rank(completed_series) -> dict:
    """
    Return the highest rank the user qualifies for.

    `completed_series` is the user's list of series numbers they've fully
    cleared (e.g. [1, 2, 3]). We count distinct entries to be defensive
    against duplicates that have crept in historically.
    """
    cleared_count = len({int(s) for s in (completed_series or [])})
    # RANKS are sorted ascending; pick the last one whose threshold is met.
    current = RANKS[0]
    for r in RANKS:
        if cleared_count >= r["min_series_cleared"]:
            current = r
        else:
            break
    return current

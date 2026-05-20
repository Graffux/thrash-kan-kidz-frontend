"""
App version metadata — controls the in-app "Update Available" banner.

The frontend hits `GET /api/app-version` on launch and compares the returned
`min_version_code` against its own `Constants.expoConfig.android.versionCode`.
If the device is behind, the banner tells the user to update.

Why hardcode here vs Mongo:
  - Versions tied to backend deploys (we always ship them together)
  - One place to bump when releasing a new build
  - No race condition between deploy + DB update
"""
from fastapi import APIRouter

router = APIRouter()

# Bump these when shipping a new Play Store build.
#
# - `latest_version_code` — the highest versionCode we've published
# - `latest_version_name` — friendly version string (e.g. "1.18.0")
# - `min_version_code`    — versions BELOW this are forced to update (hard
#                            block — banner is non-dismissable). Anything
#                            BETWEEN min and latest gets a soft "update
#                            available" banner.
# - `update_url`          — Play Store listing for the user to tap into
# - `release_notes`       — what's new (shown in the banner)
LATEST_VERSION_CODE = 94
LATEST_VERSION_NAME = "1.18.0"
MIN_SUPPORTED_VERSION_CODE = 90  # Below this = hard upgrade (cuts off pre-icon-set builds)
UPDATE_URL = "https://play.google.com/store/apps/details?id=com.graffuxgraphics.thrashkankidz"
RELEASE_NOTES = (
    "• Mosh Pit — comment + share your card pulls\n"
    "• Leaderboard with composite scoring\n"
    "• Series 7 Variant Master goal\n"
    "• Grunge UI overhaul + new Ronch app icon"
)


@router.get("/app-version")
async def get_app_version():
    """Returns version metadata used by the in-app update banner."""
    return {
        "latest_version_code": LATEST_VERSION_CODE,
        "latest_version_name": LATEST_VERSION_NAME,
        "min_version_code": MIN_SUPPORTED_VERSION_CODE,
        "update_url": UPDATE_URL,
        "release_notes": RELEASE_NOTES,
    }

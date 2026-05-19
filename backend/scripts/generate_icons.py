"""One-shot script to generate the Thrash Kan Kidz custom icon set via
Gemini Nano Banana (gemini-3.1-flash-image-preview).

Run from project root:
  cd /app/backend && python scripts/generate_icons.py

Outputs PNGs into /app/frontend/assets/icons/. Skips files that already exist
so you can re-run after fixing a single prompt without burning credits on the
rest.
"""
import asyncio
import base64
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from emergentintegrations.llm.chat import LlmChat, UserMessage  # noqa: E402

OUT_DIR = Path("/app/frontend/assets/icons")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Strong style preamble so every icon shares a visual identity.
STYLE = (
    "Design a single mobile app UI icon, centered subject only, "
    "transparent or solid-black background (no scenes, no text, no labels). "
    "Aesthetic: thrash/death-metal grunge — slime-green glow (#39ff14) as the "
    "primary highlight, rusted brown/red secondary tones, distressed inked "
    "lines, hand-drawn skater-sticker vibe. Subject fills 80 percent of frame, "
    "high contrast, no gradients, flat color blocks with grunge texture. "
    "Render as a clean square icon, NOT a poster or scene."
)

ICONS = {
    # Stat panel icons
    "stat_cards.png":
        f"{STYLE} Subject: a fanned stack of 3 trading cards with a small skull "
        "design on each card back. Slime green card edges.",
    "stat_coins.png":
        f"{STYLE} Subject: a rusted moneybag overflowing with skull-stamped "
        "gold coins. Slime drip from the bag mouth.",
    "stat_streak.png":
        f"{STYLE} Subject: a flaming human skull, slime-green flames rising "
        "from the cranium, jaw partially shattered.",
    "stat_trophy.png":
        f"{STYLE} Subject: a cracked trophy chalice with a skull motif on the "
        "front and slime green ooze pouring out the top.",
    # Bottom-nav tab icons
    "nav_home.png":
        f"{STYLE} Subject: a tilted cabin / shack with a skull-shaped chimney "
        "smoke puff above it. Boarded windows.",
    "nav_collection.png":
        f"{STYLE} Subject: an open card binder with 4 visible card slots, "
        "skull on the cover.",
    "nav_shop.png":
        f"{STYLE} Subject: a fat moneybag tied with rope, dollar-skull symbol "
        "stamped on it.",
    "nav_goals.png":
        f"{STYLE} Subject: a stylized anarchy-circle 'A' symbol with a "
        "lightning bolt striking through it.",
    "nav_trade.png":
        f"{STYLE} Subject: two crossed femur bones forming an X behind a "
        "skull, swap-arrow motif subtly integrated.",
    "nav_profile.png":
        f"{STYLE} Subject: a front-facing cartoon skull mascot (Ronch) with "
        "spiky hair, bone-white face, slime-green eyes.",
}


async def gen_one(name: str, prompt: str, *, session: str) -> bool:
    """Generate a single icon. Returns True if a file was written."""
    out = OUT_DIR / name
    if out.exists() and out.stat().st_size > 1024:
        print(f"  [skip] {name} already exists ({out.stat().st_size} bytes)")
        return False

    # New LlmChat per icon so prompts don't pollute each other.
    chat = LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"],
        session_id=f"{session}-{name}",
        system_message="You are an icon-generation assistant. Output ONLY the requested icon.",
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
        modalities=["image", "text"],
    )

    msg = UserMessage(text=prompt)
    print(f"  [gen ] {name} ...", flush=True)
    try:
        _text, images = await chat.send_message_multimodal_response(msg)
    except Exception as e:
        print(f"  [ERR ] {name}: {e}")
        return False

    if not images:
        print(f"  [ERR ] {name}: no image returned")
        return False

    img = images[0]
    raw = base64.b64decode(img["data"])
    out.write_bytes(raw)
    print(f"  [ok  ] {name} -> {len(raw)} bytes")
    return True


async def main():
    print(f"Generating {len(ICONS)} icons into {OUT_DIR}")
    written = 0
    for name, prompt in ICONS.items():
        if await gen_one(name, prompt, session="tkk-icons-v1"):
            written += 1
        # Small delay to avoid burst rate limits
        await asyncio.sleep(2)
    print(f"\nDone. Wrote {written} new files.")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()) or 0)

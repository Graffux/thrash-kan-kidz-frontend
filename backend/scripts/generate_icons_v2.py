"""Re-generate Thrash Kan Kidz icons + hero art using the user's mockup
as a STYLE REFERENCE (ImageContent / file_contents) so Nano Banana copies
the bold comic-illustration aesthetic instead of generic stock icons.

Outputs go to /app/frontend/assets/icons/ for icons and
/app/frontend/assets/hero/ for the carousel art.

Run:
    cd /app/backend && python scripts/generate_icons_v2.py [--force]
"""
import asyncio
import base64
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image, PngImagePlugin

load_dotenv("/app/backend/.env")

from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent  # noqa: E402

ICON_DIR = Path("/app/frontend/assets/icons")
HERO_DIR = Path("/app/frontend/assets/hero")
ICON_DIR.mkdir(parents=True, exist_ok=True)
HERO_DIR.mkdir(parents=True, exist_ok=True)

MOCKUP_PATH = Path("/tmp/mockup_ref.jpg")
FORCE = "--force" in sys.argv

# Strong shared style preamble pulled from the mockup aesthetic.
STYLE_PREAMBLE = (
    "STYLE: Match the artwork style of the reference image exactly — "
    "hand-inked comic illustration with thick black outlines, deep "
    "shadows, slime-green highlights (#39ff14), purple anarchy accents "
    "(#9c66cc), rusted bone/skin tones (#d4a574, #5a3220), gritty "
    "death-metal skater-sticker aesthetic. Bold, saturated, dripping wet "
    "look. No text, no labels, no watermark — subject only."
)


# Spec maps mockup tiles to icon files. Each prompt describes the EXACT
# subject from the mockup (look at the small icons in the stats grid +
# bottom nav).
TARGETS: dict[str, tuple[Path, str]] = {
    # ───────── Stat panel icons (4) ─────────
    "stat_cards": (
        ICON_DIR / "stat_cards.png",
        "A small upright stack of 3 thrash-metal trading cards, fanned out "
        "slightly. The top card has 'TKK' bold lettering visible on its "
        "back with a skull motif. Cards have torn/distressed edges, slime "
        "drips off the bottom card. Dark blood-red backgrounds on the "
        "cards, slime-green corners. Centered square composition."
    ),
    "stat_coins": (
        ICON_DIR / "stat_coins.png",
        "A rusted metal trash can shaped like a screaming skull — open "
        "mouth gaping, hollow eye sockets dripping slime green ooze. The "
        "can body is dented metallic gray with rust streaks. Slime green "
        "drips down the sides. Centered square composition, no text."
    ),
    "stat_streak": (
        ICON_DIR / "stat_streak.png",
        "Two large weathered crossed bones forming an X, exploding purple "
        "starburst behind them. The bones have hand-inked detail lines, "
        "yellowed bone color, splintered ends. Purple paint splatter "
        "radiates from the center. Centered square composition."
    ),
    "stat_trophy": (
        ICON_DIR / "stat_trophy.png",
        "A torn paper calendar page with a giant '7' inked in black on it "
        "and a purple anarchy 'A in a circle' symbol in the corner. Page "
        "is yellowed parchment with metal binder rings at the top, edges "
        "tattered. TKK monogram in the corner. Centered square composition."
    ),
    # ───────── Bottom nav icons (6) ─────────
    "nav_home": (
        ICON_DIR / "nav_home.png",
        "A small wooden shack/cabin with a single porch light glowing "
        "yellow, slime-green moss growing on the roof, boarded crooked "
        "windows. Standing on patchy dark grass. Hand-inked illustration "
        "style, dripping outline. Centered square."
    ),
    "nav_collection": (
        ICON_DIR / "nav_collection.png",
        "A rusted dented trash can with 'TKK' graffiti sprayed on the "
        "front in green paint. The lid is slightly askew. Slime green "
        "drips down the side, small skull-shaped trash visible peeking "
        "from the top opening. Centered square."
    ),
    "nav_shop": (
        ICON_DIR / "nav_shop.png",
        "A small wireframe shopping cart with a skull sitting inside it "
        "instead of groceries. Cart wheels are rusted. The skull has "
        "glowing slime-green eyes. Dripping graffiti style. Centered square."
    ),
    "nav_goals": (
        ICON_DIR / "nav_goals.png",
        "A bold circled 'A' anarchy symbol made of dripping spray-paint, "
        "with a slime-green lightning bolt striking through the middle of "
        "the A. Spatters of paint around it. Centered square."
    ),
    "nav_trade": (
        ICON_DIR / "nav_trade.png",
        "Two crossed bones forming an X centered behind a small grinning "
        "skull. The bones overlap at the middle, ends are splintered. "
        "Skull has hollow black eyes. Hand-inked rough illustration. "
        "Centered square."
    ),
    "nav_profile": (
        ICON_DIR / "nav_profile.png",
        "A cartoon skull mascot face — front view, grinning evil "
        "expression with crooked teeth, bone-white face, deep dark eye "
        "sockets with tiny slime-green pupils, faint cracks across the "
        "forehead. Centered square, no body, just face."
    ),
    # ───────── Hero carousel slides (3) ─────────
    # Saved into HERO_DIR — used by HeroCarousel.tsx
}

HERO_TARGETS: dict[str, tuple[Path, str]] = {
    "hero_series7": (
        HERO_DIR / "hero_series7.png",
        "A wide horizontal scene: a wild-haired thrash-metal mascot "
        "throwing the devil-horns hand sign in the foreground (left side), "
        "leather vest covered in band patches, scraggly facial hair, "
        "grinning manically. On the right side of the scene, a flying "
        "saucer UFO beams a glowing slime-green light down onto two "
        "creepy gray alien figures. Dark forest background, foggy "
        "atmosphere. Hand-inked comic style with bold black outlines, "
        "limited palette of slime green, purple, rust, bone. Wide "
        "landscape composition."
    ),
    "hero_missions": (
        HERO_DIR / "hero_missions.png",
        "A wide horizontal scene: a giant green slime-soaked skull "
        "smashing through brick wall, lightning anarchy bolts radiating "
        "outward, dripping paint everywhere. 'Goals' / 'Missions' mood. "
        "Dark cave-like background, dramatic comic style with thick "
        "black outlines, purple paint splatter. Wide landscape composition."
    ),
    "hero_trade": (
        HERO_DIR / "hero_trade.png",
        "A wide horizontal scene: two muscular grinning skeleton hands "
        "(one left, one right) reaching toward each other, each holding "
        "a glowing trading card. Slime-green energy crackles between the "
        "two cards. Dark grungy background with rusted texture, purple "
        "lightning. Hand-inked comic style with bold black outlines. "
        "Wide landscape composition."
    ),
}


def _load_ref_b64() -> str:
    """Encode the mockup reference image to base64 (once, cached)."""
    return base64.b64encode(MOCKUP_PATH.read_bytes()).decode()


def _save_clean_png(raw_bytes: bytes, out: Path, size: int, *, wide: bool = False) -> int:
    """Pillow re-save: strip metadata + ICC, resize.
    If `wide`, output as a 2:1 banner (size×size/2).
    """
    tmp = out.with_suffix(".tmp.png")
    tmp.write_bytes(raw_bytes)
    im = Image.open(tmp).convert("RGB")
    if wide:
        target = (size, size // 2)
        # Center-crop to 2:1 first to avoid squishing portrait outputs
        w, h = im.size
        target_ratio = 2.0
        cur_ratio = w / h
        if cur_ratio > target_ratio:
            new_w = int(h * target_ratio)
            left = (w - new_w) // 2
            im = im.crop((left, 0, left + new_w, h))
        elif cur_ratio < target_ratio:
            new_h = int(w / target_ratio)
            top = (h - new_h) // 2
            im = im.crop((0, top, w, top + new_h))
        im = im.resize(target, Image.LANCZOS)
    else:
        im = im.resize((size, size), Image.LANCZOS)
    clean = PngImagePlugin.PngInfo()
    im.save(out, "PNG", optimize=True, pnginfo=clean)
    tmp.unlink(missing_ok=True)
    return out.stat().st_size


async def _gen_one(key: str, out: Path, prompt: str, *, size: int,
                   ref_b64: str, hero: bool = False) -> bool:
    if out.exists() and not FORCE:
        print(f"  [skip] {out.name}")
        return False

    chat = LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"],
        session_id=f"tkk-v2-{key}",
        system_message=(
            "You are a professional metal-aesthetic illustrator. Generate "
            "ONE image matching the requested subject and STYLE. No text."
        ),
    )
    chat.with_model(
        "gemini", "gemini-3.1-flash-image-preview"
    ).with_params(modalities=["image", "text"])

    aspect_hint = (
        "wide horizontal banner (2:1 aspect ratio, much wider than tall)"
        if hero else "centered square image"
    )
    full_prompt = f"{STYLE_PREAMBLE}\n\nSUBJECT: {prompt}\n\nReturn ONE {aspect_hint}."

    msg = UserMessage(
        text=full_prompt,
        file_contents=[ImageContent(ref_b64)],
    )

    print(f"  [gen ] {out.name} ...", flush=True)
    try:
        _t, images = await chat.send_message_multimodal_response(msg)
    except Exception as e:
        print(f"  [ERR ] {out.name}: {e}")
        return False
    if not images:
        print(f"  [ERR ] {out.name}: no images returned")
        return False

    raw = base64.b64decode(images[0]["data"])
    written = _save_clean_png(raw, out, size, wide=hero)
    print(f"  [ok  ] {out.name} -> {written} bytes")
    return True


async def main():
    ref_b64 = _load_ref_b64()
    print(f"Style reference loaded: {len(ref_b64)} base64 chars")
    print(f"Force mode: {FORCE}\n")

    print(f"--- {len(TARGETS)} icons (256x256) ---")
    for key, (out, prompt) in TARGETS.items():
        await _gen_one(key, out, prompt, size=256, ref_b64=ref_b64)
        await asyncio.sleep(2)

    print(f"\n--- {len(HERO_TARGETS)} hero slides (1024x512) ---")
    for key, (out, prompt) in HERO_TARGETS.items():
        await _gen_one(key, out, prompt, size=512, ref_b64=ref_b64, hero=True)
        await asyncio.sleep(2)

    print("\nDone.")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()) or 0)

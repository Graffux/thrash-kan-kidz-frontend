"""
One-off generator for `ronch_peek_v2.png` — the "Ronchy" mascot that peeks up
from the bottom edge of the screen behind the bottom nav.

Why: the original `ronch_peek.png` was cropped above the eyes (showed only
forehead + dreadlocks + hands), so users complained they "couldn't see his
eyes." This generates a replacement composed for the same use case (face
near the bottom of the canvas, looking up) but with the FULL face — eyes
prominently visible — so when the image is positioned at the bottom of
the screen the eyes land where the user expects them.

Run from /app: `python backend/scripts/gen_ronch_peek.py`
Outputs to /app/frontend/assets/decor/ronch_peek_v2.png
"""
import asyncio
import base64
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

OUTPUT = Path("/app/frontend/assets/decor/ronch_peek_v2.png")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)


async def main() -> None:
    key = os.getenv("EMERGENT_LLM_KEY")
    if not key:
        sys.exit("EMERGENT_LLM_KEY missing")

    chat = LlmChat(
        api_key=key,
        session_id="ronch-peek-v2",
        system_message="You are a concept artist for a grunge / death-metal mobile game.",
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
        modalities=["image", "text"]
    )

    # Prompt designed so the face lands in the LOWER HALF of the canvas
    # (the image gets positioned at the bottom of the screen, so anything
    # above the face is visually cut off / behind the nav bar).
    prompt = (
        "Cartoon character peeking up from the bottom of the frame, "
        "composed so his face fills the lower 60% of the canvas. "
        "He is a Garbage-Pail-Kids style death-metal kid: messy black "
        "dreadlocks, pale-green skin with grime smears, WIDE crazed "
        "yellow-and-black eyes (eyes MUST be fully visible and prominent), "
        "exaggerated devilish grin showing crooked teeth, dripping toxic-"
        "green slime from his mouth and forehead. Hands gripping the edge "
        "below the chin as if he is hanging off the bottom of a screen. "
        "Style: hand-drawn comic ink + watercolor, heavy black outlines, "
        "punk grunge texture. Background: 100% transparent (PNG alpha). "
        "Square aspect ratio 1024x1024. NO text, NO logos, NO watermarks."
    )

    text, images = await chat.send_message_multimodal_response(UserMessage(text=prompt))
    print("text response:", (text or "")[:200])
    if not images:
        sys.exit("no image returned")

    img_bytes = base64.b64decode(images[0]["data"])
    OUTPUT.write_bytes(img_bytes)
    print(f"wrote {OUTPUT} ({len(img_bytes)} bytes)")


if __name__ == "__main__":
    asyncio.run(main())

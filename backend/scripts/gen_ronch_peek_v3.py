"""
Generate ronch_peek_v3 using the user's ACTUAL Ronch reference image.

The previous v2 was an "invent from prompt" generation that produced a
character that wasn't Ronch (wrong hair color, wrong skin tone, wrong vibe
entirely). v3 passes the user's real Ronch portrait in as a reference image
and asks Nano Banana to keep his exact look while re-composing him in a
"peeking up from the bottom of the screen" pose with hands gripping the
edge. Same Ronch, new pose.

Run from /app: `python backend/scripts/gen_ronch_peek_v3.py`
Outputs to /app/frontend/assets/decor/ronch_peek_v3.png
"""
import asyncio
import base64
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image, ImageFile
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

ImageFile.LOAD_TRUNCATED_IMAGES = True
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

REFERENCE = Path("/tmp/ronch_ref_clean.png")
OUTPUT = Path("/app/frontend/assets/decor/ronch_peek_v3.png")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)


async def main() -> None:
    key = os.getenv("EMERGENT_LLM_KEY")
    if not key:
        sys.exit("EMERGENT_LLM_KEY missing")
    if not REFERENCE.exists():
        sys.exit(f"Reference image not at {REFERENCE}")

    # base64-encode the reference for the multimodal request
    with open(REFERENCE, "rb") as f:
        ref_b64 = base64.b64encode(f.read()).decode("utf-8")

    chat = LlmChat(
        api_key=key,
        session_id="ronch-peek-v3",
        system_message="You are an expert concept artist preserving character likeness across new poses.",
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
        modalities=["image", "text"]
    )

    prompt = (
        "Use the EXACT character from the reference image — the same face, "
        "same wild tan/dirty-blonde dreadlocks (NOT black, NOT green-skinned), "
        "same white goatee scruff, same crooked asymmetric crazy eyes, same "
        "manic open-mouth grin with tongue out and sharp/crooked teeth, same "
        "denim/leather punk vest with metal pins, same TKK forehead patch. "
        "Keep him recognizable as the SAME character — do not redesign him. "
        "\n\nRe-compose him in a NEW pose: he is peeking UP from the bottom "
        "edge of a phone screen. His head and shoulders fill the lower 60% "
        "of the canvas, looking up toward the camera with a mischievous "
        "grin. Both of his hands are visible at the very bottom of the "
        "image, fingers gripping the edge like he is hanging off it. "
        "The background MUST be fully transparent (PNG alpha = 0 outside "
        "the character silhouette — no checkerboard, no solid color). "
        "\n\nStyle: stay faithful to the reference image's hyper-detailed "
        "stylized cartoon/clay-render aesthetic with heavy ink-line shadows "
        "and gritty texture. Output a square 1024x1024 PNG. NO extra text, "
        "NO logos beyond what is on his outfit."
    )

    msg = UserMessage(text=prompt, file_contents=[ImageContent(ref_b64)])
    text, images = await chat.send_message_multimodal_response(msg)
    print("text:", (text or "")[:200])
    if not images:
        sys.exit("no image returned")

    raw = base64.b64decode(images[0]["data"])
    tmp = Path("/tmp/ronch_v3_raw.bin")
    tmp.write_bytes(raw)
    print(f"raw bytes: {len(raw)}")

    # Gemini sometimes returns JPEG-in-.png. Re-encode through Pillow to
    # guarantee a clean PNG that Android AAPT2 will compile.
    img = Image.open(tmp)
    print(f"loaded: mode={img.mode} size={img.size}")
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    img.thumbnail((600, 600), Image.LANCZOS)
    img.save(OUTPUT, "PNG", optimize=True)
    print(f"wrote {OUTPUT} -> {OUTPUT.stat().st_size} bytes ({img.size})")


if __name__ == "__main__":
    asyncio.run(main())

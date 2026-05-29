"""
v4: Generate Ronch against a SOLID BLACK background, then chroma-key the
black out with a wide tolerance. This eliminates the white-halo problem
entirely because there's never any white/light antialiasing — the AA
blends to black, which is exactly the color of the app background.
Any remaining mid-grey edges blend invisibly into the dark grunge UI.
"""
import asyncio, base64, os, sys
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image, ImageFile
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

ImageFile.LOAD_TRUNCATED_IMAGES = True
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

REFERENCE = Path("/tmp/ronch_ref_clean.png")
OUTPUT = Path("/app/frontend/assets/decor/ronch_peek_v3.png")


async def main() -> None:
    key = os.getenv("EMERGENT_LLM_KEY")
    if not key or not REFERENCE.exists():
        sys.exit("missing key or reference")

    with open(REFERENCE, "rb") as f:
        ref_b64 = base64.b64encode(f.read()).decode("utf-8")

    chat = LlmChat(
        api_key=key,
        session_id="ronch-peek-v4",
        system_message="Concept artist preserving exact character likeness.",
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
        modalities=["image", "text"]
    )

    prompt = (
        "Use the EXACT character from the reference image — same dirty-blonde "
        "tan dreadlocks, same tan skin, same white goatee scruff, same wild "
        "asymmetric crazy eyes, same manic open-mouth grin showing tongue and "
        "sharp teeth, same denim/leather punk vest with metal pins, same TKK "
        "forehead patch. Keep him 100% recognizable — do not redesign.\n\n"
        "Re-compose him in a NEW pose: peeking UP from the bottom edge of a "
        "phone screen. His head and shoulders fill the lower 60% of the canvas, "
        "looking up at the camera with a mischievous grin. Both hands gripping "
        "the very bottom edge.\n\n"
        "CRITICAL — BACKGROUND: Use a 100% solid PURE BLACK (#000000) "
        "background. NO checkerboard, NO grey, NO gradient, NO white edges, "
        "NO rim lighting, NO glow around the character. The character must sit "
        "directly against pure black with no halo or highlight around the hair. "
        "Edges should blend NATURALLY into the black background — when the "
        "antialiasing fades, it should fade to black, not to white or grey.\n\n"
        "Style: stay faithful to the reference's hyper-detailed stylized "
        "cartoon clay-render aesthetic, heavy ink shadows. Square 1024x1024. "
        "NO text, NO logos beyond his outfit."
    )

    msg = UserMessage(text=prompt, file_contents=[ImageContent(ref_b64)])
    text, images = await chat.send_message_multimodal_response(msg)
    print("text:", (text or "")[:200])
    if not images:
        sys.exit("no image")

    raw = base64.b64decode(images[0]["data"])
    tmp = Path("/tmp/ronch_v4_raw.bin")
    tmp.write_bytes(raw)

    # Chroma-key the pure black background. Any pixel within tolerance
    # of #000 becomes transparent. Tolerance up to ~40 catches the
    # antialiased edge pixels too without eating any character pixels
    # (Ronch's darkest internal pixels are still well above 50).
    img = Image.open(tmp).convert("RGBA")
    img.thumbnail((600, 600), Image.LANCZOS)
    import numpy as np
    arr = np.array(img)
    r, g, b = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)
    brightness = (r + g + b) // 3
    # Hard transparent: brightness <= 25
    # Soft fade-out:  brightness 26..60 -> proportional alpha so the
    # silhouette edge smoothly blends to transparent without a white
    # halo (because there IS no white — only varying levels of black).
    alpha = np.where(brightness <= 25, 0,
              np.where(brightness >= 60, 255,
                       ((brightness - 25) * 255 // 35))).astype(np.uint8)
    arr[:, :, 3] = alpha
    Image.fromarray(arr, "RGBA").save(OUTPUT, "PNG", optimize=True)

    n_trans = int((alpha == 0).sum())
    n_opaque = int((alpha == 255).sum())
    n_partial = int(((alpha > 0) & (alpha < 255)).sum())
    print(f"transparent={n_trans} opaque={n_opaque} partial={n_partial}")
    print(f"wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes)")


if __name__ == "__main__":
    asyncio.run(main())

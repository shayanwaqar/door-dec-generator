import io
import os
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont

# Locate fonts directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(BASE_DIR, "static", "fonts")

# Default font (fallback if specific font can't be loaded)
# Replace with whatever font you prefer:
DEFAULT_FONT_PATH = os.path.join(FONT_DIR, "PressStart2P-Regular.ttf")


# ------------------------------
# FONT LOADING
# ------------------------------

def _load_font(size: int):
    """Try to load TTF font; fallback to Pillow default."""
    try:
        if os.path.exists(DEFAULT_FONT_PATH):
            return ImageFont.truetype(DEFAULT_FONT_PATH, size=size)
    except Exception:
        pass
    return ImageFont.load_default()


# ------------------------------
# IMAGE RESIZING
# ------------------------------

def _resize_image_if_needed(img: Image.Image, max_width=1000) -> Image.Image:
    """Resize template images so processing is faster and consistent."""
    if img.width <= max_width:
        return img
    ratio = max_width / img.width
    new_size = (max_width, int(img.height * ratio))
    return img.resize(new_size, Image.LANCZOS)


# ------------------------------
# DRAW CENTERED TEXT WITH BORDER
# ------------------------------

def _draw_centered_text(
    img: Image.Image,
    text: str,
    font_color: str = "#FFFFFF",
    text_position: str = "center",
    stroke_width: int = 3,
    stroke_fill: str = "#000000",
    width_margin_ratio: float = 0.9,
) -> Image.Image:
    """
    Draw text in the center of the image with auto-fit and stroke border.
    """

    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)

    # Font size boundaries
    MAX_FS = int(img.height * 0.12)  # ~12% of height
    MIN_FS = 18                      # Prevent tiny unreadable text

    # Start with largest font size
    size = MAX_FS
    font = _load_font(size)

    # Fit name inside allowed width
    max_width_allowed = img.width * width_margin_ratio

    while size >= MIN_FS:
        font = _load_font(size)
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
        text_w = bbox[2] - bbox[0]
        if text_w <= max_width_allowed:
            break
        size -= 2

    # Calculate Y coordinate based on text_position
    x = img.width // 2
    if text_position == "top":
        # Position text with a 5% margin from the top
        y = int(img.height * 0.05)
        anchor = "ma"  # Middle-aligned horizontally, Ascender-aligned vertically
    elif text_position == "bottom":
        # Position text with a 5% margin from the bottom
        y = int(img.height * 0.95)
        anchor = "md"  # Middle-aligned horizontally, Descender-aligned vertically
    else:  # "center"
        y = img.height // 2
        anchor = "mm"  # Middle-aligned horizontally and vertically

    draw.text(
        (x, y),
        text,
        font=font,
        fill=font_color,
        anchor=anchor,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )

    return img


# ------------------------------
# PREVIEW GENERATION
# ------------------------------

def generate_preview_image(file_obj, name: str, font_color: str, text_position: str) -> bytes:
    """Generate one preview PNG based on first template + first name."""

    img = Image.open(file_obj.stream)
    img = _resize_image_if_needed(img)

    # White text, black outline works best visually
    img = _draw_centered_text(img, name, font_color, text_position, stroke_width=3)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ------------------------------
# BATCH IMAGE GENERATION
# ------------------------------

def generate_batch_images(
    files,
    names: List[str],
    font_color: str,
    text_position: str,
) -> List[Tuple[str, bytes]]:
    """
    Generate all name tags and return list of (filename, image_bytes).
    """

    # Load all uploaded templates into memory & resize for consistency
    templates = []
    for f in files:
        img = Image.open(f.stream)
        img = _resize_image_if_needed(img)
        templates.append(img.copy())

    results = []
    tcount = len(templates)

    for idx, name in enumerate(names):
        template = templates[idx % tcount].copy()
        img = _draw_centered_text(template, name, font_color, text_position, stroke_width=3)

        # Safe filename
        safe = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip()
        if not safe:
            safe = f"resident_{idx+1}"

        filename = f"{idx+1:03d}_{safe}.png"

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        results.append((filename, buf.getvalue()))

    return results

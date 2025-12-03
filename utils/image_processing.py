import io
import os
from typing import List, Tuple, Union

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

def _draw_text_at_position(
    img: Image.Image,
    text: str,
    position_xy: Tuple[int, int],
    font_color: str = "#FFFFFF",
    stroke_width: int = 3,
    stroke_fill: str = "#000000",
    width_margin_ratio: float = 0.9,
) -> Image.Image:
    """
    Draw text at a specific (x, y) coordinate with auto-fit font and stroke.
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

    draw.text(
        position_xy,
        text,
        font=font,
        fill=font_color,
        anchor="mm",  # Middle-aligned anchor
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )

    return img


# ------------------------------
# BATCH IMAGE GENERATION
# ------------------------------

def generate_batch_images(
    files,
    names: List[str],
    font_color: str,
    positions: Union[dict, None] = None,
) -> List[Tuple[str, bytes]]:
    """
    Generate all name tags and return list of (filename, image_bytes).
    """

    # Load all uploaded templates into memory & resize for consistency
    templates = []
    for file_obj in files:
        img = Image.open(file_obj.stream)
        img = _resize_image_if_needed(img)
        templates.append(img.copy())

    results = []
    tcount = len(templates)
    if not tcount:
        return []

    for idx, name in enumerate(names):
        t_idx = idx % tcount
        template = templates[t_idx].copy()

        # Default: center
        cx = template.width // 2
        cy = template.height // 2

        # If manual position provided for this template, use it
        if positions and str(t_idx) in positions:
            frac = positions[str(t_idx)]
            try:
                fx = float(frac.get("x", 0.5))
                fy = float(frac.get("y", 0.5))
                cx = int(fx * template.width)
                cy = int(fy * template.height)
            except (ValueError, TypeError):
                pass  # Keep default on parsing error

        img = _draw_text_at_position(template, name, (cx, cy), font_color=font_color, stroke_width=3)

        # Safe filename
        safe = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip()
        if not safe:
            safe = f"resident_{idx+1}"

        filename = f"{idx+1:03d}_{safe}.png"

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        results.append((filename, buf.getvalue()))

    return results

import io
import os
import re
from typing import List, Tuple, Union

from PIL import Image, ImageDraw, ImageFont

# Locate fonts directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(BASE_DIR, "static", "fonts")


# ------------------------------
# FONT LOADING
# ------------------------------

def get_available_fonts() -> dict:
    """
    Scan the font directory and return a dictionary of font names to file paths.
    """
    fonts = {}
    if not os.path.isdir(FONT_DIR):
        return fonts
    for filename in os.listdir(FONT_DIR):
        if filename.lower().endswith((".ttf", ".otf")):
            font_path = os.path.join(FONT_DIR, filename)
            
            # --- Advanced Font Name Cleaning ---
            # 1. Get the base name without extension
            name = os.path.splitext(filename)[0]
            
            # 2. Split on common metadata keywords like "Variable" or "Italic"
            # e.g., "OpenSans-VariableFont_wdth,wght" -> "OpenSans"
            name = re.split(r'[_-]?(Variable|Italic|Static|VF|Flex)', name, maxsplit=1, flags=re.IGNORECASE)[0]

            # 3. Insert spaces before uppercase letters in camelCase, e.g., "OpenSans" -> "Open Sans"
            name = re.sub(r'(?<!^)(?=[A-Z])', ' ', name)

            # 4. Replace separators and title-case the result
            font_name = name.replace("-", " ").replace("_", " ").strip().title()
            fonts[font_name] = font_path
    return fonts


AVAILABLE_FONTS = get_available_fonts()
DEFAULT_FONT_NAME = next(iter(AVAILABLE_FONTS), None)

# Define the desired default font and set it if available, otherwise fall back to the first font found.
DESIRED_DEFAULT_FONT = "Sports World"
DEFAULT_FONT_NAME = DESIRED_DEFAULT_FONT if DESIRED_DEFAULT_FONT in AVAILABLE_FONTS else next(iter(AVAILABLE_FONTS), None)


def _load_font(font_name: str, size: int):
    """Load a TTF font by name; fallback to Pillow default."""
    font_path = AVAILABLE_FONTS.get(font_name)
    try:
        if font_path and os.path.exists(font_path):
            return ImageFont.truetype(font_path, size=size)
    except IOError:
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
    font_name: str,
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
    font = _load_font(font_name, size)

    # Fit name inside allowed width
    max_width_allowed = img.width * width_margin_ratio

    while size >= MIN_FS:
        font = _load_font(font_name, size)
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
# PREVIEW IMAGE GENERATION
# ------------------------------

def generate_preview_image(
    file_obj,
    name: str,
    font_color: str,
    font_name: str,
    position: dict,
) -> bytes:
    """Generate one preview PNG based on first template, first name, and selected options."""
    img = Image.open(file_obj.stream)
    img = _resize_image_if_needed(img)

    # Calculate position from fractional coordinates
    try:
        fx = float(position.get("x", 0.5))
        fy = float(position.get("y", 0.5))
        cx = int(fx * img.width)
        cy = int(fy * img.height)
    except (ValueError, TypeError):
        cx, cy = img.width // 2, img.height // 2

    img = _draw_text_at_position(img, name, (cx, cy), font_name, font_color, stroke_width=3)

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
    font_name: str,
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

        img = _draw_text_at_position(template, name, (cx, cy), font_name, font_color=font_color, stroke_width=3)

        # Safe filename
        safe = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip()
        if not safe:
            safe = f"resident_{idx+1}"

        filename = f"{idx+1:03d}_{safe}.png"

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        results.append((filename, buf.getvalue()))

    return results

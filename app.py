import io
import zipfile
import json
from datetime import datetime

from flask import Flask, render_template, request, send_file, abort

from utils.image_processing import generate_batch_images, generate_preview_image, AVAILABLE_FONTS, DEFAULT_FONT_NAME

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", fonts=AVAILABLE_FONTS)


def _parse_names(raw: str):
    if not raw:
        return []
    names = [line.strip() for line in raw.splitlines()]
    # remove empty lines
    return [n for n in names if n]


@app.route("/preview", methods=["POST"])
def preview():
    files = request.files.getlist("images")
    if not files:
        abort(400, "Please upload at least one image for a preview.")

    raw_names = request.form.get("names", "")
    names = _parse_names(raw_names)
    if not names:
        abort(400, "Please enter at least one name for a preview.")

    font_color = request.form.get("font_color", "#FFFFFF")
    font_name = request.form.get("font_name", DEFAULT_FONT_NAME)
    positions_json = request.form.get("positions", "{}")
    try:
        positions = json.loads(positions_json)
        # Position for the first image (index "0")
        position = positions.get("0", {"x": 0.5, "y": 0.5})
    except json.JSONDecodeError:
        position = {"x": 0.5, "y": 0.5}

    img_bytes = generate_preview_image(files[0], names[0], font_color, font_name, position)

    return send_file(io.BytesIO(img_bytes), mimetype="image/png")


@app.route("/generate", methods=["POST"])
def generate():
    files = request.files.getlist("images")
    raw_names = request.form.get("names", "")
    font_color = request.form.get("font_color", "#FFFFFF")
    font_name = request.form.get("font_name", DEFAULT_FONT_NAME)
    positions_json = request.form.get("positions", "")
    positions = {}
    if positions_json:
        try:
            positions = json.loads(positions_json)  # keys like "0", "1", ...
        except json.JSONDecodeError:
            positions = {}

    names = _parse_names(raw_names)
    if not files:
        abort(400, "Please upload at least one image.")
    if not names:
        abort(400, "Please provide at least one name.")

    # limit for sanity (simple guardrail)
    if len(names) > 300:
        abort(400, "Too many names. Please limit to 300 per batch.")

    images_data = generate_batch_images(files, names, font_color, font_name, positions=positions)

    # build ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for filename, img_bytes in images_data:
            zip_file.writestr(filename, img_bytes)
    zip_buffer.seek(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"door_tags_{timestamp}.zip"

    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name=zip_name,
        mimetype="application/zip",
    )

if __name__ == "__main__":
    app.run(debug=True, port=5050)

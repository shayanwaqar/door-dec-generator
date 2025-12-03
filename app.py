import io
import zipfile
import json
from datetime import datetime

from flask import Flask, render_template, request, send_file, abort

from utils.image_processing import generate_batch_images

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


def _parse_names(raw: str):
    if not raw:
        return []
    names = [line.strip() for line in raw.splitlines()]
    # remove empty lines
    return [n for n in names if n]


@app.route("/generate", methods=["POST"])
def generate():
    files = request.files.getlist("images")
    raw_names = request.form.get("names", "")
    font_color = request.form.get("font_color", "#000000")
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

    images_data = generate_batch_images(files, names, font_color, positions=positions)

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

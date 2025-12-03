import io
import zipfile
from datetime import datetime

from flask import Flask, render_template, request, send_file, abort

from utils.image_processing import generate_preview_image, generate_batch_images

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


@app.route("/preview", methods=["POST"])
def preview():
    files = request.files.getlist("images")
    raw_names = request.form.get("names", "")
    font_color = request.form.get("font_color", "#000000")

    names = _parse_names(raw_names)
    if not files or not names:
        abort(400, "Need at least one image and one name for preview.")

    # use first image + first name
    first_file = files[0]
    first_name = names[0]

    img_bytes = generate_preview_image(first_file, first_name, font_color)

    return send_file(
        io.BytesIO(img_bytes),
        mimetype="image/png",
        download_name="preview.png",
    )


@app.route("/generate", methods=["POST"])
def generate():
    files = request.files.getlist("images")
    raw_names = request.form.get("names", "")
    font_color = request.form.get("font_color", "#000000")

    names = _parse_names(raw_names)
    if not files:
        abort(400, "Please upload at least one image.")
    if not names:
        abort(400, "Please provide at least one name.")

    # limit for sanity (simple guardrail)
    if len(names) > 300:
        abort(400, "Too many names. Please limit to 300 per batch.")

    images_data = generate_batch_images(files, names, font_color)

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
    app.run(debug=True)

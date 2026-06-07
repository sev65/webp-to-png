import io
import os
import uuid
import zipfile
from flask import Flask, jsonify, render_template, request, send_file

from PIL import Image

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB limit


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/convert", methods=["POST"])
def convert():
    files = request.files.getlist("files")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No files provided"}), 400

    results = []
    for f in files:
        if not f.filename.lower().endswith(".webp"):
            results.append({"name": f.filename, "error": "Not a .webp file"})
            continue
        try:
            img = Image.open(f.stream).convert("RGBA")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            token = uuid.uuid4().hex
            _store[token] = (os.path.splitext(f.filename)[0] + ".png", buf.read())
            results.append({"name": f.filename, "token": token})
        except Exception as e:
            results.append({"name": f.filename, "error": str(e)})

    return jsonify({"results": results})


@app.route("/download/<token>")
def download(token):
    entry = _store.pop(token, None)
    if entry is None:
        return "Not found or already downloaded", 404
    name, data = entry
    return send_file(io.BytesIO(data), mimetype="image/png", download_name=name, as_attachment=True)


@app.route("/download-zip", methods=["POST"])
def download_zip():
    tokens = request.json.get("tokens", [])
    if not tokens:
        return "No tokens", 400

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for token in tokens:
            entry = _store.pop(token, None)
            if entry:
                name, data = entry
                zf.writestr(name, data)
    buf.seek(0)
    return send_file(buf, mimetype="application/zip", download_name="converted.zip", as_attachment=True)


# In-memory store: token -> (filename, bytes)
_store: dict[str, tuple[str, bytes]] = {}

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

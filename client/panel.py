import io
import logging
import threading
import time
from pathlib import Path

from flask import Flask, Response, jsonify
from PIL import Image, ImageDraw

import config
import status
from oled import oled
from oled.face import Face

SCALE = 4
PAGE = (Path(__file__).parent / "panel.html").read_text(encoding="utf-8")

app = Flask(__name__)
logging.getLogger("werkzeug").setLevel(logging.ERROR) # one line per request would bury the useful logs

_display = None
# its own Face, so the preview blinks and looks around like the OLED without touching its state
_face = None
_face_lock = threading.Lock()


@app.get("/")
def index():
    return Response(PAGE, mimetype="text/html")


@app.get("/face.png")
def face_png():
    name, text = _display.state
    img = Image.new("1", (oled.W, oled.H), 0)
    with _face_lock:
        getattr(_face, name)(ImageDraw.Draw(img), time.time(), text)
    buf = io.BytesIO()
    img.resize((oled.W * SCALE, oled.H * SCALE), Image.NEAREST).save(buf, "PNG")
    return Response(buf.getvalue(), mimetype="image/png", headers={"Cache-Control": "no-store"})


@app.get("/api/state")
def state():
    name, text = _display.state
    return jsonify(state=name, text=text, since=_display.since, now=time.time(), **status.snapshot())


def start(display):
    global _display, _face
    _display, _face = display, Face()
    threading.Thread(
        target=lambda: app.run(host=config.PANEL_HOST, port=config.PANEL_PORT, threaded=True, use_reloader=False),
        name="panel",
        daemon=True,
    ).start()
    print(f"Panel: http://{config.PANEL_HOST}:{config.PANEL_PORT}", flush=True)

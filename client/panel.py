import io
import logging
import threading
import time
from pathlib import Path

from flask import Flask, Response, jsonify, redirect, request
from PIL import Image, ImageDraw

import config
import status
import wifi
from oled import oled
from oled.face import Face

SCALE = 4
PAGE = (Path(__file__).parent / "panel.html").read_text(encoding="utf-8")
WIFI_PAGE = (Path(__file__).parent / "wifi.html").read_text(encoding="utf-8")

app = Flask(__name__)
logging.getLogger("werkzeug").setLevel(logging.ERROR) # one line per request would bury the useful logs

_display = None
# its own Face, so the preview blinks and looks around like the OLED without touching its state
_face = None
_face_lock = threading.Lock()


@app.before_request
def captive_portal():
    """on the hotspot every name resolves to us, so a phone checking for internet lands on the wi-fi page"""
    wifi.visit()
    if wifi.hotspot_active() and request.host.split(":")[0] != config.HOTSPOT_IP:
        return redirect(f"http://{config.HOTSPOT_IP}/wifi")


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


@app.get("/wifi")
def wifi_page():
    return Response(WIFI_PAGE, mimetype="text/html")


@app.get("/api/wifi")
def wifi_state():
    return jsonify(wifi.snapshot())


@app.post("/api/wifi/scan")
def wifi_scan():
    return jsonify(networks=wifi.scan())


@app.post("/api/wifi/connect")
def wifi_connect():
    body = request.get_json(silent=True) or {}
    ssid, password = (body.get("ssid") or "").strip(), body.get("password") or ""
    if not ssid:
        return jsonify(error="podaj nazwę sieci"), 400
    if password and len(password) < 8:
        return jsonify(error="hasło Wi-Fi ma co najmniej 8 znaków"), 400
    wifi.connect(ssid, password)
    return jsonify(ok=True), 202


@app.post("/api/wifi/forget")
def wifi_forget():
    name = (request.get_json(silent=True) or {}).get("name")
    if not name:
        return jsonify(error="brak nazwy"), 400
    wifi.forget(name)
    return jsonify(ok=True)


def start(display):
    global _display, _face
    _display, _face = display, Face()
    threading.Thread(
        target=lambda: app.run(host=config.PANEL_HOST, port=config.PANEL_PORT, threaded=True, use_reloader=False),
        name="panel",
        daemon=True,
    ).start()
    print(f"Panel: http://{config.PANEL_HOST}:{config.PANEL_PORT}", flush=True)

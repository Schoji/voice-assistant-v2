"""bluetooth speaker: pairs through bluetoothctl, plays through pipewire

Aleksy keeps talking through the HAT whenever the chosen speaker is off or out
of range, and reconnects it in the background once it comes back. The choice
lives in the home dir because every deploy rsyncs over the client dir.
"""
import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path

import config

STATE_FILE = Path.home() / ".local/state/aleksy/audio.json"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
# pw-cat finds the user's pipewire through this, a system service does not get it
os.environ.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")

_lock = threading.Lock() # bluetoothctl commands one at a time
_state = {"speaker": None, "connected": False, "sink": None, "busy": None, "error": None, "devices": []}
_last_reconnect = 0.0


def _ctl(*args, timeout=None):
    """runs bluetoothctl non-interactively; --timeout keeps it waiting for scan/pair/connect to finish"""
    cmd = ["bluetoothctl"] + (["--timeout", str(timeout)] if timeout else []) + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=(timeout or 10) + 10)
    return ANSI.sub("", r.stdout + r.stderr)


def _info(mac):
    info = {"mac": mac, "name": mac, "paired": False, "connected": False, "audio": False}
    for line in _ctl("info", mac).splitlines():
        key, _, value = line.strip().partition(": ")
        if key == "Name":
            info["name"] = value
        elif key in ("Paired", "Connected"):
            info[key.lower()] = value == "yes"
        elif (key == "Icon" and value.startswith("audio")) or (key == "UUID" and value.startswith("Audio Sink")):
            info["audio"] = True
    return info


def _devices():
    """named devices only, a bare address is some phone or beacon nobody wants to pick"""
    found = []
    for line in _ctl("devices").splitlines():
        m = re.match(r"Device (\S+) (.*)", line.strip())
        if m and m.group(2) != m.group(1).replace(":", "-"):
            found.append(_info(m.group(1)))
    return sorted(found, key=lambda d: (not d["connected"], not d["paired"], not d["audio"], d["name"].lower()))


def _find_sink(mac):
    """the pipewire node wireplumber made for the speaker, None until the a2dp profile is up"""
    try:
        nodes = json.loads(subprocess.run(["pw-dump"], capture_output=True, text=True, timeout=10).stdout or "[]")
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None
    for node in nodes:
        props = (node.get("info") or {}).get("props") or {}
        if props.get("media.class") == "Audio/Sink" and props.get("api.bluez5.address", "").upper() == mac.upper():
            return props.get("node.name")
    return None


def _load():
    try:
        return json.loads(STATE_FILE.read_text()).get("speaker")
    except (OSError, ValueError):
        return None


def _save(speaker):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"speaker": speaker}))


def _refresh():
    global _last_reconnect
    speaker = _state["speaker"]
    if not speaker:
        _state.update(connected=False, sink=None)
        return
    info = _info(speaker["mac"])
    if not info["connected"] and time.time() - _last_reconnect >= config.BT_RECONNECT_EVERY:
        # speakers go to sleep or get switched off, so keep knocking
        _last_reconnect = time.time()
        _ctl("connect", speaker["mac"], timeout=10)
        info = _info(speaker["mac"])
    _state.update(connected=info["connected"], sink=_find_sink(speaker["mac"]) if info["connected"] else None)


def _watch():
    with _lock:
        _state["devices"] = _devices()
    while True:
        try:
            with _lock:
                _refresh()
        except (OSError, subprocess.TimeoutExpired) as e:
            print(f"Bluetooth: {e}", flush=True)
        time.sleep(config.BT_CHECK_EVERY)


def _background(busy, work):
    def run():
        with _lock:
            _state.update(busy=busy, error=None)
            try:
                work()
            except (OSError, subprocess.TimeoutExpired) as e:
                print(f"Bluetooth: {e}", flush=True)
                _state["error"] = str(e)
            finally:
                _state["busy"] = None
    _state.update(busy=busy, error=None)
    threading.Thread(target=run, name="bt", daemon=True).start()


def scan():
    def work():
        _ctl("scan", "on", timeout=config.BT_SCAN_SECONDS)
        _state["devices"] = _devices()
    _background("szukam urządzeń (włącz w głośniku tryb parowania)", work)


def use(mac):
    def work():
        global _last_reconnect
        info = _info(mac)
        if not info["paired"]:
            _ctl("scan", "on", timeout=5) # bluez only pairs with something it has seen recently
            out = _ctl("pair", mac, timeout=30)
            if not _info(mac)["paired"]:
                print(f"Bluetooth: parowanie z {mac} nieudane: {out.strip()[-200:]}", flush=True)
                _state["error"] = f"Nie udało się sparować z {info['name']}. Czy jest w trybie parowania?"
                return
        _ctl("trust", mac) # lets the speaker reconnect by itself when it wakes up
        _ctl("connect", mac, timeout=15)
        info = _info(mac)
        _state["speaker"] = {"mac": mac, "name": info["name"]}
        _save(_state["speaker"])
        _last_reconnect = time.time()
        if info["connected"]:
            time.sleep(2) # wireplumber needs a moment to create the sink
            print(f"Bluetooth: gram przez {info['name']}", flush=True)
        else:
            _state["error"] = f"Sparowano z {info['name']}, ale nie udało się połączyć. Spróbuję ponownie za chwilę."
        _refresh()
        _state["devices"] = _devices()
    _background("łączę z głośnikiem", work)


def stop_using():
    def work():
        speaker = _state["speaker"]
        _state["speaker"] = None
        _save(None)
        if speaker:
            _ctl("disconnect", speaker["mac"], timeout=5)
        _refresh()
        _state["devices"] = _devices()
    _background("wracam do głośnika Aleksego", work)


def forget(mac):
    def work():
        if _state["speaker"] and _state["speaker"]["mac"] == mac:
            _state["speaker"] = None
            _save(None)
        _ctl("remove", mac)
        _refresh()
        _state["devices"] = _devices()
    _background("usuwam urządzenie", work)


def sink():
    """where to play right now: a pipewire node name, or None for the HAT"""
    return _state["sink"]


def snapshot():
    return dict(_state)


def start():
    _state["speaker"] = _load()
    threading.Thread(target=_watch, name="bt-watch", daemon=True).start()

import threading
import time
import traceback

from PIL import Image, ImageDraw
from smbus2 import SMBus

from . import oled
from .face import STATES, Face

FPS = 25
RETRY_DELAY = 1.0
MAX_RETRY_DELAY = 60.0


class FaceDisplay:
    def __init__(self, state="idle", text=""):
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self.set(state, text)

    def set(self, state, text=""):
        if state not in STATES:
            raise ValueError(f"nieznany stan: {state} (dostępne: {', '.join(STATES)})")
        with self._lock:
            self._state = (state, text)

    @property
    def state(self):
        with self._lock:
            return self._state

    def start(self):
        if self._thread and self._thread.is_alive():
            return self
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="oled-face", daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join()
            self._thread = None

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()

    def _run(self):
        face = Face()
        delay, last_error = RETRY_DELAY, None
        while not self._stop.is_set():
            try:
                with SMBus(oled.BUS) as bus:
                    oled.init(bus)
                    if last_error:
                        print("oled: wyświetlacz znowu działa", flush=True)
                        delay, last_error = RETRY_DELAY, None
                    try:
                        self._loop(bus, face)
                    finally:
                        oled.clear(bus)
                        oled.off(bus)
            except Exception as e:
                error = f"{type(e).__name__}: {e}"
                if error != last_error:
                    print(f"oled: błąd wyświetlania, ponawiam do skutku (co najwyżej co {MAX_RETRY_DELAY:.0f} s)", flush=True)
                    traceback.print_exc()
                    last_error = error
                self._stop.wait(delay)
                delay = min(delay * 2, MAX_RETRY_DELAY)

    def _loop(self, bus, face):
        while not self._stop.is_set():
            now = time.time()
            name, text = self.state
            img = Image.new("1", (oled.W, oled.H), 0)
            getattr(face, name)(ImageDraw.Draw(img), now, text)
            oled.show(bus, img)
            self._stop.wait(max(0, 1 / FPS - (time.time() - now)))

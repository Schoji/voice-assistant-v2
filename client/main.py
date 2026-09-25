import time, signal, sys
from listener import mww, feats, vad, reset
from audio import open_mic, play_filler_word, play_startup_word, play_thinking_word
from transport import send_file
from oled.face_display import FaceDisplay
from websockets.exceptions import WebSocketException
import config
import asyncio

face = FaceDisplay().start()
play_startup_word()
mic = open_mic()

signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

CHUNK = config.CHUNK
SILENCE_LIMIT = config.SILENCE_LIMIT
START_LIMIT = config.START_LIMIT
MAX_FRAMES = config.MAX_FRAMES
COOLDOWN = config.COOLDOWN
SLEEP_AFTER = config.SLEEP_AFTER
ERROR_HOLD = config.ERROR_HOLD

recording = False
speech_started = False
frames, silence = [], 0
last = 0.0
idle_since = time.time()

print("Słucham...", flush=True)

try:
    while data := mic.stdout.read(CHUNK * 10):
        if not recording:
            state = face.state[0]
            waited = time.time() - idle_since
            if state == "error" and waited >= ERROR_HOLD:
                face.set("idle")
            elif state == "idle" and waited >= SLEEP_AFTER:
                face.set("sleep")

        for i in range(0, len(data), CHUNK):
            block = data[i:i + CHUNK]
            if len(block) < CHUNK:
                continue

            if not recording:
                for f in feats.process_streaming(block):
                    prob = mww.process_streaming_prob(f)
                    if prob > 0.5:
                        print(f"  prob={prob:.4f}", flush=True)
                    if prob > 0.97 and time.time() - last > COOLDOWN:
                        last = time.time()
                        print("wake!", flush=True)
                        face.set("listen")
                        play_filler_word()
                        mic.kill()
                        mic = open_mic()
                        last = time.time()
                        reset()
                        recording, frames, silence = True, [], 0
                        speech_started = False
            else:
                frames.append(block)
                prob = vad.process_10ms(block)
                if prob >= 0:
                    if prob >= 0.5:
                        speech_started = True
                        silence = 0
                    else:
                        silence += 1

                limit = SILENCE_LIMIT if speech_started else START_LIMIT
                if silence >= limit or len(frames) >= MAX_FRAMES:
                    face.set("think")
                    play_thinking_word()
                    try:
                        asyncio.run(send_file(frames, on_audio=lambda: face.set("talk")))
                        face.set("idle")
                    except TimeoutError:
                        face.set("error", "timeout")
                    except (OSError, WebSocketException) as e:
                        print(f"  (brak połączenia z serwerem: {e})", flush=True)
                        face.set("error", "brak serwera")
                    idle_since = time.time()
                    mic.kill()
                    mic = open_mic()
                    recording = False
                    reset()
finally:
    face.stop()
    mic.kill()
    mic.wait()

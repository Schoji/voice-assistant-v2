from aleksy_protocol.wire import MIC_RATE

SERVER_URI = "ws://100.68.78.95:8000"

MIC = ["arecord", "-D", "default", "-q",
       "-r", str(MIC_RATE), "-c", "1", "-f", "S16_LE", "-t", "raw"]

OUT_DEVICE = "default"

FILLER_WORD = "assets/tak.wav"

STARTUP_WORD = "assets/zainicjalizowany.wav"

# played once the user stops talking, to cover the wait for the server
THINKING_WORDS = [
    "assets/chwileczke.wav",
    "assets/momencik.wav",
    "assets/sekunda.wav",
    "assets/lemon.wav",
]

CHUNK = 320              # models need 10ms per execution. 160 000 * 10 ms = 160 samples * 2 bytes = 320 bytes
SILENCE_LIMIT = 80
START_LIMIT = 250
MAX_FRAMES = 1000
COOLDOWN = 1.5 # cooldown so this cringelord doesn't detect the wakeword 10000000 times a second

SLEEP_AFTER = 30 # seconds of waiting for the wakeword before the face falls asleep
ERROR_HOLD = 3 # seconds the error face stays up before going back to idle

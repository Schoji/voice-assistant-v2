from aleksy_protocol.wire import MIC_RATE

# tried in order: mac mini first, piotr's macbook as a fallback
SERVER_URIS = [
    "ws://100.99.241.45:8000",
    "ws://100.68.78.95:8000",
]
CONNECT_TIMEOUT = 3
# the server sends audio only once the whole answer is synthesized
RESPONSE_TIMEOUT = 60

MIC = ["arecord", "-D", "default", "-q",
       "-r", str(MIC_RATE), "-c", "1", "-f", "S16_LE", "-t", "raw"]

OUT_DEVICE = "default"

# set on every start: alsactl store needs sudo, so the mixer level does not survive a reboot
SPEAKER_CARD = "wm8960soundcard"
SPEAKER_VOLUME = 113 # -8 dB out of 0-127, 0 dB (121) already distorts

# web panel with the face, conversation history, timings and logs
PANEL_HOST = "0.0.0.0"
PANEL_PORT = 5000
PANEL_HISTORY = 50
PANEL_LOG_LINES = 300

# own hotspot when no known network is around, the panel then lets you pick a new one (wifi.py)
WIFI_IFACE = "wlan0"
HOTSPOT_SSID = "Aleksy"
# written by deploy/client/setup-wifi.sh and kept out of the repo, without it there is no hotspot
HOTSPOT_PASSWORD_FILE = "/etc/aleksy/hotspot-password"
HOTSPOT_IP = "10.42.0.1" # NetworkManager's default for shared connections, setup-wifi.sh points dns here
HOTSPOT_AFTER = 45 # seconds without a network before the hotspot goes up, NetworkManager needs a moment after boot
HOTSPOT_RETRY = 180 # how often the hotspot steps aside to try the saved networks again, unless someone is using it
WIFI_CHECK_EVERY = 5

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
# the alexa model peaks around 0.75-0.9 when you say "Aleksy", background noise stays below ~0.65
WAKE_THRESHOLD = 0.75
COOLDOWN = 1.5 # cooldown so this cringelord doesn't detect the wakeword 10000000 times a second

SLEEP_AFTER = 30 # seconds of waiting for the wakeword before the face falls asleep
ERROR_HOLD = 3 # seconds the error face stays up before going back to idle

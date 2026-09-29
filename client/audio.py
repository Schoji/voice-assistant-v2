import random
import subprocess
from aleksy_protocol.wire import TTS_RATE
import bt
import config


## this piece of shit opens arecord as subprocess and takes it's output to a mic variable
def open_mic():
    return subprocess.Popen(config.MIC, stdout=subprocess.PIPE)


def set_volume():
    try:
        subprocess.run(["amixer", "-q", "-c", config.SPEAKER_CARD, "sset", "Speaker", str(config.SPEAKER_VOLUME)], check=True)
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"  (nie udało się ustawić głośności: {e})", flush=True)


def _file_player(path):
    """the bluetooth speaker when one is connected, the HAT otherwise"""
    sink = bt.sink()
    if sink:
        return ["pw-cat", "--playback", "--target", sink, path]
    return ["aplay", "-q", "-D", config.OUT_DEVICE, path]


def play_word(path):
    try:
        subprocess.run(_file_player(path), check=True)
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"  (nie udało się odtworzyć {path}: {e})", flush=True)


def play_filler_word():
    """plays out the filler word so we know that aleksy hears us
    """
    play_word(config.FILLER_WORD)


def play_startup_word():
    """announces that the service is up, before the mic opens so we don't hear ourselves
    """
    play_word(config.STARTUP_WORD)


def play_thinking_word():
    """picks one at random and starts it without waiting

    Popen, not run: blocking here would just add its length to the wait the
    word is supposed to cover.
    """
    path = random.choice(config.THINKING_WORDS)
    try:
        return subprocess.Popen(_file_player(path))
    except OSError as e:
        print(f"  (nie udało się odtworzyć {path}: {e})", flush=True)


def open_player():
    sink = bt.sink()
    if sink:
        cmd = ["pw-cat", "--playback", "--target", sink, "--raw",
               "--rate", str(TTS_RATE), "--channels", "1", "--format", "s16", "-"]
    else:
        cmd = ["aplay", "-D", config.OUT_DEVICE, "-r", str(TTS_RATE), "-c", "1", "-f", "S16_LE", "-t", "raw"]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)

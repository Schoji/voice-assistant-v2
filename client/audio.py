import subprocess
from aleksy_protocol.wire import TTS_RATE
import config


## this piece of shit opens arecord as subprocess and takes it's output to a mic variable
def open_mic():
    return subprocess.Popen(config.MIC, stdout=subprocess.PIPE)


def play_filler_word():
    """plays out the filler word so we know that aleksy hears us
    """
    try:
        subprocess.run(["aplay", "-q", "-D", config.OUT_DEVICE, config.FILLER_WORD], check=True)
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"  (nie udało się odtworzyć {config.FILLER_WORD}: {e})", flush=True)


def open_player():
    return subprocess.Popen(
                            ["aplay", "-D", config.OUT_DEVICE, "-r", str(TTS_RATE), "-c", "1", "-f", "S16_LE", "-t", "raw"],
                            stdin=subprocess.PIPE,
                        )

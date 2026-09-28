import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

HOST = "0.0.0.0"
PORT = 8000

STT_MODEL = "mlx-community/Qwen3-ASR-0.6B-8bit"
TTS_MODEL = "mlx-community/OmniVoice-bf16"
LLM_MODEL = "mlx-community/Qwen3-8B-4bit"
MAX_TOKENS = 100
# TTS takes ~0.055 s per character on the M2 mini at 16 steps, this keeps the wait well under the client timeout
MAX_RESPONSE_CHARS = 300
# OmniVoice unmasking steps: time scales linearly (M2 mini, 6 s of speech: 32 -> 9.1 s, 16 -> 4.6 s)
TTS_NUM_STEPS = 16
# sentence by sentence starts talking sooner, but on the M2 synthesis barely keeps up with speech,
# so it leaves pauses between sentences; off = one call for the whole answer
TTS_STREAM_SENTENCES = False
# sentences shorter than this are merged with the next one, OmniVoice sounds odd on a lone "Cześć!"
TTS_MIN_CHUNK_CHARS = 30
# a long first sentence is split at a comma, since nothing plays until the first chunk is synthesized
TTS_FIRST_CHUNK_CHARS = 60
TTS_FIRST_CHUNK_MIN_CHARS = 15

# "openai" -> GPT-6 Luna via API (needs OPENAI_API_KEY env var), "local" -> LLM_MODEL via mlx
LLM_BACKEND = os.environ.get("ALEKSY_LLM_BACKEND", "openai")
OPENAI_MODEL = "gpt-6-luna"
OPENAI_REASONING_EFFORT = "low"
# reasoning tokens count against this limit, so it is much higher than MAX_TOKENS
OPENAI_MAX_COMPLETION_TOKENS = 1000
OPENAI_TIMEOUT = 15
# load the local model too and use it when the API call fails
LLM_FALLBACK_LOCAL = os.environ.get("ALEKSY_LLM_FALLBACK_LOCAL", "true").lower() == "true"

REF_AUDIO = "assets/aleksy_ref.wav"

RECORDINGS_DIR = Path("./recordings")
PROMPTS_DIR = Path("./prompts")


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8").strip()

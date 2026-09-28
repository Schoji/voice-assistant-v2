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

# "openai" -> GPT-6 Luna via API (needs OPENAI_API_KEY env var), "local" -> LLM_MODEL via mlx
LLM_BACKEND = os.environ.get("ALEKSY_LLM_BACKEND", "openai")
OPENAI_MODEL = "gpt-6-luna"
OPENAI_REASONING_EFFORT = "low"
# reasoning tokens count against this limit, so it is much higher than MAX_TOKENS
OPENAI_MAX_COMPLETION_TOKENS = 1000
OPENAI_TIMEOUT = 15
# load the local model too and use it when the API call fails
LLM_FALLBACK_LOCAL = True

REF_AUDIO = "assets/aleksy_ref.wav"

RECORDINGS_DIR = Path("./recordings")
PROMPTS_DIR = Path("./prompts")


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8").strip()

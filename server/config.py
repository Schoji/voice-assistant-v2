from pathlib import Path

HOST = "0.0.0.0"
PORT = 8000

STT_MODEL = "mlx-community/Qwen3-ASR-0.6B-8bit"
TTS_MODEL = "mlx-community/OmniVoice-bf16"
LLM_MODEL = "mlx-community/Qwen3-8B-4bit"
MAX_TOKENS = 100

REF_AUDIO = "assets/aleksy.wav"

RECORDINGS_DIR = Path("./recordings")
PROMPTS_DIR = Path("./prompts")


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8").strip()

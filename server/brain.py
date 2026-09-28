import mlx_audio.stt as stt
import mlx_lm as lm
from openai import OpenAI
import mlx_audio.tts.utils as tts
import re
import time
from mlx_audio.tts.models.omnivoice.utils import create_voice_clone_prompt
from datetime_pl import date_time_in_words
import config

REF_AUDIO = config.REF_AUDIO
REF_TEXT = config.load_prompt("ref_text")

def timer_stop(start_time):
    print(f"Done. {time.time() - start_time:.2f}s")

def cut_at_last_sentence(text):
    end = max(text.rfind("."), text.rfind("!"), text.rfind("?"))
    return text[:end + 1] if end != -1 else text

def split_sentences(text):
    chunks, current = [], ""
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        current = f"{current} {sentence}".strip()
        if len(current) >= config.TTS_MIN_CHUNK_CHARS:
            chunks.append(current)
            current = ""
    if current:
        chunks.append(current)
    if chunks and len(chunks[0]) > config.TTS_FIRST_CHUNK_CHARS:
        comma = chunks[0].find(", ", config.TTS_FIRST_CHUNK_MIN_CHARS)
        if comma != -1:
            chunks[:1] = [chunks[0][:comma + 1], chunks[0][comma + 2:]]
    return chunks

class Brain():
    def __init__(self):
        self.messages = [
                {"role": "system", "content": self.system_prompt()},
        ]
        self.stt_model = stt.load(config.STT_MODEL)
        self.openai = None
        self.last_backend = None
        self.llm_model = self.tokenizer = None
        if config.LLM_BACKEND == "openai":
            self.openai = OpenAI(timeout=config.OPENAI_TIMEOUT, max_retries=1)
        if config.LLM_BACKEND == "local" or config.LLM_FALLBACK_LOCAL:
            self.llm_model, self.tokenizer = lm.load(config.LLM_MODEL)
        self.tts_model = tts.load_model(config.TTS_MODEL)
        self.ref_tokens = create_voice_clone_prompt(
        REF_AUDIO,
        tokenizer=self.tts_model.audio_tokenizer,
        ref_text=REF_TEXT,
)

        # the first synthesis compiles the GPU kernels, better here than on the first visitor
        for _ in self.text_to_speech("Cześć, jestem Aleksy i właśnie się rozgrzewam."):
            pass
        print("Brain initialized")

    def system_prompt(self):
        return (
            config.load_prompt("system").format(date_time=date_time_in_words())
            + "\n\n"
            + config.load_prompt("kni_context")
        )

    def speech_to_text(self, file_name: str) -> str:
        start = time.time()
        print(f"Generating text from speech. File: {file_name}")
        response = self.stt_model.generate(file_name, language="Polish").text
        timer_stop(start)
        return response

    def process(self, user_input: str):
        print(f"Asking llm: {user_input}")
        start = time.time()
        new_message =  {"role": "user", "content": user_input}
        self.messages.append(new_message)
        context = [self.messages[0]] + self.messages[1:][-6:]
        response = cut_at_last_sentence(self.generate(context)[:config.MAX_RESPONSE_CHARS])
        self.messages.append({"role": "assistant", "content": response})
        timer_stop(start)
        return response

    def generate(self, context) -> str:
        if self.openai is not None:
            try:
                response = self.generate_openai(context)
                self.last_backend = "openai"
                return response
            except Exception as e:
                if self.llm_model is None:
                    raise
                print(f"OpenAI request failed ({e}), falling back to local model")
        self.last_backend = "local"
        return self.generate_local(context)

    def generate_openai(self, context) -> str:
        completion = self.openai.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=context,
            reasoning_effort=config.OPENAI_REASONING_EFFORT,
            max_completion_tokens=config.OPENAI_MAX_COMPLETION_TOKENS,
        )
        response = completion.choices[0].message.content
        if not response:
            raise RuntimeError(f"empty response, finish_reason={completion.choices[0].finish_reason}")
        print(response)
        return response

    def generate_local(self, context) -> str:
        prompt = self.tokenizer.apply_chat_template(context, add_generation_prompt=True, enable_thinking=False)
        return lm.generate(self.llm_model, self.tokenizer, prompt=prompt, max_tokens=config.MAX_TOKENS, verbose=True)

    def text_to_speech(self, input_text: str):
        start = time.time()
        print(f"Generating speech from text: {input_text}")
        # one sentence at a time, so the client starts playing after the first one instead of the whole answer
        for chunk in split_sentences(input_text):
            for result in self.tts_model.generate(
                text=chunk,
                ref_audio=REF_AUDIO,
                ref_text= REF_TEXT,
                ref_tokens=self.ref_tokens,
                num_steps=config.TTS_NUM_STEPS,
            ):
                yield result.audio
        timer_stop(start)

# brain.process("Siemka byczku co tam")
# brain.text_to_speech("siema")

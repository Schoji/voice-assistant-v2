import mlx_audio.stt as stt
import mlx_lm as lm
import mlx_audio.tts.utils as tts
import time
from mlx_audio.tts.models.omnivoice.utils import create_voice_clone_prompt
from datetime_pl import date_time_in_words
import config

REF_AUDIO = config.REF_AUDIO
REF_TEXT = config.load_prompt("kni_context")

def timer_stop(start_time):
    print(f"Done. {time.time() - start_time:.2f}s")

class Brain():
    def __init__(self):
        self.messages = [
                {"role": "system", "content": self.system_prompt()},
        ]
        self.stt_model = stt.load(config.STT_MODEL)
        self.llm_model, self.tokenizer = lm.load(config.LLM_MODEL)
        self.tts_model = tts.load_model(config.TTS_MODEL)
        self.ref_tokens = create_voice_clone_prompt(
        REF_AUDIO,
        tokenizer=self.tts_model.audio_tokenizer,
        ref_text=REF_TEXT,
)

        print("Brain initialized")

    def system_prompt(self):
        return config.load_prompt("system").format(date_time=date_time_in_words())

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
        prompt = self.tokenizer.apply_chat_template([self.messages[0]] + self.messages[-6:], add_generation_prompt=True, enable_thinking=False)
        response = lm.generate(self.llm_model, self.tokenizer, prompt=prompt, max_tokens=config.MAX_TOKENS, verbose=True)
        self.messages.append({"role": "assistant", "content": response})
        timer_stop(start)
        return response

    def text_to_speech(self, input_text: str):
        start = time.time()
        print(f"Generating speech from text: {input_text}")
        for result in self.tts_model.generate(
            text=input_text,
            ref_audio=REF_AUDIO,
            ref_text= REF_TEXT,
            ref_tokens=self.ref_tokens
        ):
            yield result.audio
        timer_stop(start)

# brain.process("Siemka byczku co tam")
# brain.text_to_speech("siema")

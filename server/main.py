import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import websockets
import time
import wave
from brain import Brain
from aleksy_protocol.wire import END, MIC_CHANNELS, MIC_RATE, MIC_SAMPLE_WIDTH
import config

import numpy as np

RECORDINGS_DIR = config.RECORDINGS_DIR

def to_pcm16(audio):
    samples = np.clip(np.array(audio), -1.0, 1.0)
    return (samples * 32767).astype(np.int16).tobytes()

def next_pcm(chunks):
    chunk = next(chunks, None)
    return None if chunk is None else to_pcm16(chunk)

RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
# every model call runs on this one thread: MLX streams are per thread, and running them
# off the event loop lets audio go out while the next sentence is still being synthesized
models = ThreadPoolExecutor(max_workers=1)
brain = models.submit(Brain).result()

async def run(fn, *args):
    return await asyncio.get_running_loop().run_in_executor(models, fn, *args)

async def file_handler(ws):
    print("Client connected, waiting for file...")
    file_bytes = await ws.recv()  # receive bytes
    name = str(RECORDINGS_DIR / f"utt-{int(time.time())}.wav")
    # pylint: disable=no-member
    with wave.open(name, "wb") as f:
        f.setnchannels(MIC_CHANNELS)
        f.setsampwidth(MIC_SAMPLE_WIDTH)
        f.setframerate(MIC_RATE)
        f.writeframes(file_bytes)

    print(f"File saved as {name}")

    start = time.time()
    text = await run(brain.speech_to_text, name)
    stt, start = time.time() - start, time.time()
    llm_output = await run(brain.process, text)
    llm, start = time.time() - start, time.time()
    print("Sending bytes to the client")
    chunks = brain.text_to_speech(llm_output)
    while (pcm := await run(next_pcm, chunks)) is not None:
        await ws.send(pcm)
    tts = time.time() - start
    # what the client's panel shows; clients that predate it stop reading at the first text message
    await ws.send(json.dumps({
        "heard": text,
        "said": llm_output,
        "llm_backend": brain.last_backend,
        "timings": {"stt": stt, "llm": llm, "tts": tts},
    }, ensure_ascii=False))
    await ws.send(END)


async def main():
    async with websockets.serve(file_handler, config.HOST, config.PORT):
        print(f"Server running on ws://{config.HOST}:{config.PORT}")
        await asyncio.Future()

asyncio.run(main())

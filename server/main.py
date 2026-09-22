import asyncio
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

RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
brain = Brain()

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

    text = brain.speech_to_text(name)
    llm_output = brain.process(text)
    print("Sending bytes to the client")
    for chunk in brain.text_to_speech(llm_output):
        await ws.send(to_pcm16(chunk))
    await ws.send(END)


async def main():
    async with websockets.serve(file_handler, config.HOST, config.PORT):
        print(f"Server running on ws://{config.HOST}:{config.PORT}")
        await asyncio.Future()

asyncio.run(main())

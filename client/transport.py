import websockets
import asyncio
from audio import open_player
import config

async def send_file(bytes, on_audio=None):
    async with websockets.connect(config.SERVER_URI, max_size=None) as ws:
        await ws.send(bytes)

        player = open_player()

        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=20.0)


                if isinstance(msg, str):
                    break
                else:
                    if on_audio:
                        on_audio()
                        on_audio = None
                    player.stdin.write(msg)

        except asyncio.TimeoutError:
            print("Timeout")
            raise

        finally:
            player.stdin.close()
            player.wait()

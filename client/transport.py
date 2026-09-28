import websockets
import asyncio
from audio import open_player
import config

async def connect():
    for uri in config.SERVER_URIS:
        try:
            return await websockets.connect(uri, max_size=None, open_timeout=config.CONNECT_TIMEOUT)
        except (OSError, TimeoutError) as e:
            print(f"  (serwer {uri} niedostępny: {e})", flush=True)
            error = e
    raise ConnectionError("żaden serwer nie odpowiada") from error

async def send_file(bytes, on_audio=None):
    async with await connect() as ws:
        await ws.send(bytes)

        player = open_player()

        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=config.RESPONSE_TIMEOUT)


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

import json
import time
import websockets
import asyncio
from aleksy_protocol.wire import END
from audio import open_player
import config

async def connect():
    for uri in config.SERVER_URIS:
        try:
            return uri, await websockets.connect(uri, max_size=None, open_timeout=config.CONNECT_TIMEOUT)
        except (OSError, TimeoutError) as e:
            print(f"  (serwer {uri} niedostępny: {e})", flush=True)
            error = e
    raise ConnectionError("żaden serwer nie odpowiada") from error

async def send_file(bytes, on_audio=None, result=None):
    """streams the answer to the speaker and fills `result` with what the panel shows

    `result` is filled in place so the caller keeps what was measured even when this raises.
    """
    result = {} if result is None else result
    start = time.time()
    result["server"], ws = await connect()
    async with ws:
        await ws.send(bytes)

        player = open_player()

        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=config.RESPONSE_TIMEOUT)


                if msg == END:
                    break
                elif isinstance(msg, str):
                    try:
                        result.update(json.loads(msg))
                    except ValueError:
                        print(f"  (niezrozumiała wiadomość od serwera: {msg[:80]})", flush=True)
                else:
                    if "first_audio" not in result:
                        result["first_audio"] = time.time() - start
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
            result["total"] = time.time() - start
    return result

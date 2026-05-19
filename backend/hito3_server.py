"""
Hito 3 (paso 3.4) — Servidor FastAPI + WebSocket.

Cambios vs 3.3:
- Añade endpoint WebSocket /ws
- Frontend manda {"type": "speak", "text": "..."} por el socket
- Backend genera audio con ElevenLabs y lo manda de vuelta por el mismo socket
- Mantiene HTTP /tts por compatibilidad pero ya no se usa
"""

import asyncio
import base64
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

app = FastAPI(title="Dispensador IA")

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# Cliente ElevenLabs
elevenlabs_client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
VOICE_ID = os.environ["ELEVENLABS_VOICE_ID"]


# ─────────────────────────────────────────────────────────────────
# HTTP endpoints
# ─────────────────────────────────────────────────────────────────
@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


# ─────────────────────────────────────────────────────────────────
# WebSocket endpoint
# ─────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Conexión persistente con el navegador.
    Recibe mensajes JSON y responde según el tipo.
    """
    await websocket.accept()
    print("🔌 Cliente conectado vía WebSocket")

    try:
        # Saludamos al cliente al conectarse
        await websocket.send_json({
            "type": "ready",
            "message": "Conectado al servidor",
        })

        # Bucle de escucha de mensajes
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            print(f"📩 Mensaje recibido: type={msg_type}")

            if msg_type == "speak":
                # El cliente pide que el avatar diga algo
                texto = data.get("text", "").strip()
                if not texto:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Texto vacío",
                    })
                    continue

                await handle_speak(websocket, texto)

            elif msg_type == "ping":
                # Test de conexión
                await websocket.send_json({"type": "pong"})

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Tipo de mensaje desconocido: {msg_type}",
                })

    except WebSocketDisconnect:
        print("🔌 Cliente desconectado")
    except Exception as e:
        print(f"❌ Error en WebSocket: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


async def handle_speak(websocket: WebSocket, texto: str):
    """
    Genera audio con ElevenLabs y lo manda al cliente por el WebSocket.
    """
    print(f"   🎤 Generando audio para: '{texto[:50]}{'...' if len(texto) > 50 else ''}'")

    # Avisar al cliente que estamos generando
    await websocket.send_json({
        "type": "speaking_start",
        "text": texto,
    })

    try:
        # Generar audio (síncrono, lo metemos en thread aparte para no bloquear)
        loop = asyncio.get_event_loop()
        audio_bytes = await loop.run_in_executor(
            None,
            generar_audio_sync,
            texto,
        )

        # Codificar el audio en base64 para mandarlo por JSON
        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")

        # Mandar el audio completo en un mensaje
        await websocket.send_json({
            "type": "audio",
            "text": texto,
            "audio_base64": audio_b64,
            "format": "mp3",
        })

        await websocket.send_json({"type": "speaking_end"})
        print(f"   ✅ Audio enviado ({len(audio_bytes)} bytes)")

    except Exception as e:
        print(f"   ❌ Error generando audio: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Error generando audio: {e}",
        })


def generar_audio_sync(texto: str) -> bytes:
    """Llama a ElevenLabs de forma síncrona, devuelve bytes del MP3."""
    audio_stream = elevenlabs_client.text_to_speech.convert(
        voice_id=VOICE_ID,
        model_id="eleven_flash_v2_5",
        text=texto,
        output_format="mp3_44100_128",
    )
    return b"".join(audio_stream)


# ─────────────────────────────────────────────────────────────────
# Arranque
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("🥤  Dispensador IA — Servidor web (WebSocket)")
    print("=" * 60)
    print("Abre http://localhost:8000")
    print("Pulsa Ctrl+C para parar\n")

    uvicorn.run(
        "hito3_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
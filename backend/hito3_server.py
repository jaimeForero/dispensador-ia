"""
Hito 3 (paso 3.3) — Servidor FastAPI + endpoint TTS.

Añade:
- Endpoint POST /tts que recibe texto y devuelve audio MP3 de ElevenLabs.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="Dispensador IA")

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

# Monta el frontend como /static
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# ─────────────────────────────────────────────────────────────────
# Cliente de ElevenLabs (se inicializa una vez al arrancar)
# ─────────────────────────────────────────────────────────────────
elevenlabs_client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
VOICE_ID = os.environ["ELEVENLABS_VOICE_ID"]


# ─────────────────────────────────────────────────────────────────
# Modelos de datos
# ─────────────────────────────────────────────────────────────────
class TTSRequest(BaseModel):
    text: str


# ─────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────
@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/tts")
async def tts(req: TTSRequest):
    """Recibe texto, devuelve audio MP3 de ElevenLabs."""
    if not req.text or len(req.text) > 500:
        raise HTTPException(status_code=400, detail="Texto vacío o muy largo")

    try:
        # Generar audio (devuelve un generator de chunks)
        audio_stream = elevenlabs_client.text_to_speech.convert(
            voice_id=VOICE_ID,
            model_id="eleven_flash_v2_5",
            text=req.text,
            output_format="mp3_44100_128",
        )

        # Recolectar todos los chunks en bytes
        audio_bytes = b"".join(audio_stream)

        # Devolver como respuesta de audio
        return StreamingResponse(
            iter([audio_bytes]),
            media_type="audio/mpeg",
            headers={"Content-Length": str(len(audio_bytes))},
        )

    except Exception as e:
        print(f"❌ Error en TTS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────
# Arranque
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("🥤  Dispensador IA — Servidor web")
    print("=" * 60)
    print("Abre http://localhost:8000")
    print("Pulsa Ctrl+C para parar\n")

    uvicorn.run(
        "hito3_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
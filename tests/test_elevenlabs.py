import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import play

load_dotenv()

# AÑADIR ESTAS DOS LÍNEAS PARA DIAGNOSTICAR
print("Voice ID que voy a usar:", os.environ.get("ELEVENLABS_VOICE_ID"))
print("API Key (primeros 10 chars):", os.environ.get("ELEVENLABS_API_KEY", "")[:10])

# ... el resto del código sigue igual

client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])

audio = client.text_to_speech.convert(
    voice_id=os.environ["ELEVENLABS_VOICE_ID"],
    model_id="eleven_flash_v2_5",
    text="Hola, bienvenido a la máquina expendedora. ¿Qué te apetece?",
)

# Guardar a archivo para escucharlo
with open("tests/output.mp3", "wb") as f:
    for chunk in audio:
        f.write(chunk)

print("ELEVENLABS OK, audio guardado en tests/output.mp3")
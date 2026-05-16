import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.environ["GROQ_API_KEY"])

# Necesitas un audio .mp3 o .wav cualquiera para probar
# Si no tienes, graba 5 segundos con el móvil y pásalo a la carpeta tests/

with open("tests/voice_preview_christian - calm latin voice.mp3", "rb") as f:
    transcription = client.audio.transcriptions.create(
        file=f,
        model="whisper-large-v3-turbo",
        language="es",
    )

print("GROQ WHISPER OK")
print("Transcripción:", transcription.text)
import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

load_dotenv()

client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])

voices = client.voices.get_all()

print(f"Tienes {len(voices.voices)} voces disponibles:\n")
for v in voices.voices:
    print(f"- Nombre: {v.name}")
    print(f"  Voice ID: {v.voice_id}")
    print(f"  Categoría: {v.category}")
    print()
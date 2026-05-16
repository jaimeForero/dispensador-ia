import os
from dotenv import load_dotenv
from cerebras.cloud.sdk import Cerebras

load_dotenv()

modelo = "llama3.1-8b"
print("Modelo que voy a usar:", modelo)

client = Cerebras(api_key=os.environ["CEREBRAS_API_KEY"])

response = client.chat.completions.create(
    model=modelo,
    messages=[
        {"role": "system", "content": "Eres un asistente de máquina expendedora. Sé breve."},
        {"role": "user", "content": "Hola, quiero una Coca-Cola"}
    ],
    max_tokens=100,
)

print("CEREBRAS OK")
print("Respuesta:", response.choices[0].message.content)
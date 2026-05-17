"""
Hito 2 — Dispensador con voz + function calling.

El LLM (Cerebras Llama 3.1 8B) recibe la transcripción y decide:
- Responder solo con voz (charla, redirección)
- Llamar a una función para modificar el pedido
- Ambas cosas

Las funciones están en backend/domain/tools.py
"""

import asyncio
import json
import os
import re
import signal
import sys
from pathlib import Path
from dotenv import load_dotenv

# Permitir importar desde backend/domain cuando ejecutamos desde la raíz
sys.path.insert(0, str(Path(__file__).parent))

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    LLMFullResponseStartFrame,
    TextFrame,
    TranscriptionFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.cerebras.llm import CerebrasLLMService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.groq.stt import GroqSTTService
from pipecat.transports.local.audio import (
    LocalAudioTransport,
    LocalAudioTransportParams,
)

from domain.tools import TOOLS_SCHEMA, TOOLS_IMPL

load_dotenv()


# ─────────────────────────────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
Eres el asistente de una máquina expendedora de refrescos. Eres carismático, \
amable y muy breve.

CÓMO ACTUAR:
- Tienes funciones disponibles para gestionar el pedido. ÚSALAS siempre que \
el cliente pida un producto, pregunte qué hay, cambie de opinión o confirme.
- NO inventes el resultado de las funciones. Llámalas y usa lo que devuelvan.
- Después de llamar una función, dile al cliente con UNA frase corta qué pasó.
- Antes de dispensar, SIEMPRE confirma el pedido con el cliente.

REGLAS DE LENGUAJE:
1. Responde SIEMPRE en español.
2. UNA frase de máximo 15 palabras.
3. NO escribas acotaciones entre asteriscos, paréntesis o corchetes.
4. NO inventes productos. Si te piden algo que no está, ofrece una alternativa.

EJEMPLOS:
Cliente: "¿Qué tienes?"
→ Llamas a listar_productos(), luego dices: "Tengo Coca-Cola, Fanta, Sprite, \
Aquarius y Coca-Cola Zero. ¿Cuál te apetece?"

Cliente: "Una Coca y una Fanta"
→ Llamas a añadir_al_pedido("Coca-Cola", 1) y añadir_al_pedido("Fanta Naranja", 1), \
luego dices: "Marchando una Coca-Cola y una Fanta. ¿Confirmas?"

Cliente: "Sí, confirmo"
→ Llamas a confirmar_y_dispensar(), luego dices: "¡Listo! Que la disfrutes."
"""


# ─────────────────────────────────────────────────────────────────────
# Filtro de acotaciones
# ─────────────────────────────────────────────────────────────────────
class AcotacionesFilter(FrameProcessor):
    PATRON = re.compile(r"\*[^*]*\*|\([^)]*\)|\[[^\]]*\]")

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, TextFrame):
            limpio = self.PATRON.sub("", frame.text)
            limpio = re.sub(r"\s{2,}", " ", limpio).strip()
            if limpio:
                frame.text = limpio
                await self.push_frame(frame, direction)
        else:
            await self.push_frame(frame, direction)


# ─────────────────────────────────────────────────────────────────────
# Logger de eventos
# ─────────────────────────────────────────────────────────────────────
class EventLogger(FrameProcessor):
    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, TranscriptionFrame):
            print(f"\n🗣️  TÚ: {frame.text}")
        await self.push_frame(frame, direction)


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────
async def main():
    transport = LocalAudioTransport(
        LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(
                params=VADParams(
                    confidence=0.85,
                    start_secs=0.3,
                    stop_secs=0.5,
                    min_volume=0.75,
                )
            ),
        )
    )

    stt = GroqSTTService(
        api_key=os.environ["GROQ_API_KEY"],
        model="whisper-large-v3-turbo",
        language="es",
    )

    llm = CerebrasLLMService(
        api_key=os.environ["CEREBRAS_API_KEY"],
        model="llama3.1-8b",
        params=CerebrasLLMService.InputParams(
            max_tokens=80,
            temperature=0.5,   # más determinista, menos creativo
        ),
    )

    # ✨ Registrar las funciones que el LLM puede invocar
    for nombre_fn, impl in TOOLS_IMPL.items():
        llm.register_function(nombre_fn, _wrap_function(impl, nombre_fn))

    tts = ElevenLabsTTSService(
        api_key=os.environ["ELEVENLABS_API_KEY"],
        voice_id=os.environ["ELEVENLABS_VOICE_ID"],
        model="eleven_flash_v2_5",
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    context = OpenAILLMContext(messages, tools=TOOLS_SCHEMA)
    context_aggregator = llm.create_context_aggregator(context)

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            EventLogger(),
            context_aggregator.user(),
            llm,
            AcotacionesFilter(),
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(allow_interruptions=False),  # 🔇 sin auriculares
    )

    async def saludo_inicial():
        await asyncio.sleep(1.5)
        messages.append({
            "role": "user",
            "content": "[Cliente recién llegado. Salúdale en UNA frase muy corta.]",
        })
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    runner = PipelineRunner(handle_sigint=False)
    loop = asyncio.get_running_loop()
    shutdown = asyncio.Event()

    def handle_shutdown():
        if not shutdown.is_set():
            print("\n\n👋 Cerrando...")
            shutdown.set()
            loop.create_task(task.cancel())

    try:
        loop.add_signal_handler(signal.SIGINT, handle_shutdown)
        loop.add_signal_handler(signal.SIGTERM, handle_shutdown)
    except NotImplementedError:
        pass

    print("\n" + "=" * 60)
    print("🥤  Dispensador IA — Hito 2 (function calling)")
    print("=" * 60)
    print("Haz un pedido por voz. Pulsa Ctrl+C para parar.\n")

    try:
        await asyncio.gather(runner.run(task), saludo_inicial())
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        print("\n✅ Dispensador detenido.\n")


# ─────────────────────────────────────────────────────────────────────
# Wrapper para adaptar nuestras funciones al formato de Pipecat
# ─────────────────────────────────────────────────────────────────────
def _wrap_function(impl, nombre_fn):
    """
    Pipecat espera funciones async con firma específica.
    Adaptamos nuestras funciones síncronas a ese formato.
    """
    async def wrapper(params):
        # params.arguments es un dict con los args que pasó el LLM
        try:
            args = params.arguments or {}
            resultado = impl(**args)
            print(f"   🔧 {nombre_fn}({args}) → {resultado[:80]}{'...' if len(resultado) > 80 else ''}")
            await params.result_callback(json.loads(resultado))
        except Exception as e:
            print(f"   ❌ Error en {nombre_fn}: {e}")
            await params.result_callback({"ok": False, "error": str(e)})
    return wrapper


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
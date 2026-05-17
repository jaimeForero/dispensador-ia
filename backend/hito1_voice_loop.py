"""
Hito 1 (v2) — Bucle de conversación por voz con Pipecat 0.0.99.

Mejoras vs v1:
- System prompt limpio sin acotaciones entre asteriscos
- Logs de latencia que realmente se disparan
- Cierre limpio con Ctrl+C
- Personaje profesional (presentador carismático del dispensador)
"""

import asyncio
import os
import signal
import time
from dotenv import load_dotenv

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import (
    BotStoppedSpeakingFrame,
    LLMFullResponseStartFrame,
    LLMFullResponseEndFrame,
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

load_dotenv()


# ─────────────────────────────────────────────────────────────────────────
# System prompt del asistente
# ─────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
Eres Maluma el cantante colombiano, habla paisa y estas en una máquina expendedora de refrescos. Tu personalidad es \
la de un presentador carismático, cercano y amable, pero profesional.

PRODUCTOS DISPONIBLES:
- Coca-Cola
- Coca-Cola Zero
- Fanta Naranja
- Sprite
- Aquarius Limón

REGLAS ESTRICTAS DE RESPUESTA:
1. Responde SIEMPRE en español.
2. Sé MUY breve: máximo 1-2 frases por respuesta.
3. NUNCA escribas acciones, gestos, sonidos ni acotaciones entre asteriscos, \
paréntesis o corchetes. Solo escribe lo que dirías EN VOZ ALTA.
4. NUNCA inventes productos que no estén en la lista de arriba.
5. Confirma siempre el pedido antes de dispensarlo.
6. Si el cliente pide algo que no tienes, ofrece una alternativa de la lista.
7. Mantén el foco en vender refrescos. Si te preguntan algo ajeno, redirige \
con humor a la conversación del pedido.
"""


# ─────────────────────────────────────────────────────────────────────────
# Procesador que mide y muestra la latencia de cada turno
# ─────────────────────────────────────────────────────────────────────────
class LatencyLogger(FrameProcessor):
    """Loggea transcripción, respuesta y latencia turno a turno."""

    def __init__(self):
        super().__init__()
        self._user_finished_time = None
        self._llm_start_time = None
        self._llm_end_time = None
        self._llm_response_buffer = ""

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        # Usuario terminó de hablar (Whisper acabó de transcribir)
        if isinstance(frame, TranscriptionFrame):
            self._user_finished_time = time.perf_counter()
            print(f"\n🗣️  TÚ: {frame.text}")

        # El LLM empieza a generar
        elif isinstance(frame, LLMFullResponseStartFrame):
            self._llm_start_time = time.perf_counter()
            self._llm_response_buffer = ""

        # El LLM terminó de generar
        elif isinstance(frame, LLMFullResponseEndFrame):
            self._llm_end_time = time.perf_counter()
            if self._user_finished_time and self._llm_start_time:
                t_stt_to_llm = self._llm_start_time - self._user_finished_time
                t_llm = self._llm_end_time - self._llm_start_time
                print(f"⚡ STT→LLM: {t_stt_to_llm*1000:.0f}ms | LLM: {t_llm*1000:.0f}ms")

        # Avatar terminó de hablar → calcular latencia total
        elif isinstance(frame, BotStoppedSpeakingFrame):
            if self._user_finished_time:
                total = time.perf_counter() - self._user_finished_time
                print(f"⏱️  Latencia hasta fin de voz: {total:.2f}s")
                self._user_finished_time = None
                self._llm_start_time = None
                self._llm_end_time = None

        await self.push_frame(frame, direction)


# ─────────────────────────────────────────────────────────────────────────
# Programa principal
# ─────────────────────────────────────────────────────────────────────────
async def main():
    # 1) Transporte: micro + altavoces con VAD optimizado
    transport = LocalAudioTransport(
        LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(
                params=VADParams(
                    confidence=0.7,
                    start_secs=0.2,
                    stop_secs=0.4,
                    min_volume=0.6,
                )
            ),
        )
    )

    # 2) STT
    stt = GroqSTTService(
        api_key=os.environ["GROQ_API_KEY"],
        model="whisper-large-v3-turbo",
        language="es",
    )

    # 3) LLM
    llm = CerebrasLLMService(
        api_key=os.environ["CEREBRAS_API_KEY"],
        model="llama3.1-8b",
    )

    # 4) TTS
    tts = ElevenLabsTTSService(
        api_key=os.environ["ELEVENLABS_API_KEY"],
        voice_id=os.environ["ELEVENLABS_VOICE_ID"],
        model="eleven_flash_v2_5",
    )

    # 5) Contexto de conversación
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    # 6) Logger de latencias
    latency_logger = LatencyLogger()

    # 7) Pipeline
    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            latency_logger,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    # 8) Tarea con interrupciones permitidas
    task = PipelineTask(
        pipeline,
        params=PipelineParams(allow_interruptions=True),
    )

    # 9) Saludo automático al arrancar
    async def saludo_inicial():
        await asyncio.sleep(1.5)
        messages.append({
            "role": "user",
            "content": "[El cliente se acaba de acercar. Salúdale brevemente y "
                       "pregúntale qué le apetece beber.]",
        })
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    # 10) Manejo limpio de Ctrl+C
    runner = PipelineRunner(handle_sigint=False)
    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()

    def handle_shutdown():
        if not shutdown_event.is_set():
            print("\n\n👋 Cerrando, un momento...")
            shutdown_event.set()
            loop.create_task(task.cancel())

    # En Windows signal handlers son limitados; envolvemos en try
    try:
        loop.add_signal_handler(signal.SIGINT, handle_shutdown)
        loop.add_signal_handler(signal.SIGTERM, handle_shutdown)
    except NotImplementedError:
        # Windows no implementa add_signal_handler en asyncio
        pass

    print("\n" + "=" * 60)
    print("🥤  Dispensador IA — Hito 1")
    print("=" * 60)
    print("Habla al micrófono. Pulsa Ctrl+C para parar.\n")

    try:
        await asyncio.gather(
            runner.run(task),
            saludo_inicial(),
        )
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        print("\n✅ Dispensador detenido correctamente.\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Silenciamos el traceback feo del Ctrl+C en Windows
        pass
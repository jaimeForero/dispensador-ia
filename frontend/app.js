import { TalkingHead } from 'talkinghead';

// ─────────────────────────────────────────────────────────────────
// Configuración
// ─────────────────────────────────────────────────────────────────
const AVATAR_URL = '/static/assets/brunette.glb';

const container = document.getElementById('avatar-container');
const statusEl = document.getElementById('status');
const textInput = document.getElementById('text-input');
const speakButton = document.getElementById('speak-button');


// ─────────────────────────────────────────────────────────────────
// Crear instancia de TalkingHead
// ─────────────────────────────────────────────────────────────────
const head = new TalkingHead(container, {
    ttsEndpoint: 'https://example.com/tts',  // dummy, requerido pero no se usa
    cameraView: 'upper',
    lipsyncModules: ['en'],   // solo inglés (es no existe en TalkingHead)
});


// ─────────────────────────────────────────────────────────────────
// Cargar el avatar
// ─────────────────────────────────────────────────────────────────
async function cargarAvatar() {
    statusEl.textContent = 'Cargando avatar...';
    try {
        await head.showAvatar(
            {
                url: AVATAR_URL,
                body: 'M',
                avatarMood: 'neutral',
                lipsyncLang: 'en',   // motor de lipsync inglés (vale para español)
            },
            (event) => {
                if (event.lengthComputable) {
                    const pct = ((event.loaded / event.total) * 100).toFixed(0);
                    statusEl.textContent = `Cargando avatar... ${pct}%`;
                }
            }
        );

        statusEl.textContent = '✅ Avatar listo. Escribe y pulsa "Hacer hablar".';
        statusEl.classList.add('ok');
        speakButton.disabled = false;
        console.log('✅ TalkingHead inicializado y avatar cargado');
    } catch (err) {
        console.error(err);
        statusEl.textContent = `❌ Error: ${err.message}`;
        statusEl.classList.add('error');
    }
}


// ─────────────────────────────────────────────────────────────────
// Hacer que el avatar hable
// ─────────────────────────────────────────────────────────────────
async function hacerHablar(texto) {
    if (!texto.trim()) return;

    speakButton.disabled = true;
    speakButton.textContent = '⏳ Generando...';
    statusEl.textContent = 'Pidiendo audio al backend...';
    statusEl.classList.remove('error');

    try {
        // 1) Pedir audio al backend
        const resp = await fetch('/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: texto }),
        });

        if (!resp.ok) {
            throw new Error(`Backend devolvió ${resp.status}`);
        }

        // 2) Recibir el audio como blob → arraybuffer
        const audioBlob = await resp.blob();
        const audioArrayBuffer = await audioBlob.arrayBuffer();

        statusEl.textContent = '🎤 Avatar hablando...';
        speakButton.textContent = '🗣️ Hablando...';

        // 3) Decodificar audio
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const audioBuffer = await audioContext.decodeAudioData(audioArrayBuffer);

        // 4) Distribuir tiempos de palabras a lo largo del audio
        const palabras = texto.split(/\s+/).filter(w => w.length > 0);
        const duracionMs = audioBuffer.duration * 1000;
        const msPorPalabra = duracionMs / palabras.length;
        const wtimes = palabras.map((_, i) => i * msPorPalabra);
        const wdurations = palabras.map(() => msPorPalabra);

        // 5) Hacer hablar al avatar con audio + sincronización de palabras
        await head.speakAudio(
            {
                audio: audioBuffer,
                words: palabras,
                wtimes: wtimes,
                wdurations: wdurations,
            },
            {
                lipsyncLang: 'en',
            }
        );

        statusEl.textContent = '✅ Listo. Escribe otra cosa.';
        statusEl.classList.add('ok');
    } catch (err) {
        console.error(err);
        statusEl.textContent = `❌ Error: ${err.message}`;
        statusEl.classList.add('error');
    } finally {
        speakButton.disabled = false;
        speakButton.textContent = '🎤 Hacer hablar';
    }
}


// ─────────────────────────────────────────────────────────────────
// Eventos
// ─────────────────────────────────────────────────────────────────
speakButton.addEventListener('click', () => {
    hacerHablar(textInput.value);
});

textInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        hacerHablar(textInput.value);
    }
});


// ─────────────────────────────────────────────────────────────────
// Arrancar
// ─────────────────────────────────────────────────────────────────
cargarAvatar();
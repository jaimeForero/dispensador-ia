import { TalkingHead } from 'talkinghead';

console.log('🚀 APP.JS V3.4 INICIADO');
console.log('✅ TalkingHead importado:', typeof TalkingHead);

// ─────────────────────────────────────────────────────────────────
// Configuración
// ─────────────────────────────────────────────────────────────────
const AVATAR_URL = '/static/assets/brunette.glb';
const WS_URL = `ws://${window.location.host}/ws`;

console.log('🔧 Configuración:', { AVATAR_URL, WS_URL });

const container = document.getElementById('avatar-container');
const statusEl = document.getElementById('status');
const textInput = document.getElementById('text-input');
const speakButton = document.getElementById('speak-button');


// ─────────────────────────────────────────────────────────────────
// Crear instancia de TalkingHead
// ─────────────────────────────────────────────────────────────────
console.log('🎬 Creando TalkingHead...');

const head = new TalkingHead(container, {
    ttsEndpoint: 'https://example.com/tts',  // dummy
    cameraView: 'upper',
    lipsyncModules: ['en'],
});

console.log('✅ TalkingHead creado');


// ─────────────────────────────────────────────────────────────────
// Estado de la conexión WebSocket
// ─────────────────────────────────────────────────────────────────
let ws = null;
let wsReady = false;
let avatarReady = false;


// ─────────────────────────────────────────────────────────────────
// Conectar al WebSocket
// ─────────────────────────────────────────────────────────────────
function conectarWebSocket() {
    console.log(`🔌 Conectando a ${WS_URL}...`);
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
        console.log('✅ WebSocket conectado');
        wsReady = true;
        actualizarBotonHablar();
    };

    ws.onmessage = async (event) => {
        const data = JSON.parse(event.data);
        console.log(`📨 Mensaje recibido: ${data.type}`);

        switch (data.type) {
            case 'ready':
                console.log('Backend listo:', data.message);
                break;

            case 'speaking_start':
                statusEl.textContent = '🎤 Generando audio...';
                statusEl.classList.remove('error', 'ok');
                break;

            case 'audio':
                await reproducirAudioConLipsync(data.audio_base64, data.text);
                break;

            case 'speaking_end':
                statusEl.textContent = '✅ Listo. Escribe otra cosa.';
                statusEl.classList.add('ok');
                speakButton.disabled = false;
                speakButton.textContent = '🎤 Hacer hablar';
                break;

            case 'error':
                statusEl.textContent = `❌ Error: ${data.message}`;
                statusEl.classList.add('error');
                speakButton.disabled = false;
                speakButton.textContent = '🎤 Hacer hablar';
                break;
        }
    };

    ws.onerror = (error) => {
        console.error('❌ Error en WebSocket:', error);
        statusEl.textContent = '❌ Error de conexión';
        statusEl.classList.add('error');
        wsReady = false;
    };

    ws.onclose = () => {
        console.warn('🔌 WebSocket cerrado. Reintentando en 2s...');
        wsReady = false;
        actualizarBotonHablar();
        setTimeout(conectarWebSocket, 2000);
    };
}


// ─────────────────────────────────────────────────────────────────
// Cargar el avatar
// ─────────────────────────────────────────────────────────────────
async function cargarAvatar() {
    console.log('📥 Iniciando carga del avatar...');
    statusEl.textContent = 'Cargando avatar...';

    try {
        await head.showAvatar(
            {
                url: AVATAR_URL,
                body: 'M',
                avatarMood: 'neutral',
                lipsyncLang: 'en',
            },
            (event) => {
                if (event.lengthComputable) {
                    const pct = ((event.loaded / event.total) * 100).toFixed(0);
                    statusEl.textContent = `Cargando avatar... ${pct}%`;
                }
            }
        );

        avatarReady = true;
        statusEl.textContent = '✅ Avatar listo. Escribe y pulsa "Hacer hablar".';
        statusEl.classList.add('ok');
        actualizarBotonHablar();
        console.log('✅ Avatar cargado correctamente');
    } catch (err) {
        console.error('❌ Error cargando avatar:', err);
        statusEl.textContent = `❌ Error cargando avatar: ${err.message}`;
        statusEl.classList.add('error');
    }
}


// ─────────────────────────────────────────────────────────────────
// Habilitar el botón solo cuando avatar Y WebSocket estén listos
// ─────────────────────────────────────────────────────────────────
function actualizarBotonHablar() {
    if (avatarReady && wsReady) {
        speakButton.disabled = false;
    } else {
        speakButton.disabled = true;
    }
}


// ─────────────────────────────────────────────────────────────────
// Pedir al backend que genere audio (vía WebSocket)
// ─────────────────────────────────────────────────────────────────
function pedirHablar(texto) {
    if (!texto.trim()) return;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        statusEl.textContent = '❌ No hay conexión con el servidor';
        statusEl.classList.add('error');
        return;
    }

    speakButton.disabled = true;
    speakButton.textContent = '⏳ Generando...';

    ws.send(JSON.stringify({
        type: 'speak',
        text: texto,
    }));
}


// ─────────────────────────────────────────────────────────────────
// Reproducir audio recibido (con lipsync)
// ─────────────────────────────────────────────────────────────────
async function reproducirAudioConLipsync(audioBase64, texto) {
    statusEl.textContent = '🎤 Avatar hablando...';
    speakButton.textContent = '🗣️ Hablando...';

    try {
        const binaryString = atob(audioBase64);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }

        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const audioBuffer = await audioContext.decodeAudioData(bytes.buffer);

        const palabras = texto.split(/\s+/).filter(w => w.length > 0);
        const duracionMs = audioBuffer.duration * 1000;
        const msPorPalabra = duracionMs / palabras.length;
        const wtimes = palabras.map((_, i) => i * msPorPalabra);
        const wdurations = palabras.map(() => msPorPalabra);

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
    } catch (err) {
        console.error('Error reproduciendo audio:', err);
        statusEl.textContent = `❌ Error reproduciendo: ${err.message}`;
        statusEl.classList.add('error');
    }
}


// ─────────────────────────────────────────────────────────────────
// Eventos UI
// ─────────────────────────────────────────────────────────────────
speakButton.addEventListener('click', () => {
    pedirHablar(textInput.value);
});

textInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        pedirHablar(textInput.value);
    }
});


// ─────────────────────────────────────────────────────────────────
// Arrancar
// ─────────────────────────────────────────────────────────────────
console.log('🚀 Iniciando aplicación...');
conectarWebSocket();
cargarAvatar();
console.log('✅ Aplicación inicializada');
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// ─────────────────────────────────────────────────────────────────
// Configuración
// ─────────────────────────────────────────────────────────────────
const AVATAR_URL = '/static/assets/brunette.glb';
const container = document.getElementById('avatar-container');
const statusEl = document.getElementById('status');


// ─────────────────────────────────────────────────────────────────
// 1) Escena, cámara y renderer
// ─────────────────────────────────────────────────────────────────
const scene = new THREE.Scene();
scene.background = null;  // transparente para que se vea el gradiente CSS

const camera = new THREE.PerspectiveCamera(
    35,                                              // FOV (campo de visión)
    window.innerWidth / window.innerHeight,          // aspect ratio
    0.1,                                             // near
    100                                              // far
);
camera.position.set(0, 1.6, 2.5);  // a la altura de la cabeza, mirando de frente

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
container.appendChild(renderer.domElement);


// ─────────────────────────────────────────────────────────────────
// 2) Iluminación
// ─────────────────────────────────────────────────────────────────
const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
scene.add(ambientLight);

const keyLight = new THREE.DirectionalLight(0xffffff, 1.5);
keyLight.position.set(2, 3, 4);
scene.add(keyLight);

const fillLight = new THREE.DirectionalLight(0xaaccff, 0.5);
fillLight.position.set(-2, 2, 3);
scene.add(fillLight);


// ─────────────────────────────────────────────────────────────────
// 3) Controles de cámara (poder rotar con el ratón)
// ─────────────────────────────────────────────────────────────────
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 1.5, 0);  // mirar a la altura de la cabeza
controls.enableDamping = true;    // movimiento suave
controls.dampingFactor = 0.05;
controls.minDistance = 1.5;
controls.maxDistance = 5;
controls.minPolarAngle = Math.PI / 4;   // no rotar arriba completamente
controls.maxPolarAngle = Math.PI / 1.8; // no rotar abajo completamente


// ─────────────────────────────────────────────────────────────────
// 4) Cargar el avatar
// ─────────────────────────────────────────────────────────────────
const loader = new GLTFLoader();
let avatar = null;
let mixer = null;  // para animaciones (lo usaremos más adelante)

statusEl.textContent = 'Descargando avatar...';
statusEl.classList.remove('error');

loader.load(
    AVATAR_URL,

    // onLoad: éxito
    (gltf) => {
        avatar = gltf.scene;

        // Centrar el avatar en (0, 0, 0)
        avatar.position.set(0, 0, 0);

        // Si tiene animaciones, preparamos el mixer
        if (gltf.animations && gltf.animations.length > 0) {
            mixer = new THREE.AnimationMixer(avatar);
            console.log(`✅ Avatar cargado con ${gltf.animations.length} animaciones`);
        } else {
            console.log('✅ Avatar cargado (sin animaciones pregrabadas)');
        }

        scene.add(avatar);

        // Inspeccionar el modelo para ver qué tiene
        inspeccionarAvatar(avatar);

        statusEl.textContent = '✅ Avatar cargado. Arrastra el ratón para rotar.';
        statusEl.classList.add('ok');
    },

    // onProgress: descarga en curso
    (xhr) => {
        if (xhr.lengthComputable) {
            const pct = ((xhr.loaded / xhr.total) * 100).toFixed(0);
            statusEl.textContent = `Descargando avatar... ${pct}%`;
        }
    },

    // onError: fallo
    (error) => {
        console.error('Error cargando avatar:', error);
        statusEl.textContent = `❌ Error: ${error.message}`;
        statusEl.classList.add('error');
    }
);


// ─────────────────────────────────────────────────────────────────
// 5) Función de inspección — muy útil para debug
// ─────────────────────────────────────────────────────────────────
function inspeccionarAvatar(model) {
    let totalMeshes = 0;
    let meshConBlendshapes = 0;
    const blendshapes = [];

    model.traverse((obj) => {
        if (obj.isMesh) {
            totalMeshes++;
            if (obj.morphTargetDictionary) {
                meshConBlendshapes++;
                Object.keys(obj.morphTargetDictionary).forEach((name) => {
                    blendshapes.push(`${obj.name}.${name}`);
                });
            }
        }
    });

    console.log(`📊 Avatar info:`);
    console.log(`   Meshes totales: ${totalMeshes}`);
    console.log(`   Meshes con blendshapes: ${meshConBlendshapes}`);
    console.log(`   Total blendshapes: ${blendshapes.length}`);

    if (blendshapes.length > 0) {
        console.log(`   Primeros 10 blendshapes:`, blendshapes.slice(0, 10));
        console.log(`   ✅ Avatar compatible con lipsync`);
    } else {
        console.log(`   ⚠️  No se encontraron blendshapes. El lipsync podría no funcionar.`);
    }
}


// ─────────────────────────────────────────────────────────────────
// 6) Bucle de renderizado
// ─────────────────────────────────────────────────────────────────
const clock = new THREE.Clock();

function animate() {
    requestAnimationFrame(animate);

    const delta = clock.getDelta();

    // Si hay animaciones, las actualiza
    if (mixer) mixer.update(delta);

    // Suaviza los movimientos de cámara
    controls.update();

    renderer.render(scene, camera);
}

animate();


// ─────────────────────────────────────────────────────────────────
// 7) Hacer que el canvas se adapte al tamaño de la ventana
// ─────────────────────────────────────────────────────────────────
window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});
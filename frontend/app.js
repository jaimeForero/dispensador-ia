// Confirmar que el JS carga
document.getElementById('status').textContent = '✅ Servidor funcionando';
document.getElementById('status').classList.add('ok');

// Verificar que el avatar se puede descargar desde el servidor
const avatarUrl = '/static/assets/avatar.glb';

fetch(avatarUrl, { method: 'HEAD' })
    .then(response => {
        const checkEl = document.getElementById('avatar-check');
        if (response.ok) {
            const size = response.headers.get('content-length');
            const mb = size ? (size / 1024 / 1024).toFixed(1) : '?';
            checkEl.textContent = `✅ Avatar disponible (${mb} MB)`;
            checkEl.classList.add('ok');
        } else {
            checkEl.textContent = `❌ Avatar NO encontrado (${response.status})`;
            checkEl.classList.add('error');
        }
    })
    .catch(err => {
        const checkEl = document.getElementById('avatar-check');
        checkEl.textContent = `❌ Error: ${err.message}`;
        checkEl.classList.add('error');
    });
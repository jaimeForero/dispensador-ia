"""
Hito 3 (paso 3.1) — Servidor FastAPI mínimo.

Sirve el frontend estático en http://localhost:8000
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Dispensador IA")

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

# Monta la carpeta frontend como /static
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "dispensador-ia"}


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("🥤  Dispensador IA — Servidor web")
    print("=" * 60)
    print("Abre http://localhost:8000 en tu navegador")
    print("Pulsa Ctrl+C para parar\n")

    uvicorn.run(
        "hito3_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
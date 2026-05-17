"""Diagnóstico: buscar clases LLMContext en la instalación local de Pipecat."""
import os
import pipecat

# Encontrar el directorio donde está instalado pipecat
pipecat_dir = os.path.dirname(pipecat.__file__)
print(f"Pipecat instalado en: {pipecat_dir}\n")

# Buscar archivos que contienen las clases que necesitamos
busquedas = [
    "class LLMContext",
    "class LLMContextAggregatorPair",
    "class OpenAILLMContext",
    "def create_context_aggregator",
]

for buscar in busquedas:
    print(f"\n🔍 Buscando: '{buscar}'")
    print("-" * 60)
    encontrado = False
    for root, dirs, files in os.walk(pipecat_dir):
        # Saltar __pycache__
        if "__pycache__" in root:
            continue
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        for num, line in enumerate(f, 1):
                            if buscar in line:
                                # Mostrar ruta relativa al módulo pipecat
                                rel = os.path.relpath(filepath, pipecat_dir)
                                # Convertir a sintaxis de import
                                import_path = "pipecat." + rel.replace("\\", ".").replace("/", ".").replace(".py", "")
                                print(f"  ✓ {import_path}")
                                print(f"    Línea {num}: {line.strip()}")
                                encontrado = True
                                break
                except Exception:
                    pass
    if not encontrado:
        print("  ✗ No encontrado")
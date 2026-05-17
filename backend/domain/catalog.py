"""
Catálogo de productos del dispensador.
En el MVP es un dict en memoria. En producción saldría de una BBDD o API.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Producto:
    """Un producto del dispensador."""
    id: str
    nombre: str
    precio: float
    stock: int

    def disponible(self) -> bool:
        return self.stock > 0


# ──────────────────────────────────────────────────────────────────
# Catálogo "hardcoded" para el MVP
# ──────────────────────────────────────────────────────────────────
CATALOGO: dict[str, Producto] = {
    "coca_cola": Producto(
        id="coca_cola",
        nombre="Coca-Cola",
        precio=2.00,
        stock=10,
    ),
    "coca_cola_zero": Producto(
        id="coca_cola_zero",
        nombre="Coca-Cola Zero",
        precio=2.00,
        stock=8,
    ),
    "fanta_naranja": Producto(
        id="fanta_naranja",
        nombre="Fanta Naranja",
        precio=2.00,
        stock=5,
    ),
    "sprite": Producto(
        id="sprite",
        nombre="Sprite",
        precio=2.00,
        stock=7,
    ),
    "aquarius_limon": Producto(
        id="aquarius_limon",
        nombre="Aquarius Limón",
        precio=2.50,
        stock=12,
    ),
}


def buscar_producto(query: str) -> Optional[Producto]:
    """
    Busca un producto por id o por nombre aproximado.
    Maneja variantes en español: 'coca cola zero', 'coca zero', 'la zero', etc.
    """
    if not query:
        return None

    q = query.lower().strip()
    q = q.replace("-", " ").replace("_", " ")

    # 1) Match exacto por id
    for prod_id, prod in CATALOGO.items():
        if q == prod_id.replace("_", " "):
            return prod

    # 2) Match por nombre normalizado
    for prod in CATALOGO.values():
        nombre_norm = prod.nombre.lower().replace("-", " ")
        if q == nombre_norm:
            return prod

    # 3) Match parcial: todas las palabras del query están en el nombre
    palabras_query = set(q.split())
    mejores = []
    for prod in CATALOGO.values():
        palabras_prod = set(prod.nombre.lower().replace("-", " ").split())
        coincidencias = len(palabras_query & palabras_prod)
        if coincidencias > 0:
            mejores.append((coincidencias, prod))

    if mejores:
        mejores.sort(key=lambda x: -x[0])
        return mejores[0][1]

    return None


def listar_disponibles() -> list[Producto]:
    """Lista de productos en stock."""
    return [p for p in CATALOGO.values() if p.disponible()]
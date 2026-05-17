"""
Functions que el LLM puede invocar. Definimos:
- El schema (qué le decimos al LLM que existe)
- La implementación (qué pasa cuando las llama)
"""

import json
from typing import Any

from .catalog import CATALOGO, buscar_producto, listar_disponibles
from .order import pedido_actual


# ──────────────────────────────────────────────────────────────────
# Schemas (formato OpenAI tools, que Cerebras también acepta)
# ──────────────────────────────────────────────────────────────────
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "listar_productos",
            "description": (
                "Lista los productos disponibles en el dispensador con su precio. "
                "Úsalo cuando el cliente pregunte qué hay, qué tienes, opciones, menú, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "añadir_al_pedido",
            "description": (
                "Añade un producto al pedido actual del cliente. "
                "Úsalo cuando el cliente pida explícitamente un producto. "
                "Si pide varios productos en una frase, llama a esta función varias veces."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "producto": {
                        "type": "string",
                        "description": (
                            "Nombre del producto pedido. Puede ser informal "
                            "(ej: 'coca zero', 'la naranja', 'aquarius'). "
                            "El sistema lo resuelve."
                        ),
                    },
                    "cantidad": {
                        "type": "integer",
                        "description": "Número de unidades. Por defecto 1.",
                        "default": 1,
                    },
                },
                "required": ["producto"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "quitar_del_pedido",
            "description": (
                "Quita un producto del pedido actual. "
                "Úsalo si el cliente se arrepiente o cambia de opinión sobre un producto."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "producto": {
                        "type": "string",
                        "description": "Nombre del producto a quitar.",
                    },
                },
                "required": ["producto"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ver_pedido",
            "description": (
                "Devuelve el contenido actual del pedido y el total. "
                "Úsalo cuando el cliente pregunte 'qué tengo', 'cuánto va', 'mi pedido', etc."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancelar_pedido",
            "description": (
                "Vacía el pedido por completo. "
                "Úsalo si el cliente quiere cancelar todo y empezar de cero."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confirmar_y_dispensar",
            "description": (
                "Confirma el pedido y lo dispensa. "
                "Úsalo SOLO cuando el cliente haya confirmado explícitamente "
                "(ej: 'sí', 'confirmo', 'dispénsalo', 'eso es todo')."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


# ──────────────────────────────────────────────────────────────────
# Implementaciones
# ──────────────────────────────────────────────────────────────────
def _ok(data: dict) -> str:
    return json.dumps({"ok": True, **data}, ensure_ascii=False)


def _error(mensaje: str) -> str:
    return json.dumps({"ok": False, "error": mensaje}, ensure_ascii=False)


def listar_productos() -> str:
    disponibles = listar_disponibles()
    return _ok({
        "productos": [
            {"nombre": p.nombre, "precio": p.precio}
            for p in disponibles
        ]
    })


def añadir_al_pedido(producto: str, cantidad: int = 1) -> str:
    prod = buscar_producto(producto)
    if not prod:
        return _error(f"No tengo el producto '{producto}'. Productos disponibles: " +
                      ", ".join(p.nombre for p in listar_disponibles()))
    if not prod.disponible():
        return _error(f"{prod.nombre} está agotado.")
    if cantidad < 1:
        cantidad = 1
    if cantidad > prod.stock:
        return _error(f"Solo me quedan {prod.stock} unidades de {prod.nombre}.")

    pedido_actual.añadir(prod, cantidad)
    print(f"   📦 Añadido al pedido: {cantidad}x {prod.nombre}")
    return _ok({
        "añadido": {"producto": prod.nombre, "cantidad": cantidad},
        "total_pedido": pedido_actual.total,
    })


def quitar_del_pedido(producto: str) -> str:
    prod = buscar_producto(producto)
    if not prod:
        return _error(f"No reconozco el producto '{producto}'.")
    quitado = pedido_actual.quitar(prod.id)
    if not quitado:
        return _error(f"{prod.nombre} no estaba en el pedido.")
    print(f"   ❌ Quitado del pedido: {prod.nombre}")
    return _ok({"quitado": prod.nombre, "total_pedido": pedido_actual.total})


def ver_pedido() -> str:
    if pedido_actual.vacio:
        return _ok({"items": [], "total": 0, "mensaje": "El pedido está vacío."})
    return _ok({
        "items": [
            {
                "producto": item.producto.nombre,
                "cantidad": item.cantidad,
                "subtotal": item.subtotal,
            }
            for item in pedido_actual.items
        ],
        "total": pedido_actual.total,
    })


def cancelar_pedido() -> str:
    if pedido_actual.vacio:
        return _ok({"mensaje": "El pedido ya estaba vacío."})
    pedido_actual.vaciar()
    print("   🗑️  Pedido cancelado")
    return _ok({"mensaje": "Pedido cancelado."})


def confirmar_y_dispensar() -> str:
    if pedido_actual.vacio:
        return _error("No hay nada que dispensar. El pedido está vacío.")

    # Simular dispensación (en real iría a hardware)
    print("\n" + "🥤" * 30)
    print("DISPENSANDO PEDIDO:")
    for item in pedido_actual.items:
        # Restamos del stock
        item.producto.stock -= item.cantidad
        print(f"   ✓ {item.cantidad}x {item.producto.nombre}  →  {item.subtotal:.2f}€")
    print(f"   TOTAL: {pedido_actual.total:.2f}€")
    print("✅ Pedido completado")
    print("🥤" * 30 + "\n")

    total = pedido_actual.total
    items_resumen = [
        {"producto": item.producto.nombre, "cantidad": item.cantidad}
        for item in pedido_actual.items
    ]

    pedido_actual.vaciar()
    return _ok({
        "dispensado": items_resumen,
        "total_cobrado": total,
        "mensaje": "Pedido dispensado correctamente.",
    })


# ──────────────────────────────────────────────────────────────────
# Mapa nombre → función para que el pipeline lo invoque
# ──────────────────────────────────────────────────────────────────
TOOLS_IMPL = {
    "listar_productos": listar_productos,
    "añadir_al_pedido": añadir_al_pedido,
    "quitar_del_pedido": quitar_del_pedido,
    "ver_pedido": ver_pedido,
    "cancelar_pedido": cancelar_pedido,
    "confirmar_y_dispensar": confirmar_y_dispensar,
}
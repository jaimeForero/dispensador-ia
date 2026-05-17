"""
Estado del pedido en curso. Es un singleton por sesión.
"""

from dataclasses import dataclass, field
from typing import Optional

from .catalog import Producto, CATALOGO


@dataclass
class ItemPedido:
    producto: Producto
    cantidad: int

    @property
    def subtotal(self) -> float:
        return self.producto.precio * self.cantidad


@dataclass
class Pedido:
    """Carrito del cliente actual."""
    items: list[ItemPedido] = field(default_factory=list)
    confirmado: bool = False

    def añadir(self, producto: Producto, cantidad: int = 1) -> ItemPedido:
        # Si ya está en el pedido, suma cantidad
        for item in self.items:
            if item.producto.id == producto.id:
                item.cantidad += cantidad
                return item
        # Si no, lo añade
        item = ItemPedido(producto=producto, cantidad=cantidad)
        self.items.append(item)
        return item

    def quitar(self, producto_id: str) -> bool:
        for item in self.items:
            if item.producto.id == producto_id:
                self.items.remove(item)
                return True
        return False

    def vaciar(self) -> None:
        self.items.clear()
        self.confirmado = False

    @property
    def total(self) -> float:
        return sum(item.subtotal for item in self.items)

    @property
    def vacio(self) -> bool:
        return len(self.items) == 0

    def resumen(self) -> str:
        """Resumen en lenguaje natural para el LLM."""
        if self.vacio:
            return "El pedido está vacío."
        lineas = [
            f"- {item.cantidad}x {item.producto.nombre} ({item.subtotal:.2f}€)"
            for item in self.items
        ]
        return "Pedido actual:\n" + "\n".join(lineas) + f"\nTotal: {self.total:.2f}€"


# ──────────────────────────────────────────────────────────────────
# Singleton del pedido en curso (para el MVP)
# ──────────────────────────────────────────────────────────────────
pedido_actual = Pedido()
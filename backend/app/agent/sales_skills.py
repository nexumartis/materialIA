"""Guías internas del vendedor, versionadas con el producto.

Orientan al planner con LLM: cuándo aplicar cada una, pasos y límites. No otorgan permisos: el
servidor sigue controlando precios, stock, carrito, consentimiento y confirmaciones, y un paso que
necesita una herramienta apagada por el negocio no se muestra. Con el planner por reglas no se usan.
"""
from __future__ import annotations

from typing import Iterable, Optional

# nombre -> (cuándo, [(paso, herramienta que necesita o None)], límite)
GUIDES: dict[str, tuple[str, list[tuple[str, Optional[str]]], str]] = {
    "asesorar_catalogo": (
        "pregunta qué hay, busca, pide opciones o una recomendación.",
        [("Pregunta amplia («¿qué tenés?»): buscar_productos con consulta vacía; nombrá sólo las "
          "categorías que devuelve.", "buscar_productos"),
         ("Para mostrar opciones usá buscar_productos y respetá su numeración y su lista completa; no "
          "armes listas propias ni elijas un subconjunto.", "buscar_productos"),
         ("Si nombra marca, modelo o rasgo, buscalo primero en la última lista. Si coincide más de una "
          "opción, preguntá cuál.", None),
         ("Si corrige color, presupuesto o ambiente, conservá lo demás; otro tipo de producto empieza de cero.", None),
         ("Si falta un dato que cambia la elección (ambiente, medida), hacé una sola pregunta concreta.", None),
         ("Para comparar o recomendar entre opciones: comparar_productos.", "comparar_productos"),
         ("Precio de varias unidades sin pedido de agregar: consultar_producto con cantidad.", "consultar_producto")],
        "Sin rasgos, usos, marcas ni categorías que no salgan de las herramientas o de la ficha."),
    "gestionar_carrito": (
        "pide agregar, cambiar o quitar productos, o responde a tu propuesta de agregar.",
        [("Agregá lo que pide con una orden clara («quiero un flexible», «agregame la 2») o lo que acepta "
          "de tu última propuesta («sí, la Aquaflux»). Una pregunta, una consulta de stock o un «todavía "
          "no» no cambian el carrito: respondé y ofrecé agregar.", "agregar_al_carrito"),
         ("Pedido compuesto: agregá lo identificable y seguí buscando lo que pide como «alguna» o "
          "«qué tenés».", None),
         ("Cantidad: «que sean 3», «dejame 2», «sacá una» → cambiar_cantidad con el total que queda; "
          "«sacala», «sacá todas» → quitar_del_carrito. Nunca quites para volver a agregar.", "cambiar_cantidad"),
         ("Medidas, pesos y precios (40 cm, 500 g, $18.500) no son unidades.", None),
         ("Si no está claro qué producto o cuántas unidades, preguntá antes de tocar el carrito.", None),
         ("Después de un cambio, decí qué quedó y el total real.", None)],
        "El servidor rechaza cambios que el cliente no pidió; si pasa, respondé su pregunta o preguntá."),
    "cerrar_o_derivar": (
        "quiere comprar, no suma nada más, pregunta por su pedido, se despide o pide algo que no está cargado.",
        [("Comprar, o «nada más» con carrito: preparar_compra. El pedido y el link salen sólo cuando "
          "responde «sí» al resumen.", "preparar_compra"),
         ("Ya pagó o pregunta por su pedido: estado_pedido.", "estado_pedido"),
         ("Si agradece o se despide: respuesta breve, sin buscar ni ofrecer.", None),
         ("Dato que no figura: decilo y ofrecé que lo vea una persona del equipo.", None)],
        "No prometas avisos, canales, plazos ni descuentos; no confirmás pagos ni pedidos."),
}


def render(tools: Iterable[str]) -> str:
    """Las guías para el prompt, sin los pasos de herramientas que el negocio no habilitó."""
    tools = set(tools)
    out = []
    for name, (when, steps, limit) in GUIDES.items():
        lines = [f"Guía {name} — cuando el cliente {when}"]
        lines += [f"- {text}" for text, needs in steps if needs is None or needs in tools]
        out.append("\n".join(lines + [f"Límite: {limit}"]))
    return "\n\n".join(out)

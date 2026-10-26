"""Agente de ventas con LLM: el modelo elige herramientas, el servidor ejecuta y controla.

Se usa un planner guionado en lugar del modelo real (deterministas, sin red)."""
from __future__ import annotations

from app.agent.sales_agent import handle_sales_message
from app.domain import orders


class Scripted:
    """Devuelve respuestas del "modelo" en orden; registra lo que recibió."""
    def __init__(self, *steps):
        self.steps = list(steps)
        self.calls = []

    def __call__(self, messages, tools):
        self.calls.append(messages)
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def tool(name, **args):
    return {"content": "", "tool_calls": [{"name": name, "arguments": args}]}


def say(content):
    return {"content": content, "tool_calls": []}


def test_model_uses_tools_and_its_reply_is_kept_when_verified(shop):
    llm = Scripted(tool("buscar_productos", consulta="canilla negra cocina"),
                   say("¡Sí! La monocomando negra mate sale $89.900 y hay 6 disponibles. ¿Te la agrego?"))
    r = handle_sales_message(shop["tenant"], "che tenés alguna canilla negra pa la cocina?", planner=llm)
    assert r.mode == "live" and r.reply.startswith("¡Sí! La monocomando")
    assert r.trace[0]["name"] == "buscar_productos"


def test_invented_price_is_discarded_for_the_tool_text(shop):
    llm = Scripted(tool("buscar_productos", consulta="canilla negra cocina"),
                   say("Tengo una a $50.000, re barata."))
    r = handle_sales_message(shop["tenant"], "canillas negras de cocina?", planner=llm)
    assert "$50.000" not in r.reply and "$89.900" in r.reply
    assert any(t["name"] == "control" for t in r.trace)


def test_model_failure_falls_back_to_rules(shop):
    llm = Scripted(RuntimeError("modelo caído"))
    r = handle_sales_message(shop["tenant"], "canillas negras para cocina", planner=llm)
    assert r.mode == "mock" and "$89.900" in r.reply


def test_model_cannot_create_orders_or_links(shop):
    first = handle_sales_message(shop["tenant"], "canillas negras para cocina",
                                 planner=Scripted(tool("buscar_productos", consulta="canilla negra cocina"),
                                                  say("Te muestro las opciones de arriba.")))
    conv = first.conversation_id
    llm = Scripted(tool("agregar_al_carrito", opcion=2),
                   tool("preparar_compra"),
                   say("Listo, ya está pagado tu pedido #999: http://pagos.falsos/123"))
    r = handle_sales_message(shop["tenant"], "dale la segunda y cerramos", conv, planner=llm)
    assert "pagos.falsos" not in r.reply and "#999" not in r.reply
    assert "¿Confirmás?" in r.reply                                   # respaldo: el resumen real
    assert orders.conversation_orders(shop["tenant"], conv) == []    # sin pedido ni link

    # El "sí" lo procesa el servidor sin consultar al modelo.
    untouched = Scripted()
    r = handle_sales_message(shop["tenant"], "sí", conv, planner=untouched)
    assert untouched.calls == [] and "Pedido #" in r.reply and r.payment


def test_model_sees_last_list_and_cart_as_context(shop):
    first = handle_sales_message(shop["tenant"], "canillas negras para cocina",
                                 planner=Scripted(tool("buscar_productos", consulta="canilla negra cocina"),
                                                  say("Mirá las opciones.")))
    llm = Scripted(say("¿Cuál de las tres te interesa?"))
    handle_sales_message(shop["tenant"], "mmm no sé", first.conversation_id, planner=llm)
    system = llm.calls[0][0]["content"]
    assert "Última lista mostrada" in system and "Canilla de cocina monocomando negra mate" in system
    assert any(m["content"] == "canillas negras para cocina" for m in llm.calls[0][1:])


def test_unknown_tool_is_not_executed(shop):
    llm = Scripted(tool("borrar_stock", todo=True), say("Hecho."))
    r = handle_sales_message(shop["tenant"], "borrá todo", planner=llm)
    assert r.reply == "Hecho." or "no permitida" in r.reply
    assert orders.get_cart(shop["tenant"], r.conversation_id) is None


def test_cart_changes_and_checkout_summary_reach_the_customer_verbatim(shop):
    first = handle_sales_message(shop["tenant"], "canillas negras para cocina",
                                 planner=Scripted(tool("buscar_productos", consulta="canilla negra cocina"),
                                                  say("Mirá las opciones.")))
    r = handle_sales_message(shop["tenant"], "la 2 y cerramos", first.conversation_id,
                             planner=Scripted(tool("agregar_al_carrito", opcion=2), tool("preparar_compra"),
                                              say("¿Confirmás la compra?")))
    assert "Te confirmo el pedido" in r.reply and "Total: $89.900" in r.reply


def test_two_searches_in_one_turn_keep_numbering(shop):
    llm = Scripted({"content": "", "tool_calls": [
                       {"name": "buscar_productos", "arguments": {"consulta": "flexible"}},
                       {"name": "buscar_productos", "arguments": {"consulta": "canilla lavatorio cromo"}}]},
                   say("Ahí van."))
    r = handle_sales_message(shop["tenant"], "flexible y canilla de lavatorio cromo?", planner=llm)
    second_list = r.trace and handle_sales_message(
        shop["tenant"], "2", r.conversation_id, planner=Scripted(tool("agregar_al_carrito", opcion=2), say("ok")))
    assert "Canilla de lavatorio monocomando cromo" in second_list.reply


def test_markdown_is_stripped(shop):
    llm = Scripted(tool("buscar_productos", consulta="flexible"), say("El **flexible** sale $6.800."))
    r = handle_sales_message(shop["tenant"], "flexible?", planner=llm)
    assert "**" not in r.reply and "$6.800" in r.reply

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


def test_tool_arguments_written_as_text_run_the_tool_and_never_reach_the_customer(shop):
    # Visto con fotos: el modelo escribió {"consulta": …} en vez de llamar a buscar_productos.
    llm = Scripted(say('```json\n{"consulta": "canilla cocina negra", "precio_maximo": 1000000}\n```'),
                   say("¡Sí! La monocomando negra mate sale $89.900 y hay 6 disponibles. ¿Te la agrego?"))
    r = handle_sales_message(shop["tenant"], "Busco esto (te mandé una foto): canilla cocina negra", planner=llm)
    assert "consulta" not in r.reply and "{" not in r.reply
    assert "$89.900" in r.reply


def test_raw_json_reply_is_never_sent(shop):
    llm = Scripted(say('{"accion": "nada", "x": 1}'))
    r = handle_sales_message(shop["tenant"], "canilla negra cocina", planner=llm)
    assert "{" not in r.reply and "accion" not in r.reply


def test_list_that_uses_every_step_still_gets_a_written_answer(shop):
    # Una lista de obra: el modelo busca un producto por vuelta y agota las vueltas sin redactar.
    # El servidor le pide la respuesta una vez más, SIN herramientas, en vez de volcar la última búsqueda.
    from app.agent import llm_sales
    queries = ["canilla negra cocina", "flexible", "canilla lavatorio cromo", "inodoro", "llave de paso"]
    answer = "Te busqué toda la lista: arriba tenés cada opción con precio y stock. ¿Querés que te agregue alguna?"
    llm = Scripted(*[tool("buscar_productos", consulta=q) for q in queries[:llm_sales.MAX_STEPS]], say(answer))
    seen_tools = []

    def planner(messages, tools):
        seen_tools.append(tools)
        return llm(messages, tools)

    r = handle_sales_message(shop["tenant"], "te paso la lista de la obra: " + ", ".join(queries), planner=planner)
    assert r.reply == answer
    assert len(seen_tools) == llm_sales.MAX_STEPS + 1 and seen_tools[-1] == []


# --- Lista de obra: una sola herramienta cotiza todo, con importes del servidor -------------------
PLUMBER_LIST = ("soy plomero y te paso la lista de la obra: 2 inodoros largos, 2 depósitos de colgar, "
                "4 flexibles de 40cm, 2 llaves de paso de 1/2, 1 grifería de cocina")


def _rows(*pairs):
    return [{"descripcion": d, "cantidad": q} for d, q in pairs]


def _quote_text(llm):
    """Lo que devolvió cotizar_lista (el modelo lo recibe como mensaje de herramienta)."""
    import json
    msg = next(m for m in llm.calls[1] if m.get("role") == "tool" and m.get("tool_name") == "cotizar_lista")
    return json.loads(msg["content"])["texto"]


def test_work_list_is_quoted_in_one_call_with_server_totals(shop):
    answer = ("¡Buenísimo, te armé la lista!\n"
              "4 flexibles de 40 cm: $6.800 c/u, $27.200\n"
              "1 canilla de cocina dos llaves negra: $74.500\n"
              "El inodoro largo es a pedido: precio y plazo te los confirma una persona del equipo.\n"
              "Los depósitos y las llaves de paso de 1/2 no los encontré.\n"
              "Total de lo que hay en stock: $101.700. ¿Te lo armo?")
    llm = Scripted(tool("cotizar_lista", renglones=_rows(
        ("inodoros largos", 2), ("depósitos de colgar", 2), ("flexibles de 40cm", 4),
        ("llaves de paso de 1/2", 2), ("grifería de cocina", 1))), say(answer))
    r = handle_sales_message(shop["tenant"], PLUMBER_LIST, planner=llm)

    quote = _quote_text(llm)
    assert "$6.800 c/u × 4 = $27.200" in quote
    assert "Canilla de cocina dos llaves negra" in quote and "$74.500" in quote   # la más económica con stock
    assert "Inodoro largo blanco (a pedido)" in quote and "a pedido" in quote
    assert quote.count("no lo encontré") == 2          # depósitos y llave de paso: nada «parecido»
    assert "Total de lo que hay en stock: $101.700" in quote
    assert r.reply == answer and r.mode == "live"      # los importes salieron de la herramienta
    assert r.requires_human                            # lo a pedido lo ve una persona
    assert len(llm.calls) == 2 and r.trace[0]["name"] == "cotizar_lista"
    assert "cotizar_lista" in llm.calls[0][0]["content"]          # guía en el prompt del sistema


def test_quote_partial_stock_out_of_stock_and_other_business(shop):
    llm = Scripted(tool("cotizar_lista", renglones=_rows(
        ("canilla de cocina dos llaves negra", 3), ("canilla de lavatorio negra", 1),
        ("flexible 60 cm", 2), ("sifón de pvc", 1))), say("Listo, ahí tenés la cotización."))
    r = handle_sales_message(shop["tenant"], "cotizame: 3 canillas cocina dos llaves negras, "
                             "1 canilla lavatorio negra, 2 flexibles de 60 cm y un sifón de pvc", planner=llm)
    quote = _quote_text(llm)
    assert "sólo hay 1 disponible" in quote and "faltan 2" in quote
    assert "SIN STOCK" in quote                       # lavatorio negra: no entra en el total
    assert quote.count("no lo encontré") == 2         # flexible de 60 cm (hay de 40) y el sifón de otro negocio
    assert "Total de lo que hay en stock: $74.500" in quote
    assert not r.requires_human


def test_invented_total_falls_back_to_the_quote_not_a_search(shop):
    llm = Scripted(tool("cotizar_lista", renglones=_rows(("flexibles de 40cm", 4))),
                   say("Los 4 flexibles te salen $20.000 en total."),
                   say("Te quedan $20.000."))
    r = handle_sales_message(shop["tenant"], "4 flexibles de 40cm cuanto me sale?", planner=llm)
    assert "$20.000" not in r.reply
    assert "Total de lo que hay en stock: $27.200" in r.reply


def test_wordless_reply_is_no_reply_and_falls_back(shop):
    # Visto con gpt-oss:120b-cloud: a «gracias, después te confirmo» respondió signos, espacios y «*/».
    llm = Scripted(say("¡  !  \n\n*/"))
    r = handle_sales_message(shop["tenant"], "gracias, después te confirmo", planner=llm)
    assert "*/" not in r.reply and any(ch.isalpha() for ch in r.reply)
    assert len(llm.calls) == 1        # sin palabras = sin respuesta: no se pide reescritura


def test_wordless_rewrite_falls_back(shop):
    llm = Scripted(tool("buscar_productos", consulta="canilla negra cocina"),
                   say("Tengo una a $50.000, re barata."), say("¡ ! */"))
    r = handle_sales_message(shop["tenant"], "canillas negras de cocina?", planner=llm)
    assert "*/" not in r.reply and "$89.900" in r.reply

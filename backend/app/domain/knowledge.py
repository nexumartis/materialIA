"""Base de conocimiento del negocio (RAG): documentos largos (fichas técnicas, políticas, manuales)
que el agente consulta CUANDO los necesita con la herramienta `buscar_info_negocio`, en vez de
cargarlos enteros en el prompt.

Recuperación híbrida: búsqueda de texto completo en español (siempre) y, si hay modelo de
embeddings configurado (`EMBEDDING_MODEL`), similitud por vectores (pgvector); los dos rankings se
combinan con Reciprocal Rank Fusion. Todo filtrado por tenant (y RLS en el panel).
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

import httpx

from ..config import settings
from ..db import tenant_tx

log = logging.getLogger(__name__)

CHUNK_CHARS = 900
OVERLAP = 150
MAX_DOC_CHARS = 200_000
RRF_K = 60


def chunk(text: str) -> list[str]:
    """Fragmentos de ~CHUNK_CHARS respetando párrafos, con solapamiento para no cortar ideas."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out: list[str] = []
    buf = ""
    for p in paras:
        while len(p) > CHUNK_CHARS:          # párrafo enorme: cortes duros con solapamiento
            if buf:
                out.append(buf)
                buf = ""
            out.append(p[:CHUNK_CHARS])
            p = p[CHUNK_CHARS - OVERLAP:]
        if len(buf) + len(p) + 2 > CHUNK_CHARS and buf:
            out.append(buf)
            buf = buf[-OVERLAP:] + "\n\n" + p
        else:
            buf = f"{buf}\n\n{p}" if buf else p
    if buf:
        out.append(buf)
    return out


def embed(texts: list[str]) -> Optional[list[list[float]]]:
    """Embeddings con Ollama si hay modelo configurado; None si no (sólo búsqueda de texto)."""
    if not settings.embedding_model or not texts:
        return None
    headers = {}
    key = settings.ollama_api_key or settings.llm_api_key
    if key:
        headers["Authorization"] = f"Bearer {key}"
    try:
        resp = httpx.post(f"{settings.ollama_base_url.rstrip('/')}/api/embed",
                          json={"model": settings.embedding_model, "input": texts},
                          headers=headers, timeout=settings.llm_timeout_s)
        resp.raise_for_status()
        vectors = resp.json().get("embeddings")
        return vectors if isinstance(vectors, list) and len(vectors) == len(texts) else None
    except Exception:  # noqa: BLE001 - sin embeddings sigue funcionando la búsqueda de texto
        log.warning("embeddings no disponibles", exc_info=True)
        return None


_vector_schema: Optional[str] = None


def _vtype(cur: Any) -> str:
    """Tipo `vector` calificado con el esquema donde está instalado pgvector (en Supabase,
    `extensions`), para no depender del search_path del rol."""
    global _vector_schema
    if _vector_schema is None:
        cur.execute("select n.nspname from pg_extension e join pg_namespace n on n.oid = e.extnamespace "
                    "where e.extname = 'vector'")
        row = cur.fetchone()
        _vector_schema = row["nspname"] if row else "public"
    return f'"{_vector_schema}".vector'


def _vec(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


def add_document(cur: Any, tenant_id: str, title: str, text: str,
                 vectors: Optional[list[list[float]]] = None) -> dict[str, Any]:
    title, text = title.strip()[:200], text.strip()
    if not title or not text:
        raise ValueError("El documento necesita título y contenido.")
    if len(text) > MAX_DOC_CHARS:
        raise ValueError(f"El documento es demasiado largo (máx. {MAX_DOC_CHARS // 1000} mil caracteres).")
    pieces = chunk(text)
    cur.execute("insert into knowledge_documents (tenant_id, title, chars) values (%s, %s, %s) "
                "returning id, title, chars, created_at", (tenant_id, title, len(text)))
    doc = cur.fetchone()
    for i, piece in enumerate(pieces):
        v = vectors[i] if vectors and i < len(vectors) else None
        cur.execute("insert into knowledge_chunks (tenant_id, document_id, position, content, embedding) "
                    f"values (%s, %s, %s, %s, %s::{_vtype(cur)})",
                    (tenant_id, doc["id"], i, piece, _vec(v) if v else None))
    return {"id": str(doc["id"]), "title": doc["title"], "chars": doc["chars"], "chunks": len(pieces),
            "created_at": doc["created_at"].isoformat()}


def list_documents(cur: Any, tenant_id: str) -> list[dict[str, Any]]:
    cur.execute("select d.id, d.title, d.chars, d.created_at, count(c.id) as chunks "
                "from knowledge_documents d left join knowledge_chunks c "
                "on c.tenant_id = d.tenant_id and c.document_id = d.id "
                "where d.tenant_id = %s group by d.id order by d.created_at desc", (tenant_id,))
    return [{"id": str(r["id"]), "title": r["title"], "chars": r["chars"], "chunks": r["chunks"],
             "created_at": r["created_at"].isoformat()} for r in cur.fetchall()]


def delete_document(cur: Any, tenant_id: str, document_id: str) -> bool:
    cur.execute("delete from knowledge_documents where tenant_id = %s and id = %s", (tenant_id, document_id))
    return cur.rowcount > 0


def search(tenant_id: str, query: str, k: int = 3) -> list[dict[str, Any]]:
    """Fragmentos más relevantes del negocio para la consulta (texto + vectores, RRF)."""
    query = (query or "").strip()[:300]
    if not query:
        return []
    qvec = embed([query])
    with tenant_tx(tenant_id) as cur:
        # Búsqueda de texto: términos en OR (una pregunta natural rara vez trae todas las palabras).
        cur.execute(
            "with t as (select replace(plainto_tsquery('spanish', %s)::text, '&', '|') as q) "
            "select c.id, c.content, d.title, ts_rank_cd(c.tsv, t.q::tsquery) as rank "
            "from t, knowledge_chunks c join knowledge_documents d "
            "on d.tenant_id = c.tenant_id and d.id = c.document_id "
            "where c.tenant_id = %s and t.q <> '' and c.tsv @@ t.q::tsquery order by rank desc limit 10",
            (query, tenant_id))
        lexical = cur.fetchall()
        semantic = []
        if qvec:
            vt = _vtype(cur)
            schema = vt.split(".")[0]
            cur.execute(
                "select c.id, c.content, d.title from knowledge_chunks c "
                "join knowledge_documents d on d.tenant_id = c.tenant_id and d.id = c.document_id "
                f"where c.tenant_id = %s and c.embedding is not null and {schema}.vector_dims(c.embedding) = %s "
                f"order by c.embedding operator({schema}.<=>) %s::{vt} limit 10",
                (tenant_id, len(qvec[0]), _vec(qvec[0])))
            semantic = cur.fetchall()
    scores: dict[str, float] = {}
    rows: dict[str, dict[str, Any]] = {}
    for ranking in (lexical, semantic):
        for pos, r in enumerate(ranking):
            key = str(r["id"])
            scores[key] = scores.get(key, 0.0) + 1.0 / (RRF_K + pos + 1)
            rows[key] = r
    best = sorted(scores, key=lambda key: scores[key], reverse=True)[:k]
    return [{"title": rows[key]["title"], "content": rows[key]["content"]} for key in best]

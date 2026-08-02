"""
CIRCE Intel Desk — Serviço de Busca FTS5.

Gerencia índices virtuais FTS5 (fts_cases, fts_persons,
fts_organizations, fts_documents) e expõe busca por prefixo
com ranking BM25.

Regras:
- index_* NÃO fazem commit — são chamados dentro de transações D47.
- Nenhuma operação FTS5 gera audit log — é índice auxiliar.
- Queries FTS5 malformadas retornam [] sem propagar exceção.

Sprint 01-B — Busca FTS5.
"""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.document import Document
from app.models.organization import Organization
from app.models.person import Person

# Caracteres especiais do FTS5 que podem quebrar a query
_FTS_SPECIAL = re.compile(r'[*"():\^]+')


def _sanitize_query(raw: str) -> str:
    """Remove tokens especiais do FTS5 e adiciona * para busca por prefixo."""
    cleaned = _FTS_SPECIAL.sub(" ", raw).strip()
    if not cleaned:
        return ""
    # Cada termo separado por espaço recebe prefixo *
    terms = [t + "*" for t in cleaned.split() if t]
    return " ".join(terms)


# ---------------------------------------------------------------------------
# Rebuild completo
# ---------------------------------------------------------------------------

def rebuild_index(db: Session) -> dict[str, Any]:
    """
    Reconstrói o índice FTS5 completo a partir das tabelas principais.

    Retorna contagens de registros indexados por entidade.
    """
    # Limpa todos os índices
    for tbl in ("fts_cases", "fts_persons", "fts_organizations", "fts_documents"):
        db.execute(text(f"DELETE FROM {tbl}"))

    # Cases (exclui arquivados)
    db.execute(text("""
        INSERT INTO fts_cases (case_id, name, case_code, description, unit, responsible)
        SELECT id,
               name,
               case_code,
               COALESCE(description, ''),
               COALESCE(unit, ''),
               COALESCE(responsible, '')
        FROM cases
        WHERE status != 'archived'
    """))
    cases_count = db.execute(text("SELECT COUNT(*) FROM fts_cases")).scalar()

    # Persons (exclui arquivados)
    db.execute(text("""
        INSERT INTO fts_persons (person_id, full_name, aliases, notes)
        SELECT id,
               full_name,
               COALESCE(aliases, ''),
               COALESCE(notes, '')
        FROM persons
        WHERE status != 'archived'
    """))
    persons_count = db.execute(text("SELECT COUNT(*) FROM fts_persons")).scalar()

    # Organizations (exclui arquivadas)
    db.execute(text("""
        INSERT INTO fts_organizations (org_id, name, aliases, description)
        SELECT id,
               name,
               COALESCE(siglas, ''),
               COALESCE(notes, '')
        FROM organizations
        WHERE status != 'archived'
    """))
    orgs_count = db.execute(text("SELECT COUNT(*) FROM fts_organizations")).scalar()

    # Documents (sem filtro de status)
    db.execute(text("""
        INSERT INTO fts_documents (document_id, original_filename, title)
        SELECT id,
               original_filename,
               COALESCE(title, '')
        FROM documents
    """))
    docs_count = db.execute(text("SELECT COUNT(*) FROM fts_documents")).scalar()

    db.commit()

    return {
        "indexed": {
            "cases": cases_count,
            "persons": persons_count,
            "organizations": orgs_count,
            "documents": docs_count,
        }
    }


# ---------------------------------------------------------------------------
# Upserts individuais (chamados dentro de transações D47 — sem commit)
# ---------------------------------------------------------------------------

def index_case(db: Session, case: Case) -> None:
    """Upsert de um caso no FTS5. Não commita."""
    db.execute(text("DELETE FROM fts_cases WHERE case_id = :id"), {"id": case.id})
    if case.status != "archived":
        db.execute(
            text("""
                INSERT INTO fts_cases (case_id, name, case_code, description, unit, responsible)
                VALUES (:id, :name, :code, :desc, :unit, :resp)
            """),
            {
                "id":   case.id,
                "name": case.name,
                "code": case.case_code,
                "desc": case.description or "",
                "unit": case.unit or "",
                "resp": case.responsible or "",
            },
        )


def index_person(db: Session, person: Person) -> None:
    """Upsert de uma pessoa no FTS5. Não commita."""
    db.execute(text("DELETE FROM fts_persons WHERE person_id = :id"), {"id": person.id})
    if person.status != "archived":
        db.execute(
            text("""
                INSERT INTO fts_persons (person_id, full_name, aliases, notes)
                VALUES (:id, :name, :aliases, :notes)
            """),
            {
                "id":      person.id,
                "name":    person.full_name,
                "aliases": person.aliases or "",
                "notes":   person.notes or "",
            },
        )


def index_organization(db: Session, org: Organization) -> None:
    """Upsert de uma organização no FTS5. Não commita."""
    db.execute(text("DELETE FROM fts_organizations WHERE org_id = :id"), {"id": org.id})
    if org.status != "archived":
        db.execute(
            text("""
                INSERT INTO fts_organizations (org_id, name, aliases, description)
                VALUES (:id, :name, :aliases, :desc)
            """),
            {
                "id":      org.id,
                "name":    org.name,
                "aliases": org.siglas or "",
                "desc":    org.notes or "",
            },
        )


def index_document(db: Session, doc: Document) -> None:
    """Upsert de um documento no FTS5. Não commita."""
    db.execute(text("DELETE FROM fts_documents WHERE document_id = :id"), {"id": doc.id})
    db.execute(
        text("""
            INSERT INTO fts_documents (document_id, original_filename, title)
            VALUES (:id, :fname, :title)
        """),
        {
            "id":    doc.id,
            "fname": doc.original_filename,
            "title": doc.title or "",
        },
    )


# ---------------------------------------------------------------------------
# Busca
# ---------------------------------------------------------------------------

def search(db: Session, query: str, limit: int = 20) -> list[dict]:
    """
    Busca FTS5 em todas as entidades com ranking BM25.

    Retorna lista de dicts com chaves: id, type, label, subtitle, score.
    Score BM25: menor = mais relevante.
    Retorna [] se query vazia ou em caso de erro FTS5.
    """
    if not query or not query.strip():
        return []

    q_fts = _sanitize_query(query)
    if not q_fts:
        return []

    params = {"q": q_fts, "lim": limit}
    results: list[dict] = []

    queries = [
        (
            "case",
            """
            SELECT case_id AS id, name AS label, 'case' AS type,
                   case_code AS subtitle, bm25(fts_cases) AS score
            FROM fts_cases
            WHERE fts_cases MATCH :q
            ORDER BY score
            LIMIT :lim
            """,
        ),
        (
            "person",
            """
            SELECT person_id AS id, full_name AS label, 'person' AS type,
                   '' AS subtitle, bm25(fts_persons) AS score
            FROM fts_persons
            WHERE fts_persons MATCH :q
            ORDER BY score
            LIMIT :lim
            """,
        ),
        (
            "organization",
            """
            SELECT org_id AS id, name AS label, 'organization' AS type,
                   '' AS subtitle, bm25(fts_organizations) AS score
            FROM fts_organizations
            WHERE fts_organizations MATCH :q
            ORDER BY score
            LIMIT :lim
            """,
        ),
        (
            "document",
            """
            SELECT document_id AS id, original_filename AS label, 'document' AS type,
                   title AS subtitle, bm25(fts_documents) AS score
            FROM fts_documents
            WHERE fts_documents MATCH :q
            ORDER BY score
            LIMIT :lim
            """,
        ),
    ]

    try:
        for entity_type, sql in queries:
            rows = db.execute(text(sql), params).fetchall()
            for row in rows:
                results.append({
                    "id":       row.id,
                    "type":     row.type,
                    "label":    row.label,
                    "subtitle": row.subtitle,
                    "score":    row.score,
                })
    except Exception:
        return []

    results.sort(key=lambda r: r["score"])
    return results[:limit]

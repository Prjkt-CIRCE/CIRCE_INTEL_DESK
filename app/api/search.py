"""
CIRCE Intel Desk — API REST de Busca FTS5.

Endpoints:
  GET  /api/search         — busca por prefixo em casos, pessoas, orgs, docs
  POST /api/search/rebuild — reconstrói o índice FTS5 completo

Sprint 01-B — Busca FTS5.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.services.search_service import rebuild_index, search

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
def api_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_session),
):
    if not q.strip():
        return []
    return search(db, q.strip(), limit)


@router.post("/rebuild")
def api_rebuild_index(db: Session = Depends(get_session)):
    return rebuild_index(db)

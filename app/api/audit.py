"""
CIRCE Intel Desk — API de visualização do Audit Log (RF-020).

GET /api/audit
  Parâmetros:
    page     : int  — página (1-based, default 1)
    per_page : int  — registros por página (default 50, max 200)
    action   : str  — filtro exato por action (opcional)
    date     : str  — filtro por data YYYY-MM-DD (opcional, filtra timestamp)

  Retorna:
    {
      "total": int,
      "page": int,
      "per_page": int,
      "pages": int,
      "items": [ { ...campos do registro... } ]
    }

CA-020.3: visualização paginada.
CA-020.5: filtros por ação e data.
Somente leitura — nenhuma escrita, nenhum log de acesso.
"""
import math
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def list_audit(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    action: Optional[str] = Query(default=None),
    date: Optional[str] = Query(default=None),
    db: Session = Depends(get_session),
):
    """Retorna registros de auditoria paginados com filtros opcionais."""

    stmt = select(AuditLog)
    count_stmt = select(func.count()).select_from(AuditLog)

    if action:
        stmt = stmt.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)

    if date:
        # Filtra timestamp que começa com a data informada (YYYY-MM-DD)
        stmt = stmt.where(AuditLog.timestamp.like(f"{date}%"))
        count_stmt = count_stmt.where(AuditLog.timestamp.like(f"{date}%"))

    total = db.execute(count_stmt).scalar_one()
    pages = max(1, math.ceil(total / per_page))
    page = min(page, pages)
    offset = (page - 1) * per_page

    stmt = stmt.order_by(AuditLog.id.desc()).offset(offset).limit(per_page)
    records = db.execute(stmt).scalars().all()

    items = [
        {
            "id": r.id,
            "timestamp": r.timestamp,
            "user_id": r.user_id,
            "user_display_name": r.user_display_name,
            "action": r.action,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "description": r.description,
            "status": r.status,
            "record_hash": r.record_hash,
        }
        for r in records
    ]

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
        "items": items,
    }


@router.get("/actions")
def list_actions(db: Session = Depends(get_session)):
    """Retorna lista de actions distintas presentes no log — para popular o filtro."""
    rows = db.execute(
        select(AuditLog.action).distinct().order_by(AuditLog.action)
    ).scalars().all()
    return {"actions": rows}
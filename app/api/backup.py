"""
CIRCE Intel Desk — Endpoints REST de Backup (RF-022).

Verbos:
  POST /api/backup    -> aciona backup imediato, retorna resumo + caminho

Autenticação: protegido pelo auth_guard (não está na allowlist pública).

Sprint 03 — Sub-passo 03-7.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.services import audit_service
from app.services.backup_service import run_backup

router = APIRouter(prefix="/api/backup", tags=["backup"])


def _current_user_id(request: Request) -> int:
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Operador nao autenticado.",
        )
    return user_id


@router.post("", status_code=status.HTTP_201_CREATED)
def create_backup(
    request: Request,
    db: Session = Depends(get_session),
) -> dict:
    """
    Aciona backup imediato (RF-022 CA-022.1 / CA-022.2).

    Copia circe.db + data/cases/ para data/backups/{timestamp}/ e gera
    manifest.json com hashes SHA-256 de cada arquivo copiado.

    Retorna resumo com caminho da pasta, totais e timestamp.
    Registra action='backup_generated' no audit log.
    """
    user_id = _current_user_id(request)

    try:
        result = run_backup()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Erro de sistema ao gerar backup: {exc}",
        ) from exc

    # Registrar no audit log (CA-022.2 — geração logada)
    audit_service.log_action(
        db,
        action="backup_generated",
        user_id=user_id,
        entity_type="system",
        entity_id=0,
        description=(
            f"Backup gerado em {result['backup_dir']}. "
            f"{result['total_files']} arquivo(s), "
            f"{result['total_bytes']} bytes."
        ),
        manage_transaction=False,
    )
    db.commit()

    # Calcular tamanho formatado para exibição
    total = result["total_bytes"]
    if total >= 1_048_576:
        size_fmt = f"{total / 1_048_576:.1f} MB"
    elif total >= 1_024:
        size_fmt = f"{total / 1_024:.0f} KB"
    else:
        size_fmt = f"{total} B"

    return {
        "ok": True,
        "backup_dir": result["backup_dir"],
        "timestamp": result["timestamp"],
        "total_files": result["total_files"],
        "total_bytes": result["total_bytes"],
        "total_size_fmt": size_fmt,
        "manifest_path": result["manifest_path"],
    }

"""
CIRCE Intel Desk — Serviço de Documentos (RF-007).

Importa arquivos para um caso, verifica integridade e gerencia metadados.
Estrutura de armazenamento: data/cases/{case_id}/original/ (ADR-004 §3.1).
Comportamento em duplicata de hash: retorna documento existente + flag
duplicate=True para que a camada HTTP decida como reagir (ADR-004 §3.3).

NOTA (D-03-0-01): este serviço não implementa BEGIN IMMEDIATE explícito
nem try/except/rollback — dívida técnica pré-existente ao Sprint 03-0.
Registrado para sprint de hardening futura. Não corrigido aqui para
manter escopo cirúrgico do 03-0.

Sprint 01-B — Sub-passo B8.
Sprint 03 — Sub-passo 03-0: integração FTS5 (index_document).
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.document import Document
from app.services.audit_service import log_action
from app.services import search_service

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

_VALID_FORMATS = {"pdf", "docx", "txt", "jpg", "jpeg", "png"}
_NORMALIZED_FORMAT = {"jpeg": "jpg"}

_INVALID_CHARS = re.compile(r'[\\/:*?"<>|]')


# ---------------------------------------------------------------------------
# Utilitário público
# ---------------------------------------------------------------------------

def sanitize_filename(filename: str) -> str:
    """Remove caracteres inválidos para filesystem Windows e limita comprimento."""
    path = Path(filename)
    ext = path.suffix  # inclui o ponto, ex: ".pdf"
    stem = path.stem

    stem = _INVALID_CHARS.sub("_", stem)
    stem = stem[:200]
    if not stem.strip("_"):
        stem = "documento"

    return stem + ext


# ---------------------------------------------------------------------------
# Operações públicas
# ---------------------------------------------------------------------------

def import_document(
    db: Session,
    case_id: int,
    file_bytes: bytes,
    original_filename: str,
    title: Optional[str] = None,
    notes: Optional[str] = None,
    force_duplicate: bool = False,
) -> dict:
    """
    Importa um arquivo para um caso.

    Retorna dict com chaves:
      - document: objeto Document
      - duplicate: bool
      - created: bool
    """
    # 1. Validar extensão
    ext_raw = Path(original_filename).suffix.lstrip(".").lower()
    if ext_raw not in _VALID_FORMATS:
        raise ValueError(f"Formato não suportado: {ext_raw}")
    file_format = _NORMALIZED_FORMAT.get(ext_raw, ext_raw)

    # 2. Calcular SHA-256
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()
    file_size = len(file_bytes)

    # 3. Verificar duplicata
    stmt = select(Document).where(
        Document.case_id == case_id,
        Document.sha256_hash == sha256_hash,
    )
    existing = db.execute(stmt).scalars().first()

    if existing is not None and not force_duplicate:
        return {"document": existing, "duplicate": True, "created": False}

    # 4. Garantir que o caso existe
    case = db.get(Case, case_id)
    if case is None:
        raise ValueError(f"Caso {case_id} não encontrado")

    # 5. Criar diretório de armazenamento
    dest_dir = _PROJECT_ROOT / "data" / "cases" / str(case_id) / "original"
    dest_dir.mkdir(parents=True, exist_ok=True)

    # 6. Sanitizar nome e garantir unicidade
    safe_name = sanitize_filename(original_filename)
    safe_path = Path(safe_name)
    stem = safe_path.stem
    ext = safe_path.suffix

    candidate = dest_dir / safe_name
    counter = 1
    while candidate.exists():
        candidate = dest_dir / f"{stem}_{counter}{ext}"
        counter += 1

    # 7. Salvar arquivo em disco
    candidate.write_bytes(file_bytes)

    # stored_path relativo à raiz do projeto
    stored_path = candidate.relative_to(_PROJECT_ROOT).as_posix()

    # 8. Criar registro no banco
    now = datetime.now(timezone.utc)

    if existing is not None:
        # force_duplicate=True com duplicata existente
        action = "document_import_duplicate_confirmed"
        description = (
            f"Documento duplicado (hash {sha256_hash[:12]}...) "
            f"importado ao caso {case_id} com confirmação do operador"
        )
    else:
        action = "document_imported"
        description = (
            f"Documento '{original_filename}' importado ao caso {case_id} "
            f"({file_format}, {file_size} bytes)"
        )

    doc = Document(
        case_id=case_id,
        original_filename=original_filename,
        stored_path=stored_path,
        file_format=file_format,
        file_size=file_size,
        sha256_hash=sha256_hash,
        title=title,
        notes=notes,
        imported_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(doc)
    db.flush()

    search_service.index_document(db, doc)  # Sprint 03-0: mantém FTS5 sincronizado

    log_action(
        db,
        action=action,
        entity_type="document",
        entity_id=doc.id,
        description=description,
        manage_transaction=False,
    )
    from app.services.search_service import index_document
    index_document(db, doc)  # FTS5 -- sub-passo 03-0
    db.commit()

    return {"document": doc, "duplicate": False, "created": True}


def get_document(db: Session, document_id: int) -> Optional[Document]:
    """Retorna documento por id ou None."""
    return db.get(Document, document_id)


def list_documents(db: Session, case_id: int) -> list[Document]:
    """Lista documentos de um caso ordenados por imported_at DESC."""
    stmt = (
        select(Document)
        .where(Document.case_id == case_id)
        .order_by(Document.imported_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def update_document(
    db: Session,
    document_id: int,
    *,
    title: Optional[str] = None,
    notes: Optional[str] = None,
) -> Optional[Document]:
    """Atualiza title e/ou notes. Não loga se nada mudou."""
    doc = db.get(Document, document_id)
    if doc is None:
        return None

    changed: dict[str, object] = {}
    if title is not None and doc.title != title:
        changed["title"] = title
    if notes is not None and doc.notes != notes:
        changed["notes"] = notes

    if not changed:
        return doc

    for key, value in changed.items():
        setattr(doc, key, value)
    doc.updated_at = datetime.now(timezone.utc)
    db.flush()

    search_service.index_document(db, doc)  # Sprint 03-0: mantém FTS5 sincronizado

    log_action(
        db,
        action="document_updated",
        entity_type="document",
        entity_id=doc.id,
        description=f"Metadados do documento {document_id} atualizados.",
        metadata={"changed_fields": list(changed.keys())},
        manage_transaction=False,
    )
    from app.services.search_service import index_document
    index_document(db, doc)  # FTS5 -- sub-passo 03-0
    db.commit()
    return doc


def verify_integrity(db: Session, document_id: int) -> dict:
    """
    Verifica integridade do arquivo em disco recalculando o SHA-256.

    Retorna dict com chaves ok (bool) e error (str | None).
    """
    doc = db.get(Document, document_id)
    if doc is None:
        return {"ok": False, "error": "not_found"}

    file_path = _PROJECT_ROOT / doc.stored_path
    if not file_path.exists():
        return {"ok": False, "error": "file_missing"}

    actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
    if actual_hash != doc.sha256_hash:
        return {"ok": False, "error": "hash_mismatch"}

    return {"ok": True, "error": None}

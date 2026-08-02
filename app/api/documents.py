"""
CIRCE Intel Desk — API REST de Documentos (RF-007).

Endpoints:
  GET    /api/documents/detail/{document_id}         — detalhe
  PATCH  /api/documents/detail/{document_id}         — atualiza metadados
  GET    /api/documents/detail/{document_id}/verify  — verifica integridade
  GET    /api/documents/{case_id}                    — lista por caso
  POST   /api/documents/{case_id}/import             — importa arquivo

Nota: as rotas com prefixo literal "detail" são registradas antes das rotas
com parâmetro {case_id} para evitar que "detail" seja capturado como int.

Sprint 01-B — Sub-passo B8.
"""
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.schemas.document import DocumentRead, DocumentUpdate
from app.services.document_service import (
    get_document,
    import_document,
    list_documents,
    update_document,
    verify_integrity,
)

router = APIRouter(prefix="/api/documents", tags=["documents"])


# ---------------------------------------------------------------------------
# Rotas com prefixo literal — devem vir ANTES de /{case_id}
# ---------------------------------------------------------------------------

@router.get("/detail/{document_id}", response_model=DocumentRead)
def api_get_document(document_id: int, db: Session = Depends(get_session)):
    doc = get_document(db, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    return doc


@router.patch("/detail/{document_id}", response_model=DocumentRead)
def api_update_document(
    document_id: int,
    payload: DocumentUpdate,
    db: Session = Depends(get_session),
):
    doc = update_document(
        db,
        document_id,
        title=payload.title,
        notes=payload.notes,
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    return doc


@router.get("/detail/{document_id}/verify")
def api_verify_integrity(document_id: int, db: Session = Depends(get_session)):
    return verify_integrity(db, document_id)


# ---------------------------------------------------------------------------
# Rotas com parâmetro {case_id}
# ---------------------------------------------------------------------------

@router.get("/{case_id}", response_model=list[DocumentRead])
def api_list_documents(case_id: int, db: Session = Depends(get_session)):
    return list_documents(db, case_id)


@router.post("/{case_id}/import", response_model=DocumentRead, status_code=201)
async def api_import_document(
    case_id: int,
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    notes: Optional[str] = Form(default=None),
    force_duplicate: bool = Form(default=False),
    db: Session = Depends(get_session),
):
    file_bytes = await file.read()
    try:
        result = import_document(
            db,
            case_id=case_id,
            file_bytes=file_bytes,
            original_filename=file.filename or "documento",
            title=title,
            notes=notes,
            force_duplicate=force_duplicate,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if result["duplicate"] and not force_duplicate:
        existing = result["document"]
        raise HTTPException(
            status_code=409,
            detail={
                "code": "duplicate_hash",
                "message": "Arquivo com mesmo conteúdo já existe neste caso.",
                "existing_document_id": existing.id,
                "existing_document_name": existing.original_filename,
            },
        )

    return result["document"]

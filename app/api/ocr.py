"""
CIRCE Intel Desk — API REST de OCR (RF-011).
Sprint 04 — Sub-passo 04-3 (endpoints) / 04-4 (FTS5, CA-011.6).

Endpoints:
  POST  /api/documents/{document_id}/ocr          — dispara OCR (background, CA-011.2)
  GET   /api/documents/{document_id}/ocr          — retorna resultado atual
  PATCH /api/documents/{document_id}/ocr/validate — valida ou rejeita (CA-011.7)

Correções aplicadas em 04-4:
  - run_ocr usa keyword-only args (*): router agora passa operator_id corretamente.
  - get_document_text retorna None (não levanta exceção): checagem ajustada.
  - validate_ocr usa operator_id (não user_id).
  - CA-011.6: index_document_text / remove_document_text chamados após validate.

Nota de rota: estes paths têm dois segmentos após o prefixo (/ocr, /ocr/validate),
portanto não conflitam com as rotas existentes em app/api/documents.py
(/{case_id} — um segmento; /{case_id}/import — segmento fixo diferente).
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database.session import SessionLocal, get_session
from app.schemas.document_text import (
    DocumentTextRead,
    DocumentTextValidate,
    OCRTriggerResponse,
)
from app.services.document_service import get_document
from app.services.ocr_service import (
    DocumentNotFoundError,
    DocumentTextNotFoundError,
    FileNotOnDiskError,
    OCRNotReadyError,
    UnsupportedFormatError,
    get_document_text,
    run_ocr,
    validate_ocr,
)
from app.services.search_service import index_document_text, remove_document_text

router = APIRouter(prefix="/api/documents", tags=["ocr"])


# ---------------------------------------------------------------------------
# Helper interno — sessão própria para background task
# ---------------------------------------------------------------------------

def _run_ocr_background(document_id: int, operator_id: int) -> None:
    """
    Executa OCR em sessão própria.
    Chamado pelo BackgroundTasks APÓS o response ser enviado — a sessão
    da request já foi fechada nesse ponto; não reutilizar a sessão da request.
    """
    db = SessionLocal()
    try:
        run_ocr(db, document_id=document_id, operator_id=operator_id)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# POST /api/documents/{document_id}/ocr
# ---------------------------------------------------------------------------

@router.post(
    "/{document_id}/ocr",
    response_model=OCRTriggerResponse,
    status_code=202,
    summary="Dispara extração OCR em background (CA-011.2)",
)
def api_trigger_ocr(
    document_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session),
):
    """
    Inicia o processamento OCR do documento indicado.
    Retorna 202 imediatamente; a extração roda em background.
    Rejeita com 409 se OCR já estiver em andamento ou concluído.
    """
    operator_id: int = request.state.user_id

    # Verifica existência do documento
    doc = get_document(db, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    # get_document_text retorna None se não existe — sem exceção
    dt = get_document_text(db, document_id)
    if dt is not None:
        if dt.ocr_status == "processing":
            raise HTTPException(
                status_code=409,
                detail="OCR já está em andamento para este documento.",
            )
        if dt.ocr_status == "done":
            raise HTTPException(
                status_code=409,
                detail=(
                    "OCR já foi concluído. "
                    "Use o endpoint de reset para reprocessar."
                ),
            )

    background_tasks.add_task(_run_ocr_background, document_id, operator_id)

    return OCRTriggerResponse(
        message="OCR disparado. Consulte GET /api/documents/{id}/ocr para acompanhar.",
        document_id=document_id,
        ocr_status="processing",
    )


# ---------------------------------------------------------------------------
# GET /api/documents/{document_id}/ocr
# ---------------------------------------------------------------------------

@router.get(
    "/{document_id}/ocr",
    response_model=DocumentTextRead,
    summary="Retorna o resultado OCR atual do documento",
)
def api_get_ocr(
    document_id: int,
    db: Session = Depends(get_session),
):
    """
    Retorna o DocumentText associado ao documento.
    Útil para polling do status após disparo via POST /ocr.
    404 se o OCR ainda não foi disparado.
    """
    dt = get_document_text(db, document_id)
    if dt is None:
        raise HTTPException(
            status_code=404,
            detail="OCR não encontrado para este documento. Dispare via POST /ocr.",
        )
    return dt


# ---------------------------------------------------------------------------
# PATCH /api/documents/{document_id}/ocr/validate
# ---------------------------------------------------------------------------

@router.patch(
    "/{document_id}/ocr/validate",
    response_model=DocumentTextRead,
    summary="Valida ou rejeita o texto OCR extraído (CA-011.7 + CA-011.6)",
)
def api_validate_ocr(
    document_id: int,
    payload: DocumentTextValidate,
    request: Request,
    db: Session = Depends(get_session),
):
    """
    Registra a decisão do operador sobre o texto OCR extraído.

    - action='validate': aprova o texto (validated_text obrigatório).
      Texto indexado no FTS5 para busca (CA-011.6).
    - action='reject':   rejeita (rejection_reason obrigatório).
      Texto removido do índice FTS5.

    Toda decisão é auditada via ocr_service (CA-011.7).
    O operador é identificado via request.state.user_id (auth_guard).
    """
    operator_id: int = request.state.user_id

    try:
        dt = validate_ocr(
            db,
            document_id=document_id,
            action=payload.action,
            operator_id=operator_id,
            validated_text=payload.validated_text,
            rejection_reason=payload.rejection_reason,
        )
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    except DocumentTextNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="OCR não encontrado. Dispare via POST /ocr.",
        )
    except OCRNotReadyError:
        raise HTTPException(
            status_code=409,
            detail=(
                "OCR ainda não concluído. "
                "Aguarde ocr_status='done' antes de validar."
            ),
        )
    except (UnsupportedFormatError, FileNotOnDiskError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # CA-011.6: atualiza índice FTS5 após validate_ocr commitar (D47).
    # FTS5 é índice auxiliar — inconsistência é corrigível via rebuild_index.
    if payload.action == "validate":
        index_document_text(db, dt)
    else:  # reject
        remove_document_text(db, document_id)
    db.commit()

    return dt

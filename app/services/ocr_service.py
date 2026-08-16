"""
CIRCE Intel Desk — Serviço de OCR (RF-011)
Sprint 04 — Sub-passo 04-2

Engine híbrida (D-04-0-01, D-04-0-02):
  PDFs   → PyMuPDF (página → imagem, DPI=200) + pytesseract (Tesseract, lang=por)
  Imagens → EasyOCR (rede neural, melhor em material degradado)

Formatos suportados:
  PDF:    "pdf"
  Imagem: "jpg", "jpeg", "png", "tiff", "tif", "bmp", "webp"

Fluxo run_ocr():
  1. Valida Document e arquivo em disco
  2. Cria/reinicia DocumentText com ocr_status="processing"  (commit 1 — sem audit)
  3. Extrai texto pelo engine adequado (fora de transação — pode demorar)
  4. Salva raw_text, engine, ocr_status="done"               (commit 2 + audit)
  5. Em erro: ocr_status="failed"                            (commit 2 + audit)

Fluxo validate_ocr():
  action="validate": seta validation_status="validated", validated_text  → audit
  action="reject":   seta validation_status="rejected",  rejection_reason → audit
  CA-011.7: toda decisão do operador é logada.

Invariante: stored_path (arquivo original) é APENAS lido, NUNCA alterado (CA-011.5).

Padrão de transação: contrato D47 idêntico aos demais services
  (BEGIN IMMEDIATE → flush → audit_service.log_action(manage_transaction=False) → commit;
   rollback em qualquer exceção).

EasyOCR: reader inicializado com lazy-loading (singleton) para evitar carregar
~600 MB de modelo a cada import do módulo.
"""
from __future__ import annotations

import io
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_text import DocumentText
from app.services import audit_service

# ---------------------------------------------------------------------------
# Configuração de caminhos e formatos
# ---------------------------------------------------------------------------

# Fallback de PATH para Tesseract no Windows (D-04-0-02)
_TESSERACT_EXE = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

_PDF_FORMATS = {"pdf"}
_IMAGE_FORMATS = {"jpg", "jpeg", "png", "tiff", "tif", "bmp", "webp"}
_SUPPORTED_FORMATS = _PDF_FORMATS | _IMAGE_FORMATS

_ENTITY = "document_text"

# ---------------------------------------------------------------------------
# EasyOCR — singleton com inicialização lazy
# ---------------------------------------------------------------------------

_easyocr_reader = None


def _get_easyocr_reader():
    """
    Retorna o Reader EasyOCR, carregando os modelos (~600 MB) apenas na
    primeira chamada. Após isso reutiliza a instância em memória.
    """
    global _easyocr_reader
    if _easyocr_reader is None:
        import easyocr  # import lazy — não bloqueia na inicialização do módulo
        _easyocr_reader = easyocr.Reader(["pt"], verbose=False)
    return _easyocr_reader


# ---------------------------------------------------------------------------
# Exceções de domínio
# ---------------------------------------------------------------------------


class DocumentNotFoundError(Exception):
    """Documento não encontrado pelo id informado."""


class DocumentTextNotFoundError(Exception):
    """DocumentText não encontrado para o document_id informado."""


class UnsupportedFormatError(Exception):
    """Formato de arquivo não suportado pelo pipeline OCR."""

    def __init__(self, file_format: str):
        self.file_format = file_format
        super().__init__(
            f"Formato {file_format!r} não suportado pelo OCR. "
            f"Formatos aceitos: {sorted(_SUPPORTED_FORMATS)}"
        )


class FileNotOnDiskError(Exception):
    """Arquivo referenciado no banco não existe em disco (stored_path inválido)."""

    def __init__(self, stored_path: str):
        self.stored_path = stored_path
        super().__init__(f"Arquivo não encontrado em disco: {stored_path!r}")


class OCRNotReadyError(Exception):
    """Tentativa de validar OCR que ainda não foi processado (ocr_status ≠ 'done')."""


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    """Timestamp ISO 8601 UTC — mesmo formato usado nos demais services."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _configure_tesseract() -> None:
    """
    Configura o caminho do binário Tesseract explicitamente se o executável
    existir no caminho padrão do Windows e não estiver no PATH do processo.
    Necessário porque o servidor Uvicorn pode herdar um PATH sem Tesseract.
    """
    if os.path.exists(_TESSERACT_EXE):
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = _TESSERACT_EXE


def _extract_pdf(stored_path: str) -> str:
    """
    Converte cada página do PDF em imagem (DPI=200) e extrai texto via Tesseract/por.
    Texto de cada página precedido por marcador [Página N].
    CA-011.5: arquivo aberto somente para leitura, nunca modificado.
    """
    import pytesseract
    from PIL import Image

    try:
        import pymupdf as fitz  # pymupdf >= 1.24 (evita aviso de depreciação)
    except ImportError:
        import fitz  # fallback para versões anteriores

    _configure_tesseract()

    doc = fitz.open(stored_path)
    pages_text: list[str] = []

    for page_num, page in enumerate(doc, start=1):
        pix = page.get_pixmap(dpi=200)
        pil_img = Image.open(io.BytesIO(pix.tobytes("png")))
        page_text = pytesseract.image_to_string(pil_img, lang="por").strip()
        if page_text:
            pages_text.append(f"[Página {page_num}]\n{page_text}")

    doc.close()
    return "\n\n".join(pages_text)


def _extract_image(stored_path: str) -> str:
    """
    Extrai texto de imagem via EasyOCR (modelo neural pt).
    CA-011.5: arquivo lido pelo EasyOCR, nunca modificado.
    """
    reader = _get_easyocr_reader()
    results = reader.readtext(stored_path, detail=0)
    return " ".join(str(r) for r in results).strip()


def _get_or_create_document_text(db: Session, document_id: int) -> DocumentText:
    """
    Retorna DocumentText existente ou cria novo com status pending.
    NÃO commita — responsabilidade do chamador.
    """
    stmt = select(DocumentText).where(DocumentText.document_id == document_id)
    dt = db.execute(stmt).scalars().first()
    if dt is None:
        dt = DocumentText(
            document_id=document_id,
            ocr_status="pending",
            validation_status="pending",
        )
        db.add(dt)
        db.flush()
    return dt


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def run_ocr(
    db: Session,
    *,
    document_id: int,
    operator_id: int,
) -> DocumentText:
    """
    Executa OCR sobre o documento especificado.

    Commit 1 (sem audit): ocr_status = "processing".
    Extração (fora de transação): pode levar até ~60s para 20 páginas (CA-011.3).
    Commit 2 (com audit): ocr_status = "done" | "failed".

    Se o DocumentText já existir (re-run), todos os campos são resetados.

    Levanta:
      DocumentNotFoundError   — document_id inválido
      UnsupportedFormatError  — formato não suportado pelo OCR
      FileNotOnDiskError      — stored_path não encontrado em disco
    """
    # --- Pré-validação ---
    doc = db.get(Document, document_id)
    if doc is None:
        raise DocumentNotFoundError(document_id)

    fmt = (doc.file_format or "").lower().lstrip(".")
    if fmt not in _SUPPORTED_FORMATS:
        raise UnsupportedFormatError(fmt)

    if not Path(doc.stored_path).exists():
        raise FileNotOnDiskError(doc.stored_path)

    # --- Commit 1: marcar como "processing" ---
    db.execute(text("BEGIN IMMEDIATE"))
    try:
        dt = _get_or_create_document_text(db, document_id)
        # Reinicia todos os campos (permite re-run)
        dt.ocr_status = "processing"
        dt.validation_status = "pending"
        dt.raw_text = None
        dt.validated_text = None
        dt.engine = None
        dt.validated_by = None
        dt.validated_at = None
        dt.rejection_reason = None
        db.commit()
        dt_id = dt.id  # salva antes de refresh
    except Exception:
        db.rollback()
        raise

    # --- Extração (fora de transação — pode demorar) ---
    raw_text: Optional[str] = None
    engine: Optional[str] = None
    ocr_error: Optional[str] = None

    try:
        if fmt in _PDF_FORMATS:
            raw_text = _extract_pdf(doc.stored_path)
            engine = "tesseract"
        else:
            raw_text = _extract_image(doc.stored_path)
            engine = "easyocr"
    except Exception as exc:
        ocr_error = str(exc)

    # --- Commit 2: salvar resultado + audit ---
    db.execute(text("BEGIN IMMEDIATE"))
    try:
        dt = db.get(DocumentText, dt_id)

        if ocr_error is None:
            dt.ocr_status = "done"
            dt.raw_text = raw_text
            dt.engine = engine
            db.flush()
            audit_service.log_action(
                db,
                action="document_text_create",
                user_id=operator_id,
                entity_type=_ENTITY,
                entity_id=dt.id,
                description=(
                    f"OCR concluído — documento {document_id} "
                    f"({doc.original_filename!r}) via {engine}"
                ),
                metadata={
                    "document_id": document_id,
                    "engine": engine,
                    "chars": len(raw_text) if raw_text else 0,
                },
                manage_transaction=False,
            )
        else:
            dt.ocr_status = "failed"
            db.flush()
            audit_service.log_action(
                db,
                action="document_text_fail",
                user_id=operator_id,
                entity_type=_ENTITY,
                entity_id=dt.id,
                description=(
                    f"OCR falhou — documento {document_id} "
                    f"({doc.original_filename!r}): {ocr_error[:200]}"
                ),
                metadata={
                    "document_id": document_id,
                    "error": ocr_error[:500],
                },
                manage_transaction=False,
            )

        db.commit()
        db.refresh(dt)
        return dt

    except Exception:
        db.rollback()
        raise


def validate_ocr(
    db: Session,
    *,
    document_id: int,
    action: str,
    validated_text: Optional[str] = None,
    rejection_reason: Optional[str] = None,
    operator_id: int,
) -> DocumentText:
    """
    Valida ou rejeita o texto OCR extraído (CA-011.7).

    action="validate":
      - validated_text obrigatório
      - validation_status → "validated"
      - Indexação FTS5 é feita pelo chamador (API — sub-passo 04-4)

    action="reject":
      - rejection_reason obrigatório
      - validation_status → "rejected"
      - Texto NÃO é indexado no FTS5

    Toda decisão do operador é logada (CA-011.7).

    Levanta:
      DocumentTextNotFoundError — nenhum OCR processado para document_id
      OCRNotReadyError          — ocr_status ≠ "done"
      ValueError                — action inválida ou campos obrigatórios faltando
    """
    if action not in ("validate", "reject"):
        raise ValueError(f"action deve ser 'validate' ou 'reject', não {action!r}.")

    if action == "validate" and not validated_text:
        raise ValueError("validated_text é obrigatório quando action='validate'.")

    if action == "reject" and not rejection_reason:
        raise ValueError("rejection_reason é obrigatório quando action='reject'.")

    stmt = select(DocumentText).where(DocumentText.document_id == document_id)
    dt = db.execute(stmt).scalars().first()
    if dt is None:
        raise DocumentTextNotFoundError(document_id)

    if dt.ocr_status != "done":
        raise OCRNotReadyError(
            f"OCR do documento {document_id} não está pronto "
            f"(ocr_status={dt.ocr_status!r}). Execute o OCR primeiro."
        )

    db.execute(text("BEGIN IMMEDIATE"))
    try:
        now_dt = _utcnow()

        if action == "validate":
            dt.validation_status = "validated"
            dt.validated_text = validated_text
            dt.validated_by = operator_id
            dt.validated_at = now_dt
            dt.rejection_reason = None
            db.flush()
            audit_service.log_action(
                db,
                action="document_text_validate",
                user_id=operator_id,
                entity_type=_ENTITY,
                entity_id=dt.id,
                description=f"Texto OCR validado — documento {document_id}",
                metadata={
                    "document_id": document_id,
                    "chars": len(validated_text),
                },
                manage_transaction=False,
            )
        else:  # reject
            dt.validation_status = "rejected"
            dt.validated_by = operator_id
            dt.validated_at = now_dt
            dt.rejection_reason = rejection_reason
            db.flush()
            audit_service.log_action(
                db,
                action="document_text_reject",
                user_id=operator_id,
                entity_type=_ENTITY,
                entity_id=dt.id,
                description=(
                    f"Texto OCR rejeitado — documento {document_id}: "
                    f"{rejection_reason[:100]}"
                ),
                metadata={
                    "document_id": document_id,
                    "reason": rejection_reason,
                },
                manage_transaction=False,
            )

        db.commit()
        db.refresh(dt)
        return dt

    except (DocumentTextNotFoundError, OCRNotReadyError, ValueError):
        raise
    except Exception:
        db.rollback()
        raise


def get_document_text(db: Session, document_id: int) -> Optional[DocumentText]:
    """Retorna DocumentText pelo document_id, ou None. Leitura pura."""
    stmt = select(DocumentText).where(DocumentText.document_id == document_id)
    return db.execute(stmt).scalars().first()


def reset_ocr(
    db: Session,
    *,
    document_id: int,
    operator_id: int,
) -> DocumentText:
    """
    Reseta DocumentText para ocr_status='pending', permitindo re-executar OCR.
    Útil quando o operador quer tentar novamente após falha.
    """
    stmt = select(DocumentText).where(DocumentText.document_id == document_id)
    dt = db.execute(stmt).scalars().first()
    if dt is None:
        raise DocumentTextNotFoundError(document_id)

    db.execute(text("BEGIN IMMEDIATE"))
    try:
        dt.ocr_status = "pending"
        dt.validation_status = "pending"
        dt.raw_text = None
        dt.validated_text = None
        dt.engine = None
        dt.validated_by = None
        dt.validated_at = None
        dt.rejection_reason = None
        db.flush()
        audit_service.log_action(
            db,
            action="document_text_reset",
            user_id=operator_id,
            entity_type=_ENTITY,
            entity_id=dt.id,
            description=f"OCR resetado — documento {document_id}",
            manage_transaction=False,
        )
        db.commit()
        db.refresh(dt)
        return dt
    except Exception:
        db.rollback()
        raise

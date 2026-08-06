"""
CIRCE Intel Desk - Serviço Platea (AT-03).

Responsabilidades:
  - toggle_platea_exclude: marca/desmarca item individual como [NAO COMPARTILHAR].
  - build_sync_payload: monta payload do caso para envio ao Athena,
    excluindo itens com platea_exclude=True (CA-AT03.2).
    Corrigido em AT-03.8: nomes de campos alinhados ao SyncCasePayload do Athena.
  - push_to_athena: envia payload ao Athena via POST /api/sync/case (AT-03.8).
    Atualiza platea_status e registra no audit log conforme resultado.

Tipos de item suportados: "person_link" (CasePersonLink), "document" (Document).

Contrato de push (AT-03.8):
  - Sucesso (HTTP 200/201)      → platea_status = "shared"
  - Athena inacessível (conn.)  → platea_status = "pending_sync"
  - Resposta HTTP 4xx/5xx       → platea_status = "error"
  Timeout httpx: 10 segundos.
  O push é síncrono no MVP-0. Fila de retry é AT-03b (sprint separada).

AT-03.7 / AT-03.8.
"""
from __future__ import annotations

import logging
from typing import Literal, Optional

import httpx
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.case import Case
from app.models.case_person_link import CasePersonLink
from app.models.document import Document
from app.models.person import Person
from app.services.audit_service import log_action

logger = logging.getLogger(__name__)

ItemType = Literal["person_link", "document"]

# Endpoint de sincronização no Athena (AT-03.5).
_SYNC_ENDPOINT = "/api/sync/case"

# Timeout para chamadas ao Athena (segundos).
_ATHENA_TIMEOUT = 10.0


# ------------------------------------------------------------------
# toggle_platea_exclude
# ------------------------------------------------------------------

def toggle_platea_exclude(
    db: Session,
    *,
    item_type: ItemType,
    item_id: int,
    exclude: bool,
    user_id: Optional[int] = None,
) -> dict:
    """
    Marca ou desmarca um item como [NAO COMPARTILHAR] na Platea.

    Retorna dict com:
      - item_type: str
      - item_id: int
      - platea_exclude: bool (valor após a operação)
      - changed: bool (False se já estava no estado solicitado)
    """
    if item_type == "person_link":
        obj = db.get(CasePersonLink, item_id)
        if obj is None:
            raise ValueError(f"Vínculo {item_id} não encontrado.")
        entity_type = "case_person_link"
    elif item_type == "document":
        obj = db.get(Document, item_id)
        if obj is None:
            raise ValueError(f"Documento {item_id} não encontrado.")
        entity_type = "document"
    else:
        raise ValueError(f"item_type inválido: {item_type!r}")

    if obj.platea_exclude == exclude:
        return {
            "item_type": item_type,
            "item_id": item_id,
            "platea_exclude": exclude,
            "changed": False,
        }

    obj.platea_exclude = exclude
    db.flush()

    action_label = "platea_exclude_set" if exclude else "platea_exclude_cleared"
    description = (
        f"{entity_type} {item_id} marcado como [NAO COMPARTILHAR] na Platea."
        if exclude
        else f"{entity_type} {item_id} removido de [NAO COMPARTILHAR] na Platea."
    )

    log_action(
        db,
        action=action_label,
        entity_type=entity_type,
        entity_id=item_id,
        description=description,
        metadata={"platea_exclude": exclude},
        user_id=user_id,
        manage_transaction=False,
    )
    db.commit()

    return {
        "item_type": item_type,
        "item_id": item_id,
        "platea_exclude": exclude,
        "changed": True,
    }


# ------------------------------------------------------------------
# build_sync_payload
# ------------------------------------------------------------------

def build_sync_payload(
    db: Session,
    case_id: int,
    published_by: str,
) -> Optional[dict]:
    """
    Monta payload do caso para envio ao Athena.

    Campos alinhados ao SyncCasePayload do Athena (AT-03.8 — corrige AT-03.7):
      case_ref      ← case.case_code
      title         ← case.name
      status        ← case.status
      notes         ← case.summary
      published_by  ← username do operador (obrigatório no Athena)

    Exclui itens com platea_exclude=True (CA-AT03.2).
    Retorna None se o caso não existir ou não estiver com platea_status=shared.
    """
    case = db.get(Case, case_id)
    if case is None or case.platea_status != "shared":
        return None

    # Vínculos pessoa-caso ativos e não excluídos da Platea.
    links_stmt = (
        select(CasePersonLink)
        .where(
            CasePersonLink.case_id == case_id,
            CasePersonLink.active == 1,
            CasePersonLink.platea_exclude == False,  # noqa: E712
        )
    )
    links = list(db.execute(links_stmt).scalars().all())

    # Nomes das pessoas vinculadas.
    person_ids = [lk.person_id for lk in links]
    persons_map: dict[int, Person] = {}
    if person_ids:
        rows = db.execute(
            select(Person).where(Person.id.in_(person_ids))
        ).scalars().all()
        for p in rows:
            persons_map[p.id] = p

    # Documentos não excluídos da Platea.
    docs_stmt = (
        select(Document)
        .where(
            Document.case_id == case_id,
            Document.platea_exclude == False,  # noqa: E712
        )
    )
    docs = list(db.execute(docs_stmt).scalars().all())

    # Payload no formato exato do SyncCasePayload do Athena.
    payload = {
        "case_ref":       case.case_code,
        "title":          case.name,
        "status":         case.status,
        "classification": None,
        "notes":          getattr(case, "summary", None) or getattr(case, "notes", None),
        "source_unit":    getattr(case, "unit", None),
        "published_by":   published_by,
        "persons": [
            {
                "person_ref":        str(lk.person_id),
                "full_name":         persons_map[lk.person_id].full_name if lk.person_id in persons_map else "",
                "aliases":           None,
                "cpf":               persons_map[lk.person_id].cpf if lk.person_id in persons_map else None,
                "rg":                None,
                "birth_date":        None,
                "notes":             None,
                "reliability_level": lk.reliability_level,
                "role_in_case":      lk.role_in_case,
            }
            for lk in links
        ],
        "documents": [
            {
                "document_ref": str(doc.id),
                "filename":     doc.original_filename,
                "file_type":    doc.file_format,
                "sha256":       doc.sha256_hash,
                "description":  doc.title,
                "imported_at":  None,
            }
            for doc in docs
        ],
        "links": [],
    }

    return payload


# ------------------------------------------------------------------
# push_to_athena
# ------------------------------------------------------------------

def push_to_athena(
    db: Session,
    case_id: int,
    published_by: str,
    user_id: Optional[int] = None,
) -> str:
    """
    Envia o payload do caso ao Athena via POST /api/sync/case (AT-03.8).

    Fluxo:
      1. Monta payload via build_sync_payload.
      2. Envia ao Athena com httpx (timeout 10s).
      3. Interpreta resposta → novo platea_status.
      4. Persiste platea_status no banco (transação própria, ADR-003a).
      5. Registra no audit log.

    Retorna o platea_status resultante: "shared", "pending_sync" ou "error".

    Não lança exceção para falhas de rede ou HTTP — absorve e registra.
    Lança ValueError se o caso não existir ou não estiver como shared.
    """
    case = db.get(Case, case_id)
    if case is None:
        raise ValueError(f"Caso {case_id} não encontrado.")

    payload = build_sync_payload(db, case_id, published_by)
    if payload is None:
        raise ValueError(
            f"Caso {case_id} não está com platea_status=shared ou não existe."
        )

    athena_url = f"{settings.ATHENA_URL.rstrip('/')}{_SYNC_ENDPOINT}"
    new_status: str
    audit_action: str
    audit_description: str

    try:
        response = httpx.post(
            athena_url,
            json=payload,
            timeout=_ATHENA_TIMEOUT,
        )
        if response.status_code in (200, 201):
            data = response.json()
            version = data.get("published_version", "?")
            new_status = "shared"
            audit_action = "PLATEA_CASE_PUSHED"
            audit_description = (
                f"Caso {case.case_code} publicado na Platea com sucesso "
                f"(versão {version}, Athena: {athena_url})."
            )
            logger.info(audit_description)
        else:
            new_status = "error"
            audit_action = "PLATEA_PUSH_FAILED"
            audit_description = (
                f"Caso {case.case_code}: push à Platea falhou — "
                f"Athena retornou HTTP {response.status_code}."
            )
            logger.warning(audit_description)

    except httpx.TimeoutException:
        new_status = "pending_sync"
        audit_action = "PLATEA_PUSH_FAILED"
        audit_description = (
            f"Caso {case.case_code}: push à Platea falhou — "
            f"timeout ao contactar Athena ({athena_url})."
        )
        logger.warning(audit_description)

    except httpx.ConnectError:
        new_status = "pending_sync"
        audit_action = "PLATEA_PUSH_FAILED"
        audit_description = (
            f"Caso {case.case_code}: push à Platea falhou — "
            f"Athena inacessível ({athena_url})."
        )
        logger.warning(audit_description)

    except Exception as exc:  # pragma: no cover — rede imprevisível
        new_status = "error"
        audit_action = "PLATEA_PUSH_FAILED"
        audit_description = (
            f"Caso {case.case_code}: push à Platea falhou — "
            f"erro inesperado: {type(exc).__name__}: {exc}."
        )
        logger.error(audit_description, exc_info=True)

    # Persiste o novo platea_status e registra no audit log.
    db.execute(text("BEGIN IMMEDIATE"))
    try:
        case.platea_status = new_status
        db.flush()

        log_action(
            db,
            action=audit_action,
            entity_type="case",
            entity_id=case_id,
            description=audit_description,
            metadata={"platea_status": new_status, "athena_url": athena_url},
            user_id=user_id,
            manage_transaction=False,
        )

        db.commit()
    except Exception:
        db.rollback()
        raise

    return new_status

"""
CIRCE Intel Desk - Servico Platea (AT-03).

Responsabilidades:
  - toggle_platea_exclude: marca/desmarca item individual como [NAO COMPARTILHAR].
  - build_sync_payload: monta payload do caso para envio ao Athena,
    excluindo itens com platea_exclude=True (CA-AT03.2).

Tipos de item suportados: "person_link" (CasePersonLink), "document" (Document).

AT-03.7.
"""
from __future__ import annotations

from typing import Literal, Optional

from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.case_person_link import CasePersonLink
from app.models.document import Document
from app.models.person import Person
from app.services.audit_service import log_action

ItemType = Literal["person_link", "document"]


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
      - platea_exclude: bool (valor apos a operacao)
      - changed: bool (False se ja estava no estado solicitado)
    """
    if item_type == "person_link":
        obj = db.get(CasePersonLink, item_id)
        if obj is None:
            raise ValueError(f"Vinculo {item_id} nao encontrado.")
        entity_type = "case_person_link"
    elif item_type == "document":
        obj = db.get(Document, item_id)
        if obj is None:
            raise ValueError(f"Documento {item_id} nao encontrado.")
        entity_type = "document"
    else:
        raise ValueError(f"item_type invalido: {item_type!r}")

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


def build_sync_payload(db: Session, case_id: int) -> Optional[dict]:
    """
    Monta payload do caso para envio ao Athena.

    Exclui automaticamente itens com platea_exclude=True (CA-AT03.2).
    Retorna None se o caso nao existir ou nao estiver com platea_status=shared.
    """
    from sqlalchemy import select

    case = db.get(Case, case_id)
    if case is None or case.platea_status != "shared":
        return None

    links_stmt = (
        select(CasePersonLink)
        .where(
            CasePersonLink.case_id == case_id,
            CasePersonLink.active == 1,
            CasePersonLink.platea_exclude == False,
        )
    )
    links = list(db.execute(links_stmt).scalars().all())

    person_ids = [lk.person_id for lk in links]
    persons_map: dict[int, str] = {}
    if person_ids:
        rows = db.execute(
            select(Person.id, Person.full_name).where(Person.id.in_(person_ids))
        ).fetchall()
        for pid, pname in rows:
            persons_map[pid] = pname

    docs_stmt = (
        select(Document)
        .where(
            Document.case_id == case_id,
            Document.platea_exclude == False,
        )
    )
    docs = list(db.execute(docs_stmt).scalars().all())

    payload = {
        "case_id": case.id,
        "case_code": case.case_code,
        "name": case.name,
        "status": case.status,
        "summary": case.summary,
        "fact_date": case.fact_date,
        "tags": case.tags,
        "platea_status": case.platea_status,
        "persons": [
            {
                "link_id": lk.id,
                "person_id": lk.person_id,
                "person_name": persons_map.get(lk.person_id, ""),
                "role_in_case": lk.role_in_case,
                "reliability_level": lk.reliability_level,
            }
            for lk in links
        ],
        "documents": [
            {
                "document_id": doc.id,
                "original_filename": doc.original_filename,
                "file_format": doc.file_format,
                "file_size": doc.file_size,
                "sha256_hash": doc.sha256_hash,
                "title": doc.title,
            }
            for doc in docs
        ],
    }

    return payload
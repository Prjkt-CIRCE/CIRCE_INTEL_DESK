"""
CIRCE Intel Desk — Servico de Boletins de Ocorrencia (RF-009).
Operacoes: create, update, archive, get, list, link_person, unlink_person,
list_persons_by_report.
Transacao e auditoria (ADR-003 §2.4 + ADR-003a) — mesmo contrato D47:
    1. db.execute(text("BEGIN IMMEDIATE"))     -> lock de escrita
    2. db.add(entidade); db.flush()            -> materializa entity_id
    3. audit_service.log_action(..., manage_transaction=False)
    4. db.commit()                             -> commit unico; falha -> rollback
Strings de action (ADR-003 §3.2):
  "incident_report_create", "incident_report_update", "incident_report_archive",
  "incident_report_person_link_create", "incident_report_person_link_remove".
Sprint 03 — Sub-passo 03-2.
Correcoes Sprint 04-6:
  - criminal_type (schema) mapeado para criminal_classification (modelo).
  - notes (schema) ignorado: coluna nao existe no modelo IncidentReport.
  - update usa _SCHEMA_TO_MODEL para renomear campos antes de setattr.
  - _now() retorna datetime (nao string): created_at/updated_at sao DateTime.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.incident_report import IncidentReport
from app.models.incident_report_person_link import IncidentReportPersonLink
from app.schemas.incident_report import IncidentReportCreate, IncidentReportUpdate
from app.services import audit_service

_ENTITY_TYPE = "incident_report"
_LINK_ENTITY_TYPE = "incident_report_person_link"

# Papeis validos para role_in_report (CA-009.3)
ROLES_VALIDOS = {"vitima", "autor", "comunicante", "testemunha", "outro"}

# ---------------------------------------------------------------------------
# Mapeamento schema → modelo (campos com nomes distintos)
# ---------------------------------------------------------------------------

# Campos do schema Pydantic cujo nome difere do atributo no modelo SQLAlchemy.
_SCHEMA_TO_MODEL: dict[str, str] = {
    "criminal_type": "criminal_classification",
}

# Campos do schema que nao existem no modelo — silenciosamente ignorados.
# Pendente: adicionar coluna 'notes' ao modelo + migracao futura.
_SCHEMA_IGNORED: frozenset[str] = frozenset({"notes"})


def _apply_changes(report: IncidentReport, changes: dict) -> list[str]:
    """
    Aplica changes (model_dump) ao IncidentReport, respeitando o mapeamento
    de nomes e ignorando campos sem coluna no modelo.
    Retorna lista de campos do modelo que realmente mudaram.
    """
    changed_fields: list[str] = []
    for field, value in changes.items():
        if field in _SCHEMA_IGNORED:
            continue
        model_field = _SCHEMA_TO_MODEL.get(field, field)
        if getattr(report, model_field, None) != value:
            setattr(report, model_field, value)
            changed_fields.append(model_field)
    return changed_fields


# ---------------------------------------------------------------------------
# Excecoes de dominio
# ---------------------------------------------------------------------------

class IncidentReportNotFoundError(Exception):
    """BO nao encontrado pelo id informado."""


class DuplicateIRPersonLinkError(Exception):
    """Ja existe vinculo ativo com o mesmo BO, pessoa e papel."""

    def __init__(
        self,
        incident_report_id: int,
        person_id: int,
        role_in_report: str,
        existing_link_id: int,
    ):
        self.incident_report_id = incident_report_id
        self.person_id = person_id
        self.role_in_report = role_in_report
        self.existing_link_id = existing_link_id
        super().__init__(
            f"Vinculo BO {incident_report_id} + pessoa {person_id} + "
            f"papel {role_in_report!r} ja existe (id={existing_link_id})."
        )


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _now() -> datetime:
    """Retorna datetime UTC atual — compativel com colunas DateTime do modelo."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# CRUD de IncidentReport
# ---------------------------------------------------------------------------

def create_incident_report(
    db: Session,
    data: IncidentReportCreate,
    user_id: int,
) -> IncidentReport:
    """Cria um BO e registra auditoria na mesma transacao (CA-009.1, CA-009.2)."""
    db.execute(text("BEGIN IMMEDIATE"))
    try:
        now = _now()
        report = IncidentReport(
            bo_number=data.bo_number,
            bo_date=data.bo_date,
            issuing_unit=data.issuing_unit,
            summary=data.summary,
            # schema usa "criminal_type"; modelo usa "criminal_classification"
            criminal_classification=data.criminal_type,
            procedural_status=data.procedural_status,
            # "notes" ignorado: coluna nao existe no modelo (pendente sprint futura)
            case_id=data.case_id,
            document_id=data.document_id,
            status="active",
            created_at=now,
            created_by=user_id,
        )
        db.add(report)
        db.flush()
        audit_service.log_action(
            db,
            action="incident_report_create",
            user_id=user_id,
            entity_type=_ENTITY_TYPE,
            entity_id=report.id,
            description=f"BO {report.bo_number!r} cadastrado"
            + (f" — caso {report.case_id}" if report.case_id else ""),
            manage_transaction=False,
        )
        db.commit()
        db.refresh(report)
        return report
    except Exception:
        db.rollback()
        raise


def update_incident_report(
    db: Session,
    report_id: int,
    data: IncidentReportUpdate,
    user_id: int,
) -> IncidentReport:
    """Edita campos de um BO. Nao loga se nada mudou."""
    report = db.get(IncidentReport, report_id)
    if report is None:
        raise IncidentReportNotFoundError(report_id)

    changes = data.model_dump(exclude_unset=True)
    if not changes:
        return report

    db.execute(text("BEGIN IMMEDIATE"))
    try:
        changed_fields = _apply_changes(report, changes)

        if not changed_fields:
            db.rollback()
            return report

        report.updated_at = _now()
        report.updated_by = user_id
        db.flush()
        audit_service.log_action(
            db,
            action="incident_report_update",
            user_id=user_id,
            entity_type=_ENTITY_TYPE,
            entity_id=report.id,
            description=f"BO {report.bo_number!r} atualizado",
            metadata={"changed_fields": sorted(changed_fields)},
            manage_transaction=False,
        )
        db.commit()
        db.refresh(report)
        return report
    except Exception:
        db.rollback()
        raise


def archive_incident_report(
    db: Session,
    report_id: int,
    user_id: int,
) -> IncidentReport:
    """Arquivamento logico. Idempotente — nao loga se ja arquivado."""
    report = db.get(IncidentReport, report_id)
    if report is None:
        raise IncidentReportNotFoundError(report_id)

    if report.status == "archived":
        return report

    db.execute(text("BEGIN IMMEDIATE"))
    try:
        report.status = "archived"
        report.updated_at = _now()
        report.updated_by = user_id
        db.flush()
        audit_service.log_action(
            db,
            action="incident_report_archive",
            user_id=user_id,
            entity_type=_ENTITY_TYPE,
            entity_id=report.id,
            description=f"BO {report.bo_number!r} arquivado",
            manage_transaction=False,
        )
        db.commit()
        db.refresh(report)
        return report
    except Exception:
        db.rollback()
        raise


def get_incident_report(db: Session, report_id: int) -> Optional[IncidentReport]:
    """Retorna BO por id ou None. Leitura pura."""
    return db.get(IncidentReport, report_id)


def list_incident_reports(
    db: Session,
    *,
    case_id: Optional[int] = None,
    include_archived: bool = False,
) -> list[IncidentReport]:
    """Lista BOs com filtro opcional por caso e status. Leitura pura."""
    stmt = select(IncidentReport)
    if not include_archived:
        stmt = stmt.where(IncidentReport.status != "archived")
    if case_id is not None:
        stmt = stmt.where(IncidentReport.case_id == case_id)
    stmt = stmt.order_by(IncidentReport.created_at.desc())
    return list(db.execute(stmt).scalars().all())


# ---------------------------------------------------------------------------
# Vinculos BO ↔ Pessoa (CA-009.3)
# ---------------------------------------------------------------------------

def link_person(
    db: Session,
    *,
    incident_report_id: int,
    person_id: int,
    role_in_report: str,
    notes: Optional[str] = None,
    user_id: int,
) -> IncidentReportPersonLink:
    """Vincula pessoa a BO com papel declarado (CA-009.3).
    Papel deve ser um dos valores de ROLES_VALIDOS.
    Vinculo duplicado (mesmo BO + pessoa + papel, active=1) levanta
    DuplicateIRPersonLinkError.
    Vinculo previamente removido (active=0) e reativado silenciosamente
    (mesmo espirito de D-B10-05).
    """
    if role_in_report not in ROLES_VALIDOS:
        raise ValueError(
            f"role_in_report {role_in_report!r} invalido. "
            f"Valores aceitos: {sorted(ROLES_VALIDOS)}"
        )

    db.execute(text("BEGIN IMMEDIATE"))
    try:
        # Verificar existencia do BO
        report = db.get(IncidentReport, incident_report_id)
        if report is None:
            db.rollback()
            raise IncidentReportNotFoundError(incident_report_id)

        # Verificar duplicata ativa
        stmt_ativo = select(IncidentReportPersonLink).where(
            IncidentReportPersonLink.incident_report_id == incident_report_id,
            IncidentReportPersonLink.person_id == person_id,
            IncidentReportPersonLink.role_in_report == role_in_report,
            IncidentReportPersonLink.active == 1,
        )
        existente_ativo = db.execute(stmt_ativo).scalars().first()
        if existente_ativo is not None:
            db.rollback()
            raise DuplicateIRPersonLinkError(
                incident_report_id, person_id, role_in_report, existente_ativo.id
            )

        # Verificar vinculo removido para reativacao (D-B10-05)
        stmt_removido = select(IncidentReportPersonLink).where(
            IncidentReportPersonLink.incident_report_id == incident_report_id,
            IncidentReportPersonLink.person_id == person_id,
            IncidentReportPersonLink.role_in_report == role_in_report,
            IncidentReportPersonLink.active == 0,
        )
        removido = db.execute(stmt_removido).scalars().first()
        now = _now()
        if removido is not None:
            removido.active = 1
            removido.notes = notes
            removido.created_at = now
            removido.created_by = user_id
            db.flush()
            audit_service.log_action(
                db,
                action="incident_report_person_link_create",
                user_id=user_id,
                entity_type=_LINK_ENTITY_TYPE,
                entity_id=removido.id,
                description=(
                    f"Vinculo BO {incident_report_id} + pessoa {person_id} "
                    f"reativado com papel {role_in_report!r}"
                ),
                metadata={"reactivated": True},
                manage_transaction=False,
            )
            db.commit()
            db.refresh(removido)
            return removido

        # Novo vinculo
        link = IncidentReportPersonLink(
            incident_report_id=incident_report_id,
            person_id=person_id,
            role_in_report=role_in_report,
            notes=notes,
            active=1,
            created_at=now,
            created_by=user_id,
        )
        db.add(link)
        db.flush()
        audit_service.log_action(
            db,
            action="incident_report_person_link_create",
            user_id=user_id,
            entity_type=_LINK_ENTITY_TYPE,
            entity_id=link.id,
            description=(
                f"Vinculo BO {incident_report_id} + pessoa {person_id} "
                f"criado com papel {role_in_report!r}"
            ),
            manage_transaction=False,
        )
        db.commit()
        db.refresh(link)
        return link
    except (IncidentReportNotFoundError, DuplicateIRPersonLinkError, ValueError):
        raise
    except Exception:
        db.rollback()
        raise


def unlink_person(
    db: Session,
    *,
    link_id: int,
    user_id: int,
) -> Optional[IncidentReportPersonLink]:
    """Remove vinculo BO↔Pessoa (exclusao logica). Idempotente. Retorna None se nao existir."""
    link = db.get(IncidentReportPersonLink, link_id)
    if link is None:
        return None
    if link.active == 0:
        return link  # ja removido; idempotente

    db.execute(text("BEGIN IMMEDIATE"))
    try:
        link.active = 0
        db.flush()
        audit_service.log_action(
            db,
            action="incident_report_person_link_remove",
            user_id=user_id,
            entity_type=_LINK_ENTITY_TYPE,
            entity_id=link.id,
            description=(
                f"Vinculo BO {link.incident_report_id} + pessoa {link.person_id} "
                f"removido (papel {link.role_in_report!r})"
            ),
            manage_transaction=False,
        )
        db.commit()
        db.refresh(link)
        return link
    except Exception:
        db.rollback()
        raise


def list_persons_by_report(
    db: Session,
    incident_report_id: int,
    *,
    include_removed: bool = False,
) -> list[IncidentReportPersonLink]:
    """Lista vinculos de um BO. Leitura pura."""
    stmt = select(IncidentReportPersonLink).where(
        IncidentReportPersonLink.incident_report_id == incident_report_id
    )
    if not include_removed:
        stmt = stmt.where(IncidentReportPersonLink.active == 1)
    return list(db.execute(stmt).scalars().all())


def list_reports_by_person(
    db: Session,
    person_id: int,
    *,
    include_removed: bool = False,
) -> list[IncidentReportPersonLink]:
    """Lista vinculos de uma pessoa. Leitura pura."""
    stmt = select(IncidentReportPersonLink).where(
        IncidentReportPersonLink.person_id == person_id
    )
    if not include_removed:
        stmt = stmt.where(IncidentReportPersonLink.active == 1)
    return list(db.execute(stmt).scalars().all())

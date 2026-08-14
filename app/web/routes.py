"""
Rotas web (HTML) do CIRCE Intel Desk.

Bloco 11.2: adicionadas rotas GET /settings e POST /settings (D11 + D6).
Bloco 11.4: adicionada rota GET /audit (RF-020).
Sprint 01-B B4: /organizations despromovida de placeholder para tela funcional.
log_action usa manage_transaction=False (D-B11-01).
Sprint 03 - Sub-passo 03-5: rota GET /cases/{case_id}/report (RF-019).
"""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from pathlib import Path

from app.api.auth import _operator_exists
from app.database.session import get_session
from app.services import settings_service

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["web"])


def _shell_context(
    workspace_id: str,
    active_page: str | None,
    page_title: str,
) -> dict:
    return {
        "workspace_id": workspace_id,
        "active_page": active_page,
        "page_title": page_title,
        "inactivity_minutes": settings_service.get_value(
            "inactivity_lock_minutes", 0
        ),
    }


def _render_placeholder(
    request: Request,
    template_name: str,
    active_page: str,
    page_title: str,
    workspace_id: str,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context=_shell_context(workspace_id, active_page, page_title),
    )


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, workspace_id: str = "default") -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="base.html",
        context=_shell_context(workspace_id, None, "CIRCE Intel Desk"),
    )


@router.get("/setup", response_class=HTMLResponse)
async def setup_page(
    request: Request,
    db: Session = Depends(get_session),
):
    if _operator_exists(db):
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="auth/setup.html",
        context={
            "active_page": None,
            "page_title": "CIRCE // Cadastro Inicial",
        },
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    error: str | None = None,
    blocked: str | None = None,
    secs: int | None = None,
    next: str | None = None,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={
            "active_page": None,
            "page_title": "CIRCE // Acesso",
            "show_error": error is not None,
            "show_blocked": blocked is not None,
            "blocked_secs": secs if secs is not None else 0,
            "next_url": next or "/",
        },
    )


@router.get("/lock", response_class=HTMLResponse)
async def lock_page(
    request: Request,
    db: Session = Depends(get_session),
) -> HTMLResponse:
    from urllib.parse import quote
    from app.services.audit_service import log_action

    from_url = request.query_params.get("from", "/")
    reason = request.query_params.get("reason", "manual")
    next_qs = quote(from_url, safe="")

    action = "lock_inactivity" if reason == "auto" else "lock_manual"
    user_id = getattr(request.state, "user_id", None)

    log_action(
        db,
        action=action,
        user_id=user_id,
        description=f"Tela de bloqueio acionada (reason={reason!r}).",
        manage_transaction=False,
    )
    db.commit()

    return templates.TemplateResponse(
        request=request,
        name="auth/lock.html",
        context={
            "active_page": None,
            "page_title": "CIRCE // Bloqueado",
            "from_url": from_url,
            "next_qs": next_qs,
        },
    )


# ---------------------------------------------------------------------------
# Configurações — D11 + D6. Sprint 01 / Bloco 11.2.
# ---------------------------------------------------------------------------
@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    saved: str | None = None,
    error: str | None = None,
    workspace_id: str = "default",
) -> HTMLResponse:
    ctx = _shell_context(workspace_id, "settings", "CIRCE // Configurações")
    ctx["settings"] = settings_service.get_all()
    ctx["saved"] = saved is not None
    ctx["error"] = error
    return templates.TemplateResponse(
        request=request,
        name="settings/settings.html",
        context=ctx,
    )


@router.post("/settings", response_class=HTMLResponse)
async def settings_save(
    request: Request,
    inactivity_lock_minutes: int = Form(...),
    session_hours: int = Form(...),
    bruteforce_max_attempts: int = Form(...),
    bruteforce_window_seconds: int = Form(...),
    bruteforce_block_seconds: int = Form(...),
    workspace_id: str = "default",
) -> HTMLResponse:
    user_id = getattr(request.state, "user_id", None)
    try:
        settings_service.set_value("inactivity_lock_minutes", inactivity_lock_minutes, updated_by=user_id)
        settings_service.set_value("session_hours", session_hours, updated_by=user_id)
        settings_service.set_value("bruteforce_max_attempts", bruteforce_max_attempts, updated_by=user_id)
        settings_service.set_value("bruteforce_window_seconds", bruteforce_window_seconds, updated_by=user_id)
        settings_service.set_value("bruteforce_block_seconds", bruteforce_block_seconds, updated_by=user_id)
        return RedirectResponse(url="/settings?saved=1", status_code=303)
    except Exception as exc:
        return RedirectResponse(url=f"/settings?error={exc}", status_code=303)


# ---------------------------------------------------------------------------
# Casos — RF-001.
# ---------------------------------------------------------------------------
@router.get("/cases", response_class=HTMLResponse)
async def cases_page(
    request: Request, workspace_id: str = "default"
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="cases/list.html",
        context=_shell_context(workspace_id, "cases", "CIRCE // Casos"),
    )


@router.get("/cases/{case_id:int}/report", response_class=HTMLResponse)
async def case_report_page(
    request: Request,
    case_id: int,
    db: Session = Depends(get_session),
) -> HTMLResponse:
    """
    Página de relatório imprimível do caso (RF-019 CA-019.1).
    Coleta dados via API interna e renderiza o template standalone.
    O log de geração é feito pelo endpoint /api/cases/{id}/report-data.
    """
    from datetime import datetime, timezone
    from sqlalchemy import select

    from app.models.case_person_link import CasePersonLink
    from app.models.document import Document
    from app.models.incident_report import IncidentReport
    from app.models.organization import Organization
    from app.models.person import Person
    from app.models.person_org_link import PersonOrgLink
    from app.services import audit_service, case_service

    user_id = getattr(request.state, "user_id", None)

    case = case_service.get_case(db, case_id)
    if case is None:
        return HTMLResponse("<h1>Caso não encontrado.</h1>", status_code=404)

    # Pessoas vinculadas
    links_stmt = select(CasePersonLink).where(
        CasePersonLink.case_id == case_id,
        CasePersonLink.active == 1,
    )
    links = db.execute(links_stmt).scalars().all()
    persons = []
    for lk in links:
        person = db.get(Person, lk.person_id)
        persons.append({
            "person_name": person.full_name if person else f"id:{lk.person_id}",
            "role_in_case": lk.role_in_case,
            "reliability_level": lk.reliability_level,
            "source": lk.source,
        })

    # Organizações vinculadas
    org_ids_seen = set()
    organizations = []
    for lk in links:
        pol_stmt = select(PersonOrgLink).where(
            PersonOrgLink.person_id == lk.person_id,
            PersonOrgLink.active == 1,
        )
        for pol in db.execute(pol_stmt).scalars().all():
            if pol.org_id not in org_ids_seen:
                org_ids_seen.add(pol.org_id)
                org = db.get(Organization, pol.org_id)
                if org:
                    organizations.append({
                        "org_name": org.name,
                        "org_type": org.org_type,
                        "link_type": pol.link_type,
                    })

    # BOs
    ir_stmt = select(IncidentReport).where(
        IncidentReport.case_id == case_id,
        IncidentReport.status != "archived",
    ).order_by(IncidentReport.created_at.desc())
    incident_reports = db.execute(ir_stmt).scalars().all()

    # Documentos
    doc_stmt = select(Document).where(
        Document.case_id == case_id,
    ).order_by(Document.imported_at.desc())
    raw_docs = db.execute(doc_stmt).scalars().all()
    documents = []
    for doc in raw_docs:
        size = doc.file_size or 0
        if size >= 1048576:
            size_fmt = f"{size/1048576:.1f} MB"
        elif size >= 1024:
            size_fmt = f"{size/1024:.0f} KB"
        else:
            size_fmt = f"{size} B"
        doc.file_size_fmt = size_fmt
        doc.imported_at_fmt = str(doc.imported_at)[:16] if doc.imported_at else "—"
        documents.append(doc)

    # Log de geração (CA-019.4)
    audit_service.log_action(
        db,
        action="case_report_generated",
        user_id=user_id,
        entity_type="case",
        entity_id=case_id,
        description=f"Relatorio do caso {case.case_code} gerado.",
        manage_transaction=False,
    )
    db.commit()

    generated_at = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

    return templates.TemplateResponse(
        request=request,
        name="cases/report.html",
        context={
            "case": case,
            "persons": persons,
            "organizations": organizations,
            "incident_reports": incident_reports,
            "documents": documents,
            "generated_at": generated_at,
            "operator_id": user_id,
        },
    )


@router.get("/cases/{case_id:int}", response_class=HTMLResponse)
async def case_detail_page(
    request: Request, case_id: int, workspace_id: str = "default"
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="cases/detail.html",
        context=_shell_context(workspace_id, "cases", "CIRCE // Detalhe do caso"),
    )


# ---------------------------------------------------------------------------
# Pessoas — RF-002.
# ---------------------------------------------------------------------------
@router.get("/persons", response_class=HTMLResponse)
async def persons_page(
    request: Request, workspace_id: str = "default"
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="persons/list.html",
        context=_shell_context(workspace_id, "persons", "CIRCE // Pessoas"),
    )


@router.get("/persons/{person_id:int}", response_class=HTMLResponse)
async def person_detail_page(
    request: Request, person_id: int, workspace_id: str = "default"
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="persons/detail.html",
        context=_shell_context(workspace_id, "persons", "CIRCE // Detalhe da pessoa"),
    )


# ---------------------------------------------------------------------------
# Organizações — RF-004. Sprint 01-B / B4.
# ---------------------------------------------------------------------------
@router.get("/organizations", response_class=HTMLResponse)
async def organizations_page(
    request: Request, workspace_id: str = "default"
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="organizations/list.html",
        context=_shell_context(workspace_id, "organizations", "CIRCE // Organizações"),
    )


@router.get("/organizations/{org_id:int}", response_class=HTMLResponse)
async def organization_detail_page(
    request: Request, org_id: int, workspace_id: str = "default"
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="organizations/detail.html",
        context=_shell_context(workspace_id, "organizations", "CIRCE // Detalhe da organização"),
    )


# ---------------------------------------------------------------------------
# Placeholders.
# ---------------------------------------------------------------------------
@router.get("/documents", response_class=HTMLResponse)
async def documents_page(
    request: Request, workspace_id: str = "default"
) -> HTMLResponse:
    return _render_placeholder(
        request=request,
        template_name="placeholders/documents.html",
        active_page="documents",
        page_title="CIRCE // Documentos",
        workspace_id=workspace_id,
    )


@router.get("/reports", response_class=HTMLResponse)
async def reports_page(
    request: Request, workspace_id: str = "default"
) -> HTMLResponse:
    return _render_placeholder(
        request=request,
        template_name="placeholders/reports.html",
        active_page="reports",
        page_title="CIRCE // Relatórios",
        workspace_id=workspace_id,
    )


# ---------------------------------------------------------------------------
# Auditoria — RF-020. Sprint 01 / Bloco 11.4.
# ---------------------------------------------------------------------------
@router.get("/audit", response_class=HTMLResponse)
async def audit_page(
    request: Request, workspace_id: str = "default"
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="audit/audit.html",
        context=_shell_context(workspace_id, "audit", "CIRCE // Auditoria"),
    )


@router.get("/dev/components", response_class=HTMLResponse)
async def dev_components(
    request: Request, workspace_id: str = "default"
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="dev/components.html",
        context=_shell_context(workspace_id, None, "CIRCE // Showcase"),
    )

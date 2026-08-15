"""
CIRCE Intel Desk - Endpoints REST de Casos (RF-001).

Camada fina de HTTP sobre o case_service. Nenhuma regra de dominio vive
aqui: validacao e dos schemas Pydantic, regra e auditoria sao do servico.

Autenticacao: estas rotas NAO estao na allowlist publica do auth_guard
(app/web/middleware.py), portanto sao protegidas por padrao (RF-021). O
middleware popula request.state.user_id no caminho autenticado (D30); os
endpoints leem dali quem e o operador, sem reconsultar o banco.

Verbos:
  GET    /api/cases                                          -> lista
  POST   /api/cases                                         -> cria
  GET    /api/cases/{id}                                    -> detalhe
  PATCH  /api/cases/{id}                                    -> edita
  DELETE /api/cases/{id}                                    -> arquiva (logico)
  GET    /api/cases/{id}/report-data                        -> dados para relatorio JSON (RF-019)
  GET    /api/cases/{id}/report.pdf                         -> PDF do relatorio (RF-019 CA-019.3)
  PATCH  /api/cases/{id}/items/{item_type}/{item_id}/platea_exclude
                                                            -> toggle [NAO COMPARTILHAR] (AT-03.7)

Sprint 01 - Bloco 8, Sub-passo 8.3.
AT-03.7: endpoint platea_exclude adicionado.
AT-03.8: update_case passa username ao servico para published_by no Athena.
Sprint 03 - Sub-passo 03-5: endpoint report-data (RF-019 CA-019.4).
Sprint 03 - Sub-passo 03-6: endpoint report.pdf via Playwright/Chromium (RF-019 CA-019.3).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.models.case_person_link import CasePersonLink
from app.models.document import Document
from app.models.incident_report import IncidentReport
from app.models.organization import Organization
from app.models.person import Person
from app.models.person_org_link import PersonOrgLink
from app.models.user import User
from app.schemas.cases import CaseCreate, CaseResponse, CaseUpdate
from app.services import audit_service, case_service
from app.services import platea_service

router = APIRouter(prefix="/api/cases", tags=["cases"])

# ---------------------------------------------------------------------------
# Jinja2 — ambiente isolado para renderizacao de templates em PDF.
# Mesmo diretorio usado por routes.py (app/web/templates/).
# Autoescape ativo para .html, igual ao comportamento de Jinja2Templates
# do FastAPI.
# ---------------------------------------------------------------------------
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "web" / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _current_user_id(request: Request) -> int:
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Operador nao autenticado.",
        )
    return user_id


def _get_username(db: Session, user_id: int) -> Optional[str]:
    """Retorna o username do operador logado, ou None se nao encontrado."""
    user = db.get(User, user_id)
    return user.username if user else None


def _render_pdf_bytes(html_content: str) -> bytes:
    """
    Converte uma string HTML em PDF usando Playwright/Chromium.

    Estrategia: executa o Playwright num subprocess Python completamente
    separado, passando o HTML via stdin e recebendo o PDF codificado em
    base64 via stdout.

    Isso evita todos os conflitos de event loop entre Playwright e o
    ProactorEventLoop / SelectorEventLoop do Uvicorn no Windows:
    o subprocess tem seu proprio interpretador e asyncio.run() limpo.

    O HTML deve ser auto-contido (CSS inline, sem assets externos).

    Lanca RuntimeError se o Playwright nao estiver instalado, o Chromium
    nao tiver sido baixado (playwright install chromium), ou o subprocess
    falhar por qualquer outro motivo.
    """
    import base64
    import subprocess
    import sys

    # Script que roda no subprocess separado.
    # Usa aspas simples em todas as strings para nao conflitar com as aspas
    # duplas usadas na f-string que monta o comando (nao usamos f-string aqui,
    # mas mantemos a convencao por clareza).
    _WORKER = (
        "import asyncio, sys, base64\n"
        "from playwright.async_api import async_playwright\n"
        "async def go():\n"
        "    html = sys.stdin.buffer.read().decode('utf-8')\n"
        "    async with async_playwright() as p:\n"
        "        b = await p.chromium.launch()\n"
        "        try:\n"
        "            pg = await b.new_page()\n"
        "            await pg.set_content(html, wait_until='domcontentloaded')\n"
        "            pdf = await pg.pdf(\n"
        "                format='A4',\n"
        "                print_background=True,\n"
        "                margin={\n"
        "                    'top': '20mm', 'bottom': '22mm',\n"
        "                    'left': '20mm', 'right': '15mm',\n"
        "                },\n"
        "            )\n"
        "        finally:\n"
        "            await b.close()\n"
        "    sys.stdout.buffer.write(base64.b64encode(pdf))\n"
        "asyncio.run(go())\n"
    )

    try:
        proc = subprocess.run(
            [sys.executable, "-c", _WORKER],
            input=html_content.encode("utf-8"),
            capture_output=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "Timeout ao gerar PDF: Playwright nao respondeu em 60 s."
        ) from exc

    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"Playwright subprocess encerrou com codigo {proc.returncode}. "
            f"Stderr: {stderr or '(vazio)'}"
        )

    raw = proc.stdout.strip()
    if not raw:
        raise RuntimeError(
            "Playwright subprocess nao produziu saida. "
            "Verifique se o Chromium esta instalado: playwright install chromium"
        )

    return base64.b64decode(raw)


# ---------------------------------------------------------------------------
# Schemas locais
# ---------------------------------------------------------------------------

class PlateaExcludeBody(BaseModel):
    exclude: bool


class PlateaExcludeResponse(BaseModel):
    item_type: str
    item_id: int
    platea_exclude: bool
    changed: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[CaseResponse])
def list_cases(
    request: Request,
    include_archived: bool = False,
    sort_by: Literal["case_code", "name", "created_at", "status"] = "created_at",
    descending: bool = True,
    db: Session = Depends(get_session),
) -> list[CaseResponse]:
    _current_user_id(request)
    cases = case_service.list_cases(
        db,
        include_archived=include_archived,
        sort_by=sort_by,
        descending=descending,
    )
    return cases


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(
    request: Request,
    data: CaseCreate,
    db: Session = Depends(get_session),
) -> CaseResponse:
    user_id = _current_user_id(request)
    case = case_service.create_case(db, data, user_id=user_id)
    return case


@router.get("/{case_id}/report-data")
def get_case_report_data(
    request: Request,
    case_id: int,
    db: Session = Depends(get_session),
) -> dict:
    """
    Coleta todos os dados necessarios para o relatorio de caso (RF-019).
    Registra a geracao no audit log (CA-019.4).
    Retorna dict com caso, pessoas, organizacoes, BOs e documentos.
    """
    user_id = _current_user_id(request)

    case = case_service.get_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Caso {case_id} nao encontrado.")

    # Pessoas vinculadas
    links_stmt = select(CasePersonLink).where(
        CasePersonLink.case_id == case_id,
        CasePersonLink.active == 1,
    )
    links = db.execute(links_stmt).scalars().all()
    persons_data = []
    for lk in links:
        person = db.get(Person, lk.person_id)
        persons_data.append({
            "person_name": person.full_name if person else f"id:{lk.person_id}",
            "role_in_case": lk.role_in_case,
            "reliability_level": lk.reliability_level,
            "source": lk.source,
        })

    # Organizacoes vinculadas via PersonOrgLink (indireto, via pessoas do caso)
    org_ids_seen = set()
    orgs_data = []
    for lk in links:
        pol_stmt = select(PersonOrgLink).where(
            PersonOrgLink.person_id == lk.person_id,
            PersonOrgLink.active == 1,
        )
        pol_rows = db.execute(pol_stmt).scalars().all()
        for pol in pol_rows:
            if pol.org_id not in org_ids_seen:
                org_ids_seen.add(pol.org_id)
                org = db.get(Organization, pol.org_id)
                if org:
                    orgs_data.append({
                        "org_name": org.name,
                        "org_type": org.org_type,
                        "link_type": pol.link_type,
                    })

    # Boletins de Ocorrencia
    ir_stmt = select(IncidentReport).where(
        IncidentReport.case_id == case_id,
        IncidentReport.status != "archived",
    ).order_by(IncidentReport.created_at.desc())
    ir_rows = db.execute(ir_stmt).scalars().all()
    ir_data = []
    for ir in ir_rows:
        ir_data.append({
            "bo_number": ir.bo_number,
            "bo_date": ir.bo_date,
            "issuing_unit": ir.issuing_unit,
            "criminal_type": ir.criminal_type,
            "summary": ir.summary,
        })

    # Documentos
    doc_stmt = select(Document).where(
        Document.case_id == case_id,
    ).order_by(Document.imported_at.desc())
    doc_rows = db.execute(doc_stmt).scalars().all()
    docs_data = []
    for doc in doc_rows:
        size = doc.file_size or 0
        if size >= 1048576:
            size_fmt = f"{size/1048576:.1f} MB"
        elif size >= 1024:
            size_fmt = f"{size/1024:.0f} KB"
        else:
            size_fmt = f"{size} B"
        docs_data.append({
            "original_filename": doc.original_filename,
            "file_format": doc.file_format,
            "file_size_fmt": size_fmt,
            "imported_at_fmt": str(doc.imported_at)[:16] if doc.imported_at else "—",
        })

    # Log de geracao (CA-019.4)
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

    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

    return {
        "case": {
            "id": case.id,
            "case_code": case.case_code,
            "name": case.name,
            "status": case.status,
            "unit": case.unit,
            "responsible": case.responsible,
            "procedure_number": case.procedure_number,
            "fact_date": case.fact_date,
            "tags": case.tags,
            "description": case.description,
            "notes": case.notes,
            "created_at": case.created_at,
            "created_by": case.created_by,
            "updated_at": case.updated_at,
            "updated_by": case.updated_by,
        },
        "persons": persons_data,
        "organizations": orgs_data,
        "incident_reports": ir_data,
        "documents": docs_data,
        "generated_at": now,
        "operator_id": user_id,
    }


@router.get("/{case_id}/report.pdf")
def get_case_report_pdf(
    request: Request,
    case_id: int,
    db: Session = Depends(get_session),
) -> Response:
    """
    Gera e retorna o PDF do relatorio de caso (RF-019 CA-019.3).

    Renderiza o template cases/report.html via Jinja2 e converte para PDF
    usando Playwright/Chromium. O PDF e retornado como download inline.

    Registra a geracao no audit log com action='case_report_pdf_generated',
    distinta de 'case_report_generated' (versao HTML), para rastreabilidade
    do formato utilizado.

    Requer: playwright instalado e playwright install chromium executado.
    """
    user_id = _current_user_id(request)

    case = case_service.get_case(db, case_id)
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Caso {case_id} nao encontrado.",
        )

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

    # Organizacoes vinculadas
    org_ids_seen: set = set()
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

    # Boletins de Ocorrencia
    ir_stmt = select(IncidentReport).where(
        IncidentReport.case_id == case_id,
        IncidentReport.status != "archived",
    ).order_by(IncidentReport.created_at.desc())
    incident_reports = db.execute(ir_stmt).scalars().all()

    # Documentos — atributos de formatacao adicionados dinamicamente,
    # igual ao padrao de case_report_page em routes.py.
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

    # Log de geracao PDF (CA-019.3) — action distinta da versao HTML
    audit_service.log_action(
        db,
        action="case_report_pdf_generated",
        user_id=user_id,
        entity_type="case",
        entity_id=case_id,
        description=f"PDF do relatorio do caso {case.case_code} gerado.",
        manage_transaction=False,
    )
    db.commit()

    generated_at = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

    # Renderizar template para HTML string
    template = _jinja_env.get_template("cases/report.html")
    html_content = template.render(
        case=case,
        persons=persons,
        organizations=organizations,
        incident_reports=incident_reports,
        documents=documents,
        generated_at=generated_at,
        operator_id=user_id,
    )

    # Gerar PDF via Playwright
    try:
        pdf_bytes = _render_pdf_bytes(html_content)
    except Exception as exc:
        import logging
        logging.exception("Falha ao gerar PDF via Playwright")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"[{type(exc).__name__}] {exc}",
        ) from exc

    # Nome do arquivo: CIRCE-CASO-2025-001.pdf (/ substituido por -)
    safe_code = case.case_code.replace("/", "-").replace("\\", "-")
    filename = f"CIRCE-{safe_code}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store, no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(
    request: Request,
    case_id: int,
    db: Session = Depends(get_session),
) -> CaseResponse:
    _current_user_id(request)
    case = case_service.get_case(db, case_id)
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Caso {case_id} nao encontrado.",
        )
    return case


@router.patch("/{case_id}", response_model=CaseResponse)
def update_case(
    request: Request,
    case_id: int,
    data: CaseUpdate,
    db: Session = Depends(get_session),
) -> CaseResponse:
    user_id = _current_user_id(request)
    username = _get_username(db, user_id)
    case = case_service.update_case(
        db, case_id, data, user_id=user_id, username=username
    )
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Caso {case_id} nao encontrado.",
        )
    return case


@router.delete("/{case_id}", response_model=CaseResponse)
def archive_case(
    request: Request,
    case_id: int,
    db: Session = Depends(get_session),
) -> CaseResponse:
    user_id = _current_user_id(request)
    case = case_service.archive_case(db, case_id, user_id=user_id)
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Caso {case_id} nao encontrado.",
        )
    return case


@router.patch(
    "/{case_id}/items/{item_type}/{item_id}/platea_exclude",
    response_model=PlateaExcludeResponse,
)
def set_platea_exclude(
    request: Request,
    case_id: int,
    item_type: Literal["person_link", "document"],
    item_id: int,
    data: PlateaExcludeBody,
    db: Session = Depends(get_session),
) -> PlateaExcludeResponse:
    """
    Marca ou desmarca item individual como [NAO COMPARTILHAR] na Platea (AT-03.7).
    """
    user_id = _current_user_id(request)

    case = case_service.get_case(db, case_id)
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Caso {case_id} nao encontrado.",
        )

    try:
        result = platea_service.toggle_platea_exclude(
            db,
            item_type=item_type,
            item_id=item_id,
            exclude=data.exclude,
            user_id=user_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return PlateaExcludeResponse(**result)

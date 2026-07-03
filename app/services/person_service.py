"""
CIRCE Intel Desk — Serviço de Pessoas (RF-002).

Regras de domínio do cadastro de pessoas:
  - full_name obrigatório (CA-002.1).
  - cpf opcional; normalizado para apenas dígitos antes de persistir
    (CA-002.2). A normalização vive aqui, não no schema — ver docstring
    de app/models/person.py.
  - Antes de salvar, se o cpf normalizado já pertencer a outra pessoa, o
    serviço recusa a operação levantando DuplicateCPFError, carregando o
    id da pessoa existente para a API/UI oferecerem "abrir pessoa
    existente" (CA-002.5, decisão D57 — Sprint 01 Bloco 9).
  - Criação, edição e arquivamento, cada um auditado (CA-002.7).
  - Listagem com filtro de arquivados, no mesmo espírito do RF-001.

Transação e auditoria (ADR-003 §2.4 + ADR-003a) — MESMO contrato do
case_service.py:
  Operações que escrevem estado seguem:
    1. db.execute(text("BEGIN IMMEDIATE"))     -> lock de escrita (ADR-003 §2.3)
    2. (checagem de CPF duplicado acontece AQUI DENTRO, sob o mesmo lock —
       mesmo motivo documentado em case_service.generate_case_code: duas
       criações simultâneas com o mesmo CPF não podem passar)
    3. db.add(entidade); db.flush()            -> materializa entity_id
    4. audit_service.log_action(..., manage_transaction=False)
    5. db.commit()                             -> commit único; falha -> rollback
  Assim, entidade e log vivem na MESMA transação: não há ação não-logada.
  Funções de leitura (get/list) NÃO abrem transação imediata e NÃO auditam.

Strings de action (mesmo contrato de hash do ADR-003 §3.2, por analogia às
strings já em uso para "case_*"): "person_create", "person_update",
"person_archive".

NOTA (D57): a checagem de duplicidade roda tanto em create_person quanto
em update_person (quando cpf é enviado e muda), porque CA-002.5 fala em
"quando o operador informa CPF que já existe" sem restringir a criação —
editar uma pessoa para um CPF que já pertence a outra é o mesmo risco.
Se esta leitura do CA estiver errada, é fácil restringir a checagem só à
criação — sinalizado para revisão do operador.

Sprint 01 — Bloco 9, Sub-passo 9.2.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.person import Person
from app.schemas.persons import PersonCreate, PersonUpdate
from app.services import audit_service

# Tipo de entidade usado nos logs de auditoria (05_MODELO_DE_DADOS.md §3.8)
_ENTITY_TYPE = "person"

# Colunas permitidas para ordenação na listagem — mesmo espírito de
# case_service._SORTABLE (evita nome de coluna arbitrário vindo do cliente).
_SORTABLE = {
    "full_name": Person.full_name,
    "created_at": Person.created_at,
    "status": Person.status,
}

_CPF_NAO_DIGITO = re.compile(r"\D")


class DuplicateCPFError(Exception):
    """Levantada quando o CPF informado já pertence a outra pessoa (CA-002.5, D57).

    Carrega o id e o nome da pessoa já cadastrada com este CPF, para que a
    camada de API/UI possa oferecer "abrir pessoa existente" ao operador
    em vez de um erro genérico.
    """

    def __init__(self, cpf_normalizado: str, existing_person_id: int, existing_person_name: str):
        self.cpf_normalizado = cpf_normalizado
        self.existing_person_id = existing_person_id
        self.existing_person_name = existing_person_name
        super().__init__(
            f"CPF {cpf_normalizado!r} já pertence à pessoa "
            f"id={existing_person_id} ({existing_person_name!r})."
        )


def _now_iso() -> str:
    """Timestamp ISO 8601 UTC com microsegundos e sufixo Z.

    Mesmo formato usado pelo audit_service (ADR-003 §2.1) e por
    case_service._now_iso, por consistência.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def normalize_cpf(cpf: Optional[str]) -> Optional[str]:
    """Reduz o CPF a apenas dígitos (CA-002.2). None/vazio permanece None.

    Não valida quantidade de dígitos nem dígito verificador — o CA-002.2
    pede apenas normalização para exibição/busca consistente, não
    validação de CPF real (fora de escopo do Bloco 9).
    """
    if cpf is None:
        return None
    digits = _CPF_NAO_DIGITO.sub("", cpf)
    return digits or None


def _find_person_by_cpf(db: Session, cpf_normalizado: str, exclude_id: Optional[int] = None) -> Optional[Person]:
    """Busca uma pessoa existente com o mesmo CPF normalizado.

    exclude_id existe para update_person: ao editar a própria pessoa sem
    mudar o CPF, ela não deve "colidir consigo mesma".
    """
    stmt = select(Person).where(Person.cpf == cpf_normalizado)
    if exclude_id is not None:
        stmt = stmt.where(Person.id != exclude_id)
    return db.execute(stmt).scalars().first()


def create_person(db: Session, data: PersonCreate, user_id: int) -> Person:
    """Cria uma pessoa e registra a auditoria na mesma transação (CA-002.1, CA-002.7).

    Sequência conforme ADR-003a: BEGIN IMMEDIATE -> checa CPF duplicado
    (D57) -> insere pessoa -> flush (materializa id) ->
    log_action(manage_transaction=False) -> commit. Qualquer falha faz
    rollback de pessoa e log juntos.

    Levanta DuplicateCPFError se o cpf normalizado já pertencer a outra
    pessoa (CA-002.5) — a checagem acontece DENTRO da transação imediata,
    sob o mesmo lock de escrita, para evitar duas criações simultâneas
    com o mesmo CPF (mesmo raciocínio de case_service.generate_case_code).
    """
    cpf_normalizado = normalize_cpf(data.cpf)

    db.execute(text("BEGIN IMMEDIATE"))  # ADR-003 §2.3 / ADR-003a passo 1
    try:
        if cpf_normalizado:
            existing = _find_person_by_cpf(db, cpf_normalizado)
            if existing is not None:
                db.rollback()
                raise DuplicateCPFError(cpf_normalizado, existing.id, existing.full_name)

        now = _now_iso()
        person = Person(
            full_name=data.full_name,
            aliases=data.aliases,
            cpf=cpf_normalizado,
            rg=data.rg,
            birth_date=data.birth_date,
            mother_name=data.mother_name,
            father_name=data.father_name,
            notes=data.notes,
            source=data.source,
            reliability_level=data.reliability_level or "pending",  # default explícito
            status="active",  # default aplicado explicitamente (mesmo espírito de D45)
            created_at=now,
            created_by=user_id,
        )
        db.add(person)
        db.flush()  # materializa person.id para usar como entity_id
        audit_service.log_action(
            db,
            action="person_create",
            user_id=user_id,
            entity_type=_ENTITY_TYPE,
            entity_id=person.id,
            description=f"Criação da pessoa {person.full_name!r}",
            manage_transaction=False,  # ADR-003a: a transação é deste serviço
        )
        db.commit()
        db.refresh(person)
        return person
    except DuplicateCPFError:
        # rollback já foi feito acima, antes de levantar; apenas repropaga.
        raise
    except Exception:
        db.rollback()
        raise


def update_person(
    db: Session, person_id: int, data: PersonUpdate, user_id: int
) -> Optional[Person]:
    """Edita campos de uma pessoa e audita (CA-002.6, CA-002.7).

    Aplica apenas os campos enviados (edição parcial). status NÃO é
    alterado por aqui (arquivar é archive_person, dedicado).

    Levanta DuplicateCPFError se o cpf enviado (normalizado) já pertencer
    a OUTRA pessoa (D57 — ver nota no cabeçalho do módulo).

    Retorna None se a pessoa não existir.
    """
    person = db.get(Person, person_id)
    if person is None:
        return None

    # Só os campos efetivamente enviados (exclude_unset) entram na edição.
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        return person  # nada a alterar; não gera log de edição vazia

    if "cpf" in changes:
        changes["cpf"] = normalize_cpf(changes["cpf"])

    db.execute(text("BEGIN IMMEDIATE"))
    try:
        if "cpf" in changes and changes["cpf"]:
            existing = _find_person_by_cpf(db, changes["cpf"], exclude_id=person.id)
            if existing is not None:
                db.rollback()
                raise DuplicateCPFError(changes["cpf"], existing.id, existing.full_name)

        changed_fields = []
        for field, value in changes.items():
            if getattr(person, field) != value:
                setattr(person, field, value)
                changed_fields.append(field)

        if not changed_fields:
            # Valores idênticos aos atuais: nada mudou de fato.
            db.rollback()
            return person

        person.updated_at = _now_iso()
        person.updated_by = user_id
        db.flush()
        audit_service.log_action(
            db,
            action="person_update",
            user_id=user_id,
            entity_type=_ENTITY_TYPE,
            entity_id=person.id,
            description=f"Edição da pessoa {person.full_name!r} — campos: {', '.join(changed_fields)}",
            manage_transaction=False,
        )
        db.commit()
        db.refresh(person)
        return person
    except DuplicateCPFError:
        raise
    except Exception:
        db.rollback()
        raise


def archive_person(db: Session, person_id: int, user_id: int) -> Optional[Person]:
    """Arquiva uma pessoa (exclusão lógica) e audita (CA-002.7).

    Idempotente: arquivar uma pessoa já arquivada não gera novo log
    (mesmo espírito de D-idempotência do archive_case, Bloco 8.5).
    Retorna None se a pessoa não existir.
    """
    person = db.get(Person, person_id)
    if person is None:
        return None

    if person.status == "archived":
        return person  # idempotente — sem log de arquivamento repetido

    db.execute(text("BEGIN IMMEDIATE"))
    try:
        person.status = "archived"
        person.updated_at = _now_iso()
        person.updated_by = user_id
        db.flush()
        audit_service.log_action(
            db,
            action="person_archive",
            user_id=user_id,
            entity_type=_ENTITY_TYPE,
            entity_id=person.id,
            description=f"Arquivamento da pessoa {person.full_name!r}",
            manage_transaction=False,
        )
        db.commit()
        db.refresh(person)
        return person
    except Exception:
        db.rollback()
        raise


def get_person(db: Session, person_id: int) -> Optional[Person]:
    """Retorna uma pessoa por id, ou None. Leitura pura — não audita."""
    return db.get(Person, person_id)


def list_persons(
    db: Session,
    *,
    include_archived: bool = False,
    sort_by: str = "created_at",
    descending: bool = True,
) -> list[Person]:
    """Lista pessoas com ordenação e filtro de arquivadas (CA-002.4).

    Por padrão, oculta arquivadas (lista padrão) e ordena por data de
    criação decrescente. sort_by aceita: full_name, created_at, status.
    Leitura pura — não audita.
    """
    column = _SORTABLE.get(sort_by, Person.created_at)
    order = column.desc() if descending else column.asc()

    stmt = select(Person)
    if not include_archived:
        stmt = stmt.where(Person.status != "archived")
    stmt = stmt.order_by(order)

    return list(db.execute(stmt).scalars().all())

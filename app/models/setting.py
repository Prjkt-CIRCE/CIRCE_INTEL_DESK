"""
CIRCE Intel Desk — Modelo Setting (parâmetros operacionais).

Referência: ESTADO_DO_PROJETO.md §10 D11.
Todos os parâmetros operacionais (timeouts, tentativas, bloqueios)
ficam aqui, configuráveis pelo operador via UI. Exceção:
host=127.0.0.1 (D3) — não fica em settings, é hardcoded em run.py.

Valor é sempre serializado como string; value_type orienta a conversão
na camada de serviço (Bloco 4).

editable_by_operator: protege configurações internas que possam
existir no futuro e que não devam ser tocadas pela UI comum.

Sprint 01 — Bloco 2.
"""

from typing import Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Setting(Base):
    """Parâmetro operacional configurável (D11)."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String, nullable=False)
    value_type: Mapped[str] = mapped_column(String, nullable=False)  # int|str|bool|float
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    editable_by_operator: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )
    updated_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    updated_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Setting key={self.key!r} value={self.value!r}>"

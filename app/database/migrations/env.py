"""
CIRCE Intel Desk — Alembic env.py.

Este arquivo é executado pelo Alembic em cada operação (revision, upgrade,
downgrade). Customizações em relação ao template padrão gerado por
`alembic init`:

1. Adiciona a raiz do projeto ao sys.path para que `from app.models import Base`
   funcione (Alembic roda de dentro de app/database/migrations/).
2. Importa Base de app.models — necessário para --autogenerate detectar
   mudanças nos modelos.
3. Importa DATABASE_URL de app.database.session — URL vem do config da
   aplicação, não do alembic.ini.
4. Habilita render_as_batch=True para SQLite — necessário para ALTER TABLE
   em migrações futuras (SQLite tem suporte limitado a alter; o modo batch
   recria a tabela transparentemente).
5. include_object exclui tabelas fts_* do autogenerate — tabelas virtuais
   FTS5 são gerenciadas manualmente e não devem ser tocadas pelo diff ORM.

Sprint 01 — Bloco 3.
Sprint 01-B — FTS5: adição do include_object.
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# Adiciona a raiz do projeto ao sys.path.
# __file__ aqui é app/database/migrations/env.py. Subir 3 níveis = raiz.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Imports da aplicação. DEVEM vir DEPOIS do ajuste do sys.path.
from app.database.session import DATABASE_URL  # noqa: E402
from app.models import Base  # noqa: E402

# Objeto de configuração do Alembic, populado a partir do alembic.ini.
config = context.config

# Injeta dinamicamente a URL do banco, sobrescrevendo a entrada vazia do .ini.
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Configura logging conforme o .ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata alvo para --autogenerate. Base.metadata contém todos os modelos
# registrados pelo import em app/models/__init__.py.
target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    """Exclui tabelas virtuais FTS5 do diff de autogenerate."""
    if type_ == "table" and name.startswith("fts_"):
        return False
    return True


def run_migrations_offline() -> None:
    """
    Roda migrações em modo offline.

    Modo offline emite SQL para stdout/arquivo em vez de executar contra
    um banco real. Útil para gerar scripts SQL para deploy manual.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # Necessário para SQLite (ver docstring no topo).
        compare_type=True,
        compare_server_default=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Roda migrações em modo online — conectando ao banco e executando.

    Este é o modo padrão (chamado por `alembic upgrade`, `alembic revision
    --autogenerate`, etc).
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Necessário para SQLite (ver docstring no topo).
            compare_type=True,
            compare_server_default=True,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

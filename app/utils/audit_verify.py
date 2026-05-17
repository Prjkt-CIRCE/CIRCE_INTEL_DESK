"""
CIRCE Intel Desk — Utilitário de verificação da cadeia de auditoria.

Uso (com venv ativo, na raiz do projeto):
    python -m app.utils.audit_verify

Saída em caso de cadeia íntegra:
    [OK] Cadeia de auditoria íntegra. 42 registros verificados.

Saída em caso de problema:
    [ERRO] Cadeia corrompida no registro id=17.
    Detalhe: Hash corrompido no id=17: recalculado='a3f1...' armazenado='b9c2...'
    Registros verificados antes do problema: 16.

Referência: ADR-003 §2.7.
Sprint 01 — Bloco 7.
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.database.session import get_session          # noqa: E402
from app.services.audit_service import verify_chain  # noqa: E402


def main() -> None:
    """Verifica a cadeia de auditoria e imprime o resultado."""
    print("CIRCE Intel Desk — Verificação de cadeia de auditoria")
    print("-" * 52)

    db_gen = get_session()
    db = next(db_gen)

    try:
        result = verify_chain(db)
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

    total = result["total"]

    if result["ok"]:
        if total == 0:
            print("[AVISO] Tabela de auditoria vazia. Nenhum registro para verificar.")
        else:
            print(f"[OK] Cadeia de auditoria íntegra. {total} registros verificados.")
    else:
        broken_at = result["broken_at_id"]
        error_msg = result["error"]
        print(f"[ERRO] Cadeia corrompida no registro id={broken_at}.")
        print(f"Detalhe: {error_msg}")
        print(f"Registros verificados antes do problema: {total}.")
        sys.exit(1)


if __name__ == "__main__":
    main()
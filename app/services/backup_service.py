"""
CIRCE Intel Desk — Serviço de Backup básico (RF-022 CA-022.1 / CA-022.2).

Responsabilidades:
  - Copiar o banco de dados (circe.db) para data/backups/{timestamp}/
  - Copiar recursivamente a pasta data/cases/ (arquivos originais importados)
  - Gerar data/backups/{timestamp}/manifest.json com:
      - timestamp ISO-8601 da geração
      - lista de arquivos copiados com caminho relativo e hash SHA-256
      - contagem e tamanho total
  - Registrar a ação no audit_log (action='backup_generated')

Limitações (Sprint 03):
  - Backup em texto claro — criptografia é Sprint 10 (CA-022.3 / CA-022.4).
  - Restauração não implementada aqui — Sprint 10.
  - Sem compressão — cópia direta para facilitar inspeção manual.

Sprint 03 — Sub-passo 03-7.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constantes de caminhos
# ---------------------------------------------------------------------------

# Raiz do projeto: dois níveis acima deste arquivo quando em app/services/.
# Em produção: BASE_DIR = Path(__file__).resolve().parent.parent.parent
# Aqui usamos variável configurável para facilitar os testes.
_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    """Calcula o hash SHA-256 de um arquivo em blocos (memory-safe)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _copy_file_with_hash(src: Path, dst: Path) -> dict[str, Any]:
    """
    Copia src -> dst (criando diretórios intermediários se necessário)
    e retorna um dict de manifesto para esse arquivo.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return {
        "path": dst.name if dst.parent == dst.parent else str(dst),
        "sha256": _sha256(dst),
        "size_bytes": dst.stat().st_size,
    }


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------

def run_backup(data_dir: Path | None = None) -> dict[str, Any]:
    """
    Executa o backup básico e retorna um dicionário com o resultado.

    Retorno:
        {
            "backup_dir": str,          # caminho absoluto da pasta de backup
            "timestamp": str,           # ISO-8601 UTC
            "files": [                  # lista de arquivos copiados
                {"relative_path": str, "sha256": str, "size_bytes": int},
                ...
            ],
            "total_files": int,
            "total_bytes": int,
            "manifest_path": str,       # caminho absoluto do manifest.json
        }

    Lança:
        RuntimeError — se o banco de dados não for encontrado.
        OSError — se houver falha de permissão ou disco cheio.
    """
    if data_dir is None:
        data_dir = _DEFAULT_DATA_DIR

    data_dir = Path(data_dir)

    # ---- Verificar pré-condição: banco de dados deve existir ---------------
    db_path = data_dir / "circe.db"
    if not db_path.exists():
        raise RuntimeError(
            f"Banco de dados nao encontrado em {db_path}. "
            "Verifique se o sistema foi inicializado corretamente."
        )

    # ---- Criar pasta de destino com timestamp ------------------------------
    now_utc = datetime.now(timezone.utc)
    ts_label = now_utc.strftime("%Y%m%d_%H%M%S")
    backup_dir = data_dir / "backups" / ts_label
    backup_dir.mkdir(parents=True, exist_ok=True)

    files_manifest: list[dict[str, Any]] = []

    # ---- Copiar banco de dados ---------------------------------------------
    db_dst = backup_dir / "circe.db"
    db_entry = _copy_file_with_hash(db_path, db_dst)
    db_entry["relative_path"] = "circe.db"
    files_manifest.append(db_entry)

    # ---- Copiar pasta data/cases/ recursivamente ---------------------------
    cases_src = data_dir / "cases"
    if cases_src.exists() and cases_src.is_dir():
        cases_dst = backup_dir / "cases"
        for src_file in sorted(cases_src.rglob("*")):
            if src_file.is_file():
                rel = src_file.relative_to(data_dir)   # ex: cases/1/original/doc.pdf
                dst_file = backup_dir / rel
                entry = _copy_file_with_hash(src_file, dst_file)
                entry["relative_path"] = str(rel).replace("\\", "/")
                files_manifest.append(entry)

    # ---- Gerar manifest.json -----------------------------------------------
    total_bytes = sum(e["size_bytes"] for e in files_manifest)
    manifest: dict[str, Any] = {
        "circe_backup_version": "1.0",
        "generated_at": now_utc.isoformat(),
        "total_files": len(files_manifest),
        "total_bytes": total_bytes,
        "files": files_manifest,
    }
    manifest_path = backup_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "backup_dir": str(backup_dir),
        "timestamp": now_utc.isoformat(),
        "files": files_manifest,
        "total_files": len(files_manifest),
        "total_bytes": total_bytes,
        "manifest_path": str(manifest_path),
    }

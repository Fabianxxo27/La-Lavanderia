"""Ejecuta una migracion SQL usando la configuracion de Flask/SQLAlchemy."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Permite resolver rutas desde la raiz del proyecto.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def parse_sql_statements(sql_text: str) -> list[str]:
    """Convierte el contenido SQL en sentencias individuales."""
    statements = []
    cleaned_lines = []

    for line in sql_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        if "--" in line:
            line = line.split("--", 1)[0]
        cleaned_lines.append(line)

    cleaned_sql = "\n".join(cleaned_lines)
    for statement in cleaned_sql.split(";"):
        statement = statement.strip()
        if statement:
            statements.append(statement)

    return statements


def ejecutar_migracion(sql_path: Path) -> None:
    """Ejecuta todas las sentencias SQL del archivo recibido."""
    if not sql_path.exists():
        raise FileNotFoundError(f"No existe el archivo: {sql_path}")

    load_dotenv(ROOT_DIR / ".env")
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("No se encontro DATABASE_URL en las variables de entorno")

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    sql_text = sql_path.read_text(encoding="utf-8")
    statements = parse_sql_statements(sql_text)

    if not statements:
        print(f"[INFO] No hay sentencias SQL para ejecutar en {sql_path}")
        return

    engine = create_engine(database_url, pool_pre_ping=True)
    with engine.begin() as conn:
        for idx, statement in enumerate(statements, start=1):
            conn.execute(text(statement))
            print(f"[OK] Sentencia {idx} ejecutada")

    print(f"[OK] Migracion completada: {sql_path.name}")


def main() -> int:
    """Punto de entrada para CLI.

    Uso:
        python scripts/ejecutar_migracion.py
        python scripts/ejecutar_migracion.py migrations/archivo.sql
    """
    default_path = ROOT_DIR / "migrations" / "create_verification_codes.sql"

    if len(sys.argv) > 1:
        sql_path = ROOT_DIR / sys.argv[1]
    else:
        sql_path = default_path

    try:
        ejecutar_migracion(sql_path)
        return 0
    except Exception as exc:
        print(f"[ERROR] Fallo la migracion: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

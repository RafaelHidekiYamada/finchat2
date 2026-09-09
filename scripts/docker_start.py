"""Aplica as migrations e inicia a API como processo principal do container."""

import os
import subprocess
import sys


def main():
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    # Substitui o processo para que Uvicorn receba os sinais de encerramento.
    os.execv(sys.executable, [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"])


if __name__ == "__main__":
    main()

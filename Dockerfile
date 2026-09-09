FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=America/Sao_Paulo

WORKDIR /app

COPY requirements-lock.txt ./
RUN python -m pip install --no-cache-dir -r requirements-lock.txt \
    && groupadd --gid 10001 finchat \
    && useradd --uid 10001 --gid finchat --no-create-home finchat \
    && mkdir /app/data \
    && chown finchat:finchat /app/data

# Cópias explícitas mantêm .env, banco local e logs fora da imagem.
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini pytest.ini ./
COPY scripts/docker_start.py ./scripts/docker_start.py
COPY tests ./tests

USER finchat
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).close()"]

CMD ["python", "scripts/docker_start.py"]

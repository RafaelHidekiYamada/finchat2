"""Cada teste recebe um SQLite em memória, sem acessar o banco local."""

import os

os.environ.setdefault("SECRET_KEY", "segredo-apenas-para-testes-locais-1234567890")
os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # Registra todas as tabelas no metadata.
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from tests.helpers import PREFIX, sucesso


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def ativar_chaves_estrangeiras(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(db_session):
    def banco_de_teste():
        yield db_session

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = banco_de_teste
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


@pytest.fixture
def user_factory(client):
    used = {"CPF": 0, "CNPJ": 0}
    documents = {
        "CPF": ["52998224725", "11144477735"],
        "CNPJ": ["11222333000181", "11444777000161"],
    }

    def criar(document_type="CPF", **changes):
        index = used[document_type]
        used[document_type] += 1
        offset = index + (10 if document_type == "CNPJ" else 0)
        payload = {
            "name": f"Usuário de teste {document_type} {index}",
            "email": f"teste-{document_type.lower()}-{index}@example.com",
            "whatsapp": f"+551199990{offset:04d}",
            "document": documents[document_type][index],
            "document_type": document_type,
            "password": "TesteSeguro@123",
        }
        payload.update(changes)
        user = sucesso(client.post(f"{PREFIX}/auth/register", json=payload), 201)
        token = sucesso(
            client.post(
                f"{PREFIX}/auth/login",
                json={"email": payload["email"], "password": payload["password"]},
            )
        )["access_token"]
        return {"user": user, "payload": payload, "headers": {"Authorization": f"Bearer {token}"}}

    return criar


@pytest.fixture
def cpf(user_factory):
    return user_factory("CPF")


@pytest.fixture
def cnpj(user_factory):
    return user_factory("CNPJ")

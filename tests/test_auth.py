"""Cadastro, documentos, credenciais e proteção das rotas privadas."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.models import User
from tests.helpers import PREFIX, erro, sucesso


@pytest.mark.parametrize(
    ("profile", "masked", "normalized"),
    [
        ("CPF", "529.982.247-25", "52998224725"),
        ("CNPJ", "11.222.333/0001-81", "11222333000181"),
    ],
)
def test_cadastro_login_documento_normalizado_e_senha_protegida(
    client, user_factory, db_session, profile, masked, normalized
):
    identity = user_factory(profile, document=masked)
    user = identity["user"]
    assert user["document"] == normalized
    assert user["document_type"] == profile
    assert "password" not in user
    assert "password_hash" not in user
    me = sucesso(client.get(f"{PREFIX}/auth/me", headers=identity["headers"]))
    assert me["id"] == user["id"]
    stored = db_session.scalar(select(User).where(User.email == identity["payload"]["email"]))
    assert stored.document == normalized
    assert stored.password_hash != identity["payload"]["password"]
    assert stored.password_hash


@pytest.mark.parametrize(
    "path", ["/auth/me", "/bank-accounts", "/categories", "/transactions", "/partners", "/contracts"]
)
def test_rotas_privadas_exigem_autenticacao(client, path):
    erro(client.get(f"{PREFIX}{path}"), 401)


def test_token_invalido_e_senha_incorreta_sao_recusados(client, cpf):
    erro(client.get(f"{PREFIX}/auth/me", headers={"Authorization": "Bearer token-invalido"}), 401)
    response = client.post(
        f"{PREFIX}/auth/login",
        json={"email": cpf["payload"]["email"], "password": "SenhaIncorreta@123"},
    )
    erro(response, 401)


@pytest.mark.parametrize("problem", ["expirado", "assinatura_adulterada", "audiencia_incorreta"])
def test_jwt_invalido_nao_autentica_usuario_existente(client, cpf, problem):
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(cpf["user"]["id"]), "iat": now - timedelta(minutes=5),
        "exp": now + timedelta(minutes=5), "iss": "finchat", "aud": "finchat-api",
    }
    signing_key = get_settings().secret_key
    if problem == "expirado":
        claims["exp"] = now - timedelta(seconds=1)
    elif problem == "assinatura_adulterada":
        signing_key = "chave-incorreta-apenas-para-teste-de-assinatura-123456789"
    else:
        claims["aud"] = "outro-servico"
    token = jwt.encode(claims, signing_key, algorithm="HS256")
    erro(client.get(f"{PREFIX}/auth/me", headers={"Authorization": f"Bearer {token}"}), 401)


def test_usuario_inativo_nao_pode_fazer_login(client, cpf, db_session):
    user = db_session.scalar(select(User).where(User.email == cpf["payload"]["email"]))
    user.is_active = False
    db_session.commit()
    response = client.post(
        f"{PREFIX}/auth/login",
        json={"email": cpf["payload"]["email"], "password": cpf["payload"]["password"]},
    )
    assert response.status_code in (401, 403), response.text
    erro(response, response.status_code)


@pytest.mark.parametrize("field", ["email", "whatsapp", "document"])
def test_identificadores_duplicados_retornam_conflito(client, cpf, field):
    payload = {
        **cpf["payload"],
        "email": "outra-pessoa@example.com",
        "whatsapp": "+5511999999988",
        "document": "11144477735",
    }
    payload[field] = cpf["payload"][field]
    if field == "document":
        payload[field] = "529.982.247-25"
    erro(client.post(f"{PREFIX}/auth/register", json=payload), 409)


@pytest.mark.parametrize(
    ("document_type", "document"),
    [("CPF", "11111111111"), ("CPF", "52998224724"), ("CPF", "123"),
     ("CNPJ", "11111111111111"), ("CNPJ", "11222333000180"), ("CNPJ", "52998224725")],
)
def test_documentos_invalidos_sao_recusados(client, document_type, document):
    payload = {
        "name": "Documento inválido",
        "email": "documento@example.com",
        "whatsapp": "+5511999999911",
        "document": document,
        "document_type": document_type,
        "password": "TesteSeguro@123",
    }
    erro(client.post(f"{PREFIX}/auth/register", json=payload), 422)


def test_cadastro_cria_categorias_iniciais(client, cpf):
    categories = sucesso(client.get(f"{PREFIX}/categories", headers=cpf["headers"]))
    pairs = {(item["name"], item["type"]) for item in categories}
    assert {
        ("Alimentação", "EXPENSE"), ("Transporte", "EXPENSE"), ("Moradia", "EXPENSE"),
        ("Salário", "INCOME"), ("Vendas", "INCOME"), ("Serviços", "INCOME"),
        ("Fornecedores", "EXPENSE"),
    } <= pairs

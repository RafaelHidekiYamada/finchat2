"""Simulações locais e documentação pública da API."""

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app import seed
from app.main import app
from app.models import Category, Transaction
from tests.helpers import PREFIX, criar_conta, dinheiro, erro, sucesso


def test_sincronizacao_bancaria_simulada_e_idempotente(client, cpf):
    headers = cpf["headers"]
    account = criar_conta(client, headers)
    connection = sucesso(client.post(f"{PREFIX}/bank-connections", headers=headers,
                                     json={"bank_account_id": account["id"]}), 201)
    assert connection["institution"] == account["institution"]
    assert connection["status"]
    assert connection["consent_at"]
    assert connection["external_id"]
    path = f"{PREFIX}/bank-connections/{connection['id']}/sync"
    first = sucesso(client.post(path, headers=headers))
    assert first["imported_count"] > 0
    assert len(first["transactions"]) == first["imported_count"]
    assert all(row["origin"] == "BANK" and row["bank_account_id"] == account["id"] for row in first["transactions"])
    second = sucesso(client.post(path, headers=headers))
    assert second["imported_count"] == 0
    assert second["transactions"] == []
    transactions = sucesso(client.get(f"{PREFIX}/transactions", headers=headers))
    assert len(transactions) == first["imported_count"]
    listed = sucesso(client.get(f"{PREFIX}/bank-connections", headers=headers))
    assert listed[0]["last_synced_at"]


def test_sincronizacao_reutiliza_categoria_renomeada_sem_duplicar(client, cpf):
    headers = cpf["headers"]
    categories = sucesso(client.get(f"{PREFIX}/categories", headers=headers))
    transport = next(item for item in categories if item["name"] == "Transporte")
    sucesso(client.put(f"{PREFIX}/categories/{transport['id']}", headers=headers,
                       json={"name": "transporte"}))
    expected_categories = sucesso(client.get(f"{PREFIX}/categories", headers=headers))
    account = criar_conta(client, headers)
    connection = sucesso(client.post(f"{PREFIX}/bank-connections", headers=headers,
                                     json={"bank_account_id": account["id"]}), 201)
    path = f"{PREFIX}/bank-connections/{connection['id']}/sync"

    first = sucesso(client.post(path, headers=headers))
    assert first["imported_count"] == 3
    assert sucesso(client.get(f"{PREFIX}/categories", headers=headers)) == expected_categories
    imported_transport = sucesso(client.get(f"{PREFIX}/transactions", headers=headers,
                                            params={"category_id": transport["id"]}))
    assert len(imported_transport) == 1
    assert imported_transport[0]["category_id"] == transport["id"]
    assert imported_transport[0]["type"] == "EXPENSE"
    assert dinheiro(imported_transport[0]["amount"]) == Decimal("25.00")

    second = sucesso(client.post(path, headers=headers))
    assert second["imported_count"] == 0
    assert second["transactions"] == []
    assert sucesso(client.get(f"{PREFIX}/categories", headers=headers)) == expected_categories
    transactions = sucesso(client.get(f"{PREFIX}/transactions", headers=headers))
    assert len(transactions) == first["imported_count"]


def test_seed_preserva_categorias_renomeadas_ao_repetir(db_session, monkeypatch):
    monkeypatch.setattr(seed, "SessionLocal", sessionmaker(bind=db_session.get_bind(), expire_on_commit=False))
    seed.populate()
    categories = list(db_session.scalars(select(Category).order_by(Category.id)))
    assert len(categories) == 14
    for category in categories:
        category.name = category.name.lower()
    db_session.commit()
    expected_categories = [(row.id, row.user_id, row.name, row.type) for row in categories]
    expected_transactions = list(db_session.execute(select(Transaction.id, Transaction.category_id).order_by(Transaction.id)))
    assert len(expected_transactions) == 5

    seed.populate()
    db_session.expire_all()
    actual_categories = [(row.id, row.user_id, row.name, row.type)
                         for row in db_session.scalars(select(Category).order_by(Category.id))]
    actual_transactions = list(db_session.execute(select(Transaction.id, Transaction.category_id).order_by(Transaction.id)))
    assert actual_categories == expected_categories
    assert actual_transactions == expected_transactions


def test_conexao_bancaria_respeita_titularidade(client, cpf, user_factory):
    owner = cpf["headers"]
    other = user_factory("CPF")["headers"]
    account = criar_conta(client, owner)
    erro(client.post(f"{PREFIX}/bank-connections", headers=other,
                      json={"bank_account_id": account["id"]}), 404)
    connection = sucesso(client.post(f"{PREFIX}/bank-connections", headers=owner,
                                     json={"bank_account_id": account["id"]}), 201)
    erro(client.post(f"{PREFIX}/bank-connections/{connection['id']}/sync", headers=other), 404)
    assert sucesso(client.get(f"{PREFIX}/bank-connections", headers=other)) == []


def test_chat_consulta_saldo_e_resumo_do_mes(client, cpf):
    headers = cpf["headers"]
    criar_conta(client, headers, initial_balance="250.50")
    for command in ["saldo", "resumo do mês"]:
        result = sucesso(client.post(f"{PREFIX}/chat/commands", headers=headers, json={"command": command}))
        assert result["action"]
        assert result["reply"]
        assert dinheiro(result["summary"]["balance"]) == Decimal("250.50")


def test_chat_registra_gasto_e_recebimento(client, cpf):
    headers = cpf["headers"]
    for command, kind, amount in [
        ("gastei 50 em alimentação", "EXPENSE", "50.00"),
        ("recebi 200 por serviço", "INCOME", "200.00"),
    ]:
        result = sucesso(client.post(f"{PREFIX}/chat/commands", headers=headers, json={"command": command}))
        assert result["reply"]
        transaction = result["transaction"]
        assert transaction["type"] == kind
        assert dinheiro(transaction["amount"]) == Decimal(amount)
        assert transaction["origin"] in {"CASH", "MANUAL"}
        stored = sucesso(client.get(f"{PREFIX}/transactions/{transaction['id']}", headers=headers))
        assert stored["id"] == transaction["id"]
    summary = sucesso(client.get(f"{PREFIX}/transactions/summary", headers=headers))
    assert dinheiro(summary["balance"]) == Decimal("150.00")


def test_saude_documentacao_e_bearer_no_openapi(client):
    sucesso(client.get(f"{PREFIX}/health"))
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "FinChat API"
    assert schema["info"]["description"]
    schemes = schema["components"]["securitySchemes"]
    assert any(item.get("scheme", "").lower() == "bearer" for item in schemes.values())
    for path in ["/auth/register", "/auth/login", "/transactions", "/partners", "/contracts", "/chat/commands"]:
        assert f"{PREFIX}{path}" in schema["paths"]
    transaction_post = schema["paths"][f"{PREFIX}/transactions"]["post"]
    assert transaction_post["security"]
    assert transaction_post["tags"]
    assert transaction_post["requestBody"]
    assert {"201", "400", "401", "404", "422"} <= set(transaction_post["responses"])


def test_erro_interno_nao_expoe_detalhes_ao_cliente(client, cpf, db_session, monkeypatch):
    def falha_do_banco(*args, **kwargs):
        raise RuntimeError("detalhe-interno-confidencial-de-teste")

    monkeypatch.setattr(db_session, "scalars", falha_do_banco)
    with TestClient(app, raise_server_exceptions=False) as failure_client:
        response = failure_client.get(f"{PREFIX}/categories", headers=cpf["headers"])
    error = erro(response, 500)
    assert error["details"] == []
    assert "detalhe-interno-confidencial" not in response.text
    assert "RuntimeError" not in response.text
    assert "Traceback" not in response.text

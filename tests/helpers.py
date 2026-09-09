"""Asserções compartilhadas para o contrato HTTP da API."""

from decimal import Decimal


PREFIX = "/api/v1"


def sucesso(response, status=200):
    assert response.status_code == status, response.text
    body = response.json()
    assert isinstance(body["message"], str)
    assert body["message"]
    assert "data" in body
    return body["data"]


def erro(response, status):
    assert response.status_code == status, response.text
    body = response.json()
    assert set(body) == {"error"}
    assert isinstance(body["error"]["code"], str)
    assert isinstance(body["error"]["message"], str)
    assert isinstance(body["error"]["details"], list)
    return body["error"]


def dinheiro(value):
    return Decimal(str(value))


def criar_conta(client, headers, **changes):
    payload = {
        "institution": "Banco fictício de testes",
        "nickname": "Conta principal",
        "account_type": "CHECKING",
        "initial_balance": "100.00",
    }
    payload.update(changes)
    return sucesso(client.post(f"{PREFIX}/bank-accounts", json=payload, headers=headers), 201)


def categoria(client, headers, name="Alimentação"):
    categorias = sucesso(client.get(f"{PREFIX}/categories", headers=headers))
    return next(item for item in categorias if item["name"] == name)


def criar_transacao(client, headers, category_id, **changes):
    payload = {
        "description": "Despesa de teste",
        "amount": "50.00",
        "date": "2026-09-07",
        "type": "EXPENSE",
        "category_id": category_id,
    }
    payload.update(changes)
    return sucesso(client.post(f"{PREFIX}/transactions", json=payload, headers=headers), 201)


def criar_parceiro(client, headers, **changes):
    payload = {"name": "Cliente fictício", "type": "CLIENT"}
    payload.update(changes)
    return sucesso(client.post(f"{PREFIX}/partners", json=payload, headers=headers), 201)


def criar_contrato(client, headers, partner_id, **changes):
    payload = {
        "title": "Contrato demonstrativo",
        "partner_id": partner_id,
        "type": "INCOME",
        "expected_amount": "1000.00",
        "start_date": "2026-09-01",
        "end_date": "2026-12-31",
        "status": "ACTIVE",
    }
    payload.update(changes)
    return sucesso(client.post(f"{PREFIX}/contracts", json=payload, headers=headers), 201)

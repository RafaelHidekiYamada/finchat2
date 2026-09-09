"""Limites de entrada devem produzir erros de validação previsíveis."""

import pytest

from tests.helpers import PREFIX, categoria, criar_parceiro, erro


@pytest.mark.parametrize(("resource", "field", "maximum"), [
    ("bank-accounts", "institution", 120),
    ("bank-accounts", "nickname", 80),
    ("categories", "name", 80),
    ("partners", "name", 120),
    ("contracts", "title", 120),
    ("transactions", "description", 255),
    ("chat/commands", "command", 300),
])
def test_campos_de_texto_respeitam_limites(client, cnpj, resource, field, maximum):
    headers = cnpj["headers"]
    payloads = {
        "bank-accounts": {
            "institution": "Banco fictício", "nickname": "Conta de teste",
            "account_type": "CHECKING", "initial_balance": "0.00",
        },
        "categories": {"name": "Categoria de teste", "type": "EXPENSE"},
        "partners": {"name": "Cliente de teste", "type": "CLIENT"},
        "contracts": {
            "title": "Contrato de teste", "partner_id": 1, "type": "INCOME",
            "expected_amount": "100.00", "start_date": "2026-09-07",
        },
        "transactions": {
            "description": "Despesa de teste", "amount": "10.00", "date": "2026-09-07",
            "type": "EXPENSE", "category_id": categoria(client, headers)["id"],
        },
        "chat/commands": {"command": "saldo"},
    }
    payload = payloads[resource]
    if resource == "contracts":
        payload["partner_id"] = criar_parceiro(client, headers)["id"]
    payload[field] = "x" * (maximum + 1)
    erro(client.post(f"{PREFIX}/{resource}", headers=headers, json=payload), 422)


@pytest.mark.parametrize(("field", "value"), [
    ("name", "x" * 121),
    ("whatsapp", "1" * 31),
    ("password", "x" * 129),
])
def test_cadastro_rejeita_texto_excessivo(client, field, value):
    payload = {
        "name": "Usuário de teste", "email": "limites@example.com", "whatsapp": "+5511999999988",
        "document": "52998224725", "document_type": "CPF", "password": "TesteSeguro@123",
    }
    payload[field] = value
    response = client.post(f"{PREFIX}/auth/register", json=payload)
    erro(response, 422)
    if field == "password":
        assert value not in response.text

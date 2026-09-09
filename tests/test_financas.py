"""Fluxos financeiros e preservação de precisão monetária."""

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import Transaction
from tests.helpers import PREFIX, categoria, criar_conta, criar_transacao, dinheiro, erro, sucesso


def test_crud_categoria(client, cpf):
    headers = cpf["headers"]
    created = sucesso(client.post(
        f"{PREFIX}/categories", headers=headers, json={"name": "Educação", "type": "EXPENSE"}
    ), 201)
    path = f"{PREFIX}/categories/{created['id']}"
    assert sucesso(client.get(path, headers=headers))["name"] == "Educação"
    updated = sucesso(client.put(path, headers=headers, json={"name": "Cursos"}))
    assert updated["name"] == "Cursos"
    assert updated["type"] == "EXPENSE"
    assert sucesso(client.delete(path, headers=headers)) is None
    erro(client.get(path, headers=headers), 404)


def test_crud_conta_e_saldo_inicial(client, cpf):
    headers = cpf["headers"]
    account = criar_conta(client, headers, initial_balance="123.45")
    path = f"{PREFIX}/bank-accounts/{account['id']}"
    assert sucesso(client.get(path, headers=headers))["nickname"] == "Conta principal"
    listed = sucesso(client.get(f"{PREFIX}/bank-accounts", headers=headers))
    assert [item["id"] for item in listed] == [account["id"]]
    updated = sucesso(client.put(path, headers=headers, json={"nickname": "Reserva"}))
    assert updated["nickname"] == "Reserva"
    assert dinheiro(updated["initial_balance"]) == Decimal("123.45")
    balance = sucesso(client.get(f"{path}/balance", headers=headers))
    assert dinheiro(balance["balance"]) == Decimal("123.45")
    assert sucesso(client.delete(path, headers=headers)) is None
    erro(client.get(path, headers=headers), 404)


@pytest.mark.parametrize(("kind", "name"), [("INCOME", "Salário"), ("EXPENSE", "Alimentação")])
def test_cria_receita_e_despesa_com_valores_decimal(client, cpf, db_session, kind, name):
    headers = cpf["headers"]
    item = criar_transacao(client, headers, categoria(client, headers, name)["id"], type=kind, amount="10.25")
    assert dinheiro(item["amount"]) == Decimal("10.25")
    assert item["type"] == kind
    assert item["currency"] == "BRL"
    assert item["origin"] == "MANUAL"
    assert item["reconciliation_status"] == "PENDING"
    stored = db_session.scalar(select(Transaction).where(Transaction.id == item["id"]))
    assert isinstance(stored.amount, Decimal)
    assert stored.amount == Decimal("10.25")


def test_crud_transacao_recalcula_saldo(client, cpf):
    headers = cpf["headers"]
    account = criar_conta(client, headers)
    item = criar_transacao(
        client, headers, categoria(client, headers)["id"], bank_account_id=account["id"]
    )
    path = f"{PREFIX}/transactions/{item['id']}"
    balance_path = f"{PREFIX}/bank-accounts/{account['id']}/balance"
    assert sucesso(client.get(path, headers=headers))["id"] == item["id"]
    assert dinheiro(sucesso(client.get(balance_path, headers=headers))["balance"]) == Decimal("50.00")
    edited = sucesso(client.put(path, headers=headers, json={"amount": "25.15", "description": "Corrigida"}))
    assert edited["description"] == "Corrigida"
    assert dinheiro(sucesso(client.get(balance_path, headers=headers))["balance"]) == Decimal("74.85")
    assert sucesso(client.delete(path, headers=headers)) is None
    erro(client.get(path, headers=headers), 404)
    assert dinheiro(sucesso(client.get(balance_path, headers=headers))["balance"]) == Decimal("100.00")


def test_saldo_consolidado_inclui_contas_e_dinheiro(client, cpf):
    headers = cpf["headers"]
    account = criar_conta(client, headers, initial_balance="100.10")
    criar_conta(client, headers, nickname="Reserva", initial_balance="20.20")
    expense = categoria(client, headers)["id"]
    income = categoria(client, headers, "Salário")["id"]
    criar_transacao(client, headers, income, type="INCOME", amount="0.20", bank_account_id=account["id"])
    criar_transacao(client, headers, expense, amount="0.10", bank_account_id=account["id"])
    cash = sucesso(client.post(f"{PREFIX}/transactions/cash", headers=headers, json={
        "description": "Despesa em dinheiro", "type": "EXPENSE", "amount": "10.10",
        "date": "2026-09-07", "category_id": expense,
    }), 201)
    assert cash["origin"] == "CASH"
    assert cash["bank_account_id"] is None
    summary = sucesso(client.get(f"{PREFIX}/transactions/summary", headers=headers))
    assert dinheiro(summary["initial_balance"]) == Decimal("120.30")
    assert dinheiro(summary["total_income"]) == Decimal("0.20")
    assert dinheiro(summary["total_expenses"]) == Decimal("10.20")
    assert dinheiro(summary["balance"]) == Decimal("110.30")
    food = next(row for row in summary["by_category"] if row["category_id"] == expense)
    assert food["category_name"] == "Alimentação"
    assert dinheiro(food["total"]) == Decimal("10.20")
    balance = sucesso(client.get(f"{PREFIX}/bank-accounts/{account['id']}/balance", headers=headers))
    assert dinheiro(balance["balance"]) == Decimal("100.20")


@pytest.mark.parametrize("amount", ["0", "-1.00", "1.001", "NaN", "Infinity", "1e99999999", 1.25, True])
def test_valores_invalidos_nao_criam_transacoes(client, cpf, amount):
    headers = cpf["headers"]
    response = client.post(f"{PREFIX}/transactions", headers=headers, json={
        "description": "Inválida", "type": "EXPENSE", "amount": amount,
        "date": "2026-09-07", "category_id": categoria(client, headers)["id"],
    })
    erro(response, 422)
    assert sucesso(client.get(f"{PREFIX}/transactions", headers=headers)) == []


def test_categoria_deve_ser_compativel_com_tipo_na_criacao_e_edicao(client, cpf):
    headers = cpf["headers"]
    expense = categoria(client, headers)["id"]
    response = client.post(f"{PREFIX}/transactions", headers=headers, json={
        "description": "Categoria incompatível", "type": "INCOME", "amount": "10.00",
        "date": "2026-09-07", "category_id": expense,
    })
    erro(response, 400)
    item = criar_transacao(client, headers, expense)
    erro(client.put(f"{PREFIX}/transactions/{item['id']}", headers=headers, json={"type": "INCOME"}), 400)
    assert sucesso(client.get(f"{PREFIX}/transactions/{item['id']}", headers=headers))["type"] == "EXPENSE"


def test_amount_nulo_na_edicao_retorna_validacao_e_preserva_transacao(client, cpf):
    headers = cpf["headers"]
    item = criar_transacao(client, headers, categoria(client, headers)["id"])
    path = f"{PREFIX}/transactions/{item['id']}"
    erro(client.put(path, headers=headers, json={"amount": None}), 422)
    assert dinheiro(sucesso(client.get(path, headers=headers))["amount"]) == Decimal("50.00")


def test_filtros_de_periodo_tipo_categoria_conta_e_paginacao(client, cpf):
    headers = cpf["headers"]
    account = criar_conta(client, headers)
    food = categoria(client, headers)["id"]
    salary = categoria(client, headers, "Salário")["id"]
    old = criar_transacao(client, headers, food, date="2026-08-31", bank_account_id=account["id"])
    target = criar_transacao(client, headers, food, date="2026-09-07", bank_account_id=account["id"])
    received = criar_transacao(client, headers, salary, date="2026-09-30", type="INCOME")
    cases = [
        ({"start_date": "2026-09-01", "end_date": "2026-09-30"}, {target["id"], received["id"]}),
        ({"type": "INCOME"}, {received["id"]}),
        ({"category_id": food}, {old["id"], target["id"]}),
        ({"bank_account_id": account["id"]}, {old["id"], target["id"]}),
        ({"start_date": "2026-09-07", "end_date": "2026-09-07", "type": "EXPENSE", "category_id": food,
          "bank_account_id": account["id"]}, {target["id"]}),
    ]
    for params, expected in cases:
        items = sucesso(client.get(f"{PREFIX}/transactions", headers=headers, params=params))
        assert {item["id"] for item in items} == expected
    first = sucesso(client.get(f"{PREFIX}/transactions", headers=headers, params={"limit": 1, "offset": 0}))
    second = sucesso(client.get(f"{PREFIX}/transactions", headers=headers, params={"limit": 1, "offset": 1}))
    assert len(first) == len(second) == 1
    assert first[0]["id"] != second[0]["id"]


def test_resumo_por_periodo(client, cpf):
    headers = cpf["headers"]
    food = categoria(client, headers)["id"]
    criar_transacao(client, headers, food, amount="20.00", date="2026-08-31")
    criar_transacao(client, headers, food, amount="7.55", date="2026-09-01")
    summary = sucesso(client.get(f"{PREFIX}/transactions/summary", headers=headers, params={
        "start_date": "2026-09-01", "end_date": "2026-09-30",
    }))
    assert dinheiro(summary["total_expenses"]) == Decimal("7.55")


def test_recursos_utilizados_nao_podem_ser_excluidos(client, cpf):
    headers = cpf["headers"]
    account = criar_conta(client, headers)
    category_id = categoria(client, headers)["id"]
    transaction = criar_transacao(client, headers, category_id, bank_account_id=account["id"])
    for resource, resource_id in [("bank-accounts", account["id"]), ("categories", category_id)]:
        erro(client.delete(f"{PREFIX}/{resource}/{resource_id}", headers=headers), 409)
    assert sucesso(client.get(f"{PREFIX}/transactions/{transaction['id']}", headers=headers))["id"] == transaction["id"]


def test_categoria_utilizada_nao_pode_mudar_tipo(client, cpf):
    headers = cpf["headers"]
    category_id = categoria(client, headers)["id"]
    criar_transacao(client, headers, category_id)
    erro(client.put(f"{PREFIX}/categories/{category_id}", headers=headers, json={"type": "INCOME"}), 400)


def test_origem_bancaria_exige_conta_e_dinheiro_nao_aceita_conta(client, cpf):
    headers = cpf["headers"]
    account = criar_conta(client, headers)
    payload = {
        "description": "Origem inválida", "amount": "10.00", "date": "2026-09-07",
        "type": "EXPENSE", "category_id": categoria(client, headers)["id"], "origin": "BANK",
    }
    erro(client.post(f"{PREFIX}/transactions", headers=headers, json=payload), 400)
    payload.update(origin="CASH", bank_account_id=account["id"])
    erro(client.post(f"{PREFIX}/transactions", headers=headers, json=payload), 400)

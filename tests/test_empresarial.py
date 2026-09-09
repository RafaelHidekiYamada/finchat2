"""Perfis, parceiros, contratos e rastreabilidade de recebimentos e pagamentos."""

from decimal import Decimal

import pytest

from tests.helpers import (
    PREFIX, categoria, criar_contrato, criar_parceiro, criar_transacao, dinheiro, erro, sucesso,
)


@pytest.mark.parametrize("resource", ["partners", "contracts"])
def test_cpf_nao_pode_utilizar_funcionalidades_empresariais(client, cpf, resource):
    headers = cpf["headers"]
    payload = {"name": "Parceiro bloqueado", "type": "CLIENT"} if resource == "partners" else {
        "title": "Contrato bloqueado", "partner_id": 1, "type": "INCOME",
        "expected_amount": "1000.00", "start_date": "2026-09-01", "status": "ACTIVE",
    }
    erro(client.post(f"{PREFIX}/{resource}", headers=headers, json=payload), 403)
    erro(client.get(f"{PREFIX}/{resource}", headers=headers), 403)


def test_cnpj_cria_edita_lista_e_remove_parceiro_e_contrato(client, cnpj):
    headers = cnpj["headers"]
    partner = criar_parceiro(client, headers)
    contract = criar_contrato(client, headers, partner["id"])
    partner_path = f"{PREFIX}/partners/{partner['id']}"
    contract_path = f"{PREFIX}/contracts/{contract['id']}"
    assert sucesso(client.get(partner_path, headers=headers))["type"] == "CLIENT"
    assert sucesso(client.get(contract_path, headers=headers))["partner_id"] == partner["id"]
    assert [item["id"] for item in sucesso(client.get(f"{PREFIX}/partners", headers=headers))] == [partner["id"]]
    assert [item["id"] for item in sucesso(client.get(f"{PREFIX}/contracts", headers=headers))] == [contract["id"]]
    assert sucesso(client.put(partner_path, headers=headers, json={"name": "Cliente atualizado"}))["name"] == "Cliente atualizado"
    assert sucesso(client.put(contract_path, headers=headers, json={"status": "COMPLETED"}))["status"] == "COMPLETED"
    assert sucesso(client.delete(contract_path, headers=headers)) is None
    assert sucesso(client.delete(partner_path, headers=headers)) is None
    erro(client.get(contract_path, headers=headers), 404)
    erro(client.get(partner_path, headers=headers), 404)


@pytest.mark.parametrize(
    ("partner_type", "transaction_type", "category_name", "amount", "received", "paid"),
    [("CLIENT", "INCOME", "Serviços", "250.30", "250.30", "0.00"),
     ("SUPPLIER", "EXPENSE", "Fornecedores", "150.10", "0.00", "150.10")],
)
def test_vinculo_contrato_infere_parceiro_e_gera_resumos(
    client, cnpj, partner_type, transaction_type, category_name, amount, received, paid
):
    headers = cnpj["headers"]
    partner = criar_parceiro(client, headers, type=partner_type)
    contract = criar_contrato(client, headers, partner["id"], type=transaction_type)
    item = criar_transacao(client, headers, categoria(client, headers, category_name)["id"],
                          type=transaction_type, amount=amount, contract_id=contract["id"])
    assert item["contract_id"] == contract["id"]
    assert item["partner_id"] == partner["id"]
    for path in [f"partners/{partner['id']}", f"contracts/{contract['id']}"]:
        summary = sucesso(client.get(f"{PREFIX}/{path}/financial-summary", headers=headers))
        assert dinheiro(summary["total_income"]) == Decimal(received)
        assert dinheiro(summary["total_expenses"]) == Decimal(paid)
        assert dinheiro(summary["received"]) == Decimal(received)
        assert dinheiro(summary["paid"]) == Decimal(paid)
        assert dinheiro(summary["balance"]) == Decimal(received) - Decimal(paid)
        assert dinheiro(summary["expected_amount"]) == Decimal("1000.00")
        assert dinheiro(summary["outstanding_amount"]) == Decimal("1000.00") - Decimal(amount)
    for key, value in [("contract_id", contract["id"]), ("partner_id", partner["id"])]:
        listed = sucesso(client.get(f"{PREFIX}/transactions", headers=headers, params={key: value}))
        assert [row["id"] for row in listed] == [item["id"]]


@pytest.mark.parametrize(("partner_type", "transaction_type", "category_name"), [
    ("CLIENT", "EXPENSE", "Alimentação"), ("SUPPLIER", "INCOME", "Serviços"),
])
def test_tipo_da_transacao_deve_respeitar_parceiro(client, cnpj, partner_type, transaction_type, category_name):
    headers = cnpj["headers"]
    partner = criar_parceiro(client, headers, type=partner_type)
    response = client.post(f"{PREFIX}/transactions", headers=headers, json={
        "description": "Vínculo inválido", "amount": "10.00", "date": "2026-09-07",
        "type": transaction_type, "category_id": categoria(client, headers, category_name)["id"],
        "partner_id": partner["id"],
    })
    erro(response, 400)


def test_parceiro_explicito_deve_coincidir_com_o_contrato(client, cnpj):
    headers = cnpj["headers"]
    owner = criar_parceiro(client, headers, name="Titular")
    other = criar_parceiro(client, headers, name="Outro cliente")
    contract = criar_contrato(client, headers, owner["id"])
    category_id = categoria(client, headers, "Serviços")["id"]
    erro(client.post(f"{PREFIX}/transactions", headers=headers, json={
        "description": "Parceiro divergente", "amount": "10.00", "date": "2026-09-07",
        "type": "INCOME", "category_id": category_id,
        "partner_id": other["id"], "contract_id": contract["id"],
    }), 400)
    item = criar_transacao(client, headers, category_id, type="INCOME", contract_id=contract["id"])
    erro(client.put(f"{PREFIX}/transactions/{item['id']}", headers=headers,
                    json={"partner_id": other["id"]}), 400)
    stored = sucesso(client.get(f"{PREFIX}/transactions/{item['id']}", headers=headers))
    assert stored["partner_id"] == owner["id"]


def test_contrato_deve_respeitar_tipo_de_parceiro(client, cnpj):
    headers = cnpj["headers"]
    supplier = criar_parceiro(client, headers, type="SUPPLIER")
    erro(client.post(f"{PREFIX}/contracts", headers=headers, json={
        "title": "Tipo incompatível", "partner_id": supplier["id"], "type": "INCOME",
        "expected_amount": "100.00", "start_date": "2026-09-01",
    }), 400)


def test_editar_parceiro_ou_contrato_nao_pode_invalidar_transacao_existente(client, cnpj):
    headers = cnpj["headers"]
    partner = criar_parceiro(client, headers)
    other = criar_parceiro(client, headers, name="Outro cliente")
    contract = criar_contrato(client, headers, partner["id"])
    criar_transacao(client, headers, categoria(client, headers, "Serviços")["id"],
                    type="INCOME", contract_id=contract["id"])
    erro(client.put(f"{PREFIX}/partners/{partner['id']}", headers=headers, json={"type": "SUPPLIER"}), 400)
    erro(client.put(f"{PREFIX}/contracts/{contract['id']}", headers=headers, json={"partner_id": other["id"]}), 400)


def test_datas_do_contrato_sao_validadas_tambem_na_edicao_parcial(client, cnpj):
    headers = cnpj["headers"]
    partner = criar_parceiro(client, headers)
    payload = {
        "title": "Período inválido", "partner_id": partner["id"], "type": "INCOME",
        "expected_amount": "100.00", "start_date": "2026-09-07", "end_date": "2026-09-06",
    }
    erro(client.post(f"{PREFIX}/contracts", headers=headers, json=payload), 422)
    contract = criar_contrato(client, headers, partner["id"])
    erro(client.put(f"{PREFIX}/contracts/{contract['id']}", headers=headers,
                    json={"end_date": "2026-08-31"}), 422)

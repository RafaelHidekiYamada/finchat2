"""Isolamento entre titulares, inclusive durante edição de vínculos."""

import pytest

from tests.helpers import (
    PREFIX, categoria, criar_conta, criar_contrato, criar_parceiro, criar_transacao, erro, sucesso,
)


@pytest.mark.parametrize("resource", ["bank-accounts", "categories", "transactions", "partners", "contracts"])
def test_recurso_de_outro_usuario_nao_pode_ser_lido_editado_ou_excluido(client, cnpj, user_factory, resource):
    owner = cnpj["headers"]
    intruder = user_factory("CNPJ")["headers"]
    if resource == "bank-accounts":
        item = criar_conta(client, owner)
        changes = {"nickname": "Alteração indevida"}
    elif resource == "categories":
        item = categoria(client, owner)
        changes = {"name": "Alteração indevida"}
    elif resource == "transactions":
        item = criar_transacao(client, owner, categoria(client, owner)["id"])
        changes = {"description": "Alteração indevida"}
    elif resource == "partners":
        item = criar_parceiro(client, owner)
        changes = {"name": "Alteração indevida"}
    else:
        partner = criar_parceiro(client, owner)
        item = criar_contrato(client, owner, partner["id"])
        changes = {"title": "Alteração indevida"}
    path = f"{PREFIX}/{resource}/{item['id']}"
    erro(client.get(path, headers=intruder), 404)
    erro(client.put(path, headers=intruder, json=changes), 404)
    erro(client.delete(path, headers=intruder), 404)
    assert sucesso(client.get(path, headers=owner))["id"] == item["id"]
    assert item["id"] not in {row["id"] for row in sucesso(client.get(f"{PREFIX}/{resource}", headers=intruder))}
    if resource in {"partners", "contracts"}:
        erro(client.get(f"{path}/financial-summary", headers=intruder), 404)
    if resource == "bank-accounts":
        erro(client.get(f"{path}/balance", headers=intruder), 404)


@pytest.mark.parametrize("foreign_key", ["category_id", "bank_account_id", "partner_id", "contract_id"])
def test_nao_pode_vincular_transacao_a_recurso_de_outro_usuario(client, cnpj, user_factory, foreign_key):
    owner = cnpj["headers"]
    other = user_factory("CNPJ")["headers"]
    own_category = categoria(client, owner, "Serviços")["id"]
    if foreign_key == "category_id":
        foreign = categoria(client, other, "Serviços")
    elif foreign_key == "bank_account_id":
        foreign = criar_conta(client, other)
    elif foreign_key == "partner_id":
        foreign = criar_parceiro(client, other)
    else:
        partner = criar_parceiro(client, other)
        foreign = criar_contrato(client, other, partner["id"])
    payload = {
        "description": "Vínculo de outro titular", "amount": "10.00", "date": "2026-09-07",
        "type": "INCOME", "category_id": own_category, foreign_key: foreign["id"],
    }
    erro(client.post(f"{PREFIX}/transactions", headers=owner, json=payload), 404)
    item = criar_transacao(client, owner, own_category, type="INCOME")
    erro(client.put(f"{PREFIX}/transactions/{item['id']}", headers=owner,
                    json={foreign_key: foreign["id"]}), 404)
    unchanged = sucesso(client.get(f"{PREFIX}/transactions/{item['id']}", headers=owner))
    assert unchanged[foreign_key] == (own_category if foreign_key == "category_id" else None)


def test_contrato_nao_pode_usar_parceiro_de_outro_usuario(client, cnpj, user_factory):
    owner = cnpj["headers"]
    other = user_factory("CNPJ")["headers"]
    partner = criar_parceiro(client, other)
    erro(client.post(f"{PREFIX}/contracts", headers=owner, json={
        "title": "Vínculo indevido", "type": "INCOME", "partner_id": partner["id"],
        "expected_amount": "10.00", "start_date": "2026-09-01",
    }), 404)

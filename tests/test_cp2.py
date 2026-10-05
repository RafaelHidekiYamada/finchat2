"""Critérios de aceite do CP2: dashboard, paginação, banco e IA."""

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import inspect

from app.api.dependencies import get_financial_analysis_provider
from app.integrations.llm_provider import (
    FinancialAnalysisResult,
    OllamaFinancialAnalysisProvider,
    ResilientFinancialAnalysisProvider,
    deterministic_analysis,
)
from app.main import app
from app.schemas import FinancialAnalysisContent
from tests.helpers import (
    PREFIX,
    categoria,
    criar_conta,
    criar_contrato,
    criar_parceiro,
    criar_transacao,
    dinheiro,
    erro,
    sucesso,
)


def test_dashboard_consolida_dados_reais_e_isola_usuarios(client, cpf, user_factory):
    headers = cpf["headers"]
    other = user_factory("CPF")
    account = criar_conta(client, headers, initial_balance="100.00")
    food = categoria(client, headers)["id"]
    salary = categoria(client, headers, "Salário")["id"]
    criar_transacao(client, headers, salary, type="INCOME", amount="500.00", date="2026-09-02", bank_account_id=account["id"])
    criar_transacao(client, headers, food, amount="125.25", date="2026-09-03", bank_account_id=account["id"])
    criar_transacao(client, other["headers"], categoria(client, other["headers"])["id"], amount="999.00", date="2026-09-03")

    dashboard = sucesso(client.get(f"{PREFIX}/dashboard/overview", headers=headers, params={"start_date": "2026-09-01", "end_date": "2026-09-30"}))
    assert dinheiro(dashboard["total_income"]) == Decimal("500.00")
    assert dinheiro(dashboard["total_expenses"]) == Decimal("125.25")
    assert dinheiro(dashboard["net_result"]) == Decimal("374.75")
    assert dinheiro(dashboard["consolidated_balance"]) == Decimal("474.75")
    assert dinheiro(dashboard["bank_accounts"][0]["balance"]) == Decimal("474.75")
    assert [row["month"] for row in dashboard["monthly_flow"]] == ["2026-09"]
    assert len(dashboard["latest_transactions"]) == 2
    assert dashboard["company"] is None


def test_transacoes_cp2_paginam_filtram_e_ordenam(client, cpf):
    headers = cpf["headers"]
    food = categoria(client, headers)["id"]
    for index, amount in enumerate(("10.00", "30.00", "20.00"), start=1):
        criar_transacao(client, headers, food, amount=amount, date=f"2026-09-0{index}", description=f"Item {index}")

    response = client.get(f"{PREFIX}/transactions", headers=headers, params={
        "page": 2, "page_size": 1, "start_date": "2026-09-01", "end_date": "2026-09-30",
        "type": "EXPENSE", "category_id": food, "sort_by": "amount", "order": "desc",
    })
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"data", "meta"}
    assert body["meta"] == {"page": 2, "page_size": 1, "total": 3, "total_pages": 3}
    assert dinheiro(body["data"][0]["amount"]) == Decimal("20.00")
    erro(client.get(f"{PREFIX}/transactions", headers=headers, params={"page_size": 101}), 422)


def test_dashboard_cnpj_inclui_contratos_parceiros_e_vencimentos(client, cnpj):
    headers = cnpj["headers"]
    partner = criar_parceiro(client, headers)
    due = date.today() + timedelta(days=10)
    contract = criar_contrato(client, headers, partner["id"], start_date=date.today().isoformat(), end_date=due.isoformat())
    criar_transacao(client, headers, categoria(client, headers, "Serviços")["id"], type="INCOME", amount="250.00", date=date.today().isoformat(), partner_id=partner["id"], contract_id=contract["id"])
    dashboard = sucesso(client.get(f"{PREFIX}/dashboard/overview", headers=headers, params={"start_date": date.today().isoformat(), "end_date": date.today().isoformat()}))
    company = dashboard["company"]
    assert company["active_contracts"] == 1
    assert dinheiro(company["received"]) == Decimal("250.00")
    assert company["contracts_due_soon"][0]["contract_id"] == contract["id"]
    assert company["top_partners"][0]["partner_id"] == partner["id"]


def test_indices_cp2_e_unicidade_de_parceiro(db_session, client, cnpj):
    inspector = inspect(db_session.get_bind())
    transaction_indexes = {item["name"] for item in inspector.get_indexes("transactions")}
    contract_indexes = {item["name"] for item in inspector.get_indexes("contracts")}
    assert "ix_transactions_user_date" in transaction_indexes
    assert "ix_transactions_user_account_category" in transaction_indexes
    assert "ix_contracts_user_status" in contract_indexes

    headers = cnpj["headers"]
    criar_parceiro(client, headers, name="Cliente A", document="52998224725", email="financeiro@example.com")
    erro(client.post(f"{PREFIX}/partners", headers=headers, json={"name": "Cliente B", "type": "CLIENT", "document": "52998224725"}), 409)


class CapturingProvider:
    def __init__(self):
        self.payload = None

    def analyze(self, financial_context):
        self.payload = financial_context
        return FinancialAnalysisResult(
            content=FinancialAnalysisContent(
                financial_summary="Situação equilibrada no período.",
                positive_points=["Receitas superiores às despesas."],
                attention_points=[],
                recommendations=["Mantenha o acompanhamento mensal."],
                alerts=[],
                data_quality_notes=[],
                disclaimer="A análise é educacional e não representa recomendação de investimento.",
            ),
            source="ollama",
            fallback_used=False,
        )


def test_llm_recebe_apenas_agregados_e_responde_schema(client, cpf):
    headers = cpf["headers"]
    criar_transacao(client, headers, categoria(client, headers)["id"], amount="40.00", date="2026-09-10")
    provider = CapturingProvider()
    app.dependency_overrides[get_financial_analysis_provider] = lambda: provider
    try:
        analysis = sucesso(client.post(f"{PREFIX}/ai/financial-analysis", headers=headers, json={"start_date": "2026-09-01", "end_date": "2026-09-30"}))
    finally:
        app.dependency_overrides.pop(get_financial_analysis_provider, None)
    serialized = str(provider.payload).lower()
    for forbidden in (cpf["payload"]["document"], cpf["payload"]["email"], cpf["payload"]["whatsapp"], "password", "token", "external_id", "bank_account"):
        assert forbidden.lower() not in serialized
    assert set(provider.payload) >= {"profile_type", "period", "total_income", "total_expenses", "consolidated_balance", "expenses_by_category", "monthly_flow"}
    assert analysis["period"] == {"start_date": "2026-09-01", "end_date": "2026-09-30"}
    assert analysis["financial_summary"]
    assert analysis["generated_at"]
    assert analysis["analysis_source"] == "ollama"
    assert analysis["fallback_used"] is False
    assert "investimento" in analysis["disclaimer"]


def test_ollama_indisponivel_usa_fallback_sem_quebrar_endpoint(client, cpf, monkeypatch):
    headers = cpf["headers"]
    criar_transacao(client, headers, categoria(client, headers)["id"], date="2026-09-10")
    monkeypatch.setattr("app.integrations.llm_provider.httpx.post", lambda *_args, **_kwargs: (_ for _ in ()).throw(TimeoutError("offline")))
    analysis = sucesso(client.post(f"{PREFIX}/ai/financial-analysis", headers=headers, json={"start_date": "2026-09-01", "end_date": "2026-09-30"}))
    assert analysis["analysis_source"] == "deterministic"
    assert analysis["fallback_used"] is True
    assert analysis["financial_summary"]
    assert analysis["recommendations"]


def test_ollama_recebe_schema_e_resposta_estruturada(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            content = FinancialAnalysisContent(
                financial_summary="Resumo local validado.",
                positive_points=["Saldo não negativo."],
                attention_points=[],
                recommendations=["Mantenha o controle mensal."],
                alerts=[],
                data_quality_notes=[],
                disclaimer="A análise é educacional e não representa recomendação de investimento.",
            )
            return {"message": {"content": content.model_dump_json()}}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs["json"]
        return Response()

    monkeypatch.setattr("app.integrations.llm_provider.httpx.post", fake_post)
    settings = SimpleNamespace(ollama_base_url="http://localhost:11434", ollama_model="gemma3:4b", ollama_timeout_seconds=30)
    outcome = OllamaFinancialAnalysisProvider(settings).analyze({"total_income": "100.00"})
    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["json"]["model"] == "gemma3:4b"
    assert captured["json"]["stream"] is False
    assert captured["json"]["format"]["type"] == "object"
    assert outcome.source == "ollama"
    assert outcome.content.financial_summary == "Resumo local validado."


def test_timeout_do_ollama_ativa_regras_deterministicas(monkeypatch):
    monkeypatch.setattr("app.integrations.llm_provider.httpx.post", lambda *_args, **_kwargs: (_ for _ in ()).throw(TimeoutError("detalhe técnico")))
    settings = SimpleNamespace(llm_enabled=True, ollama_base_url="http://localhost:11434", ollama_model="gemma3:4b", ollama_timeout_seconds=1)
    outcome = ResilientFinancialAnalysisProvider(settings).analyze({
        "total_income": "100.00", "total_expenses": "40.00", "consolidated_balance": "60.00", "net_result": "60.00"
    })
    assert outcome.source == "deterministic"
    assert outcome.fallback_used is True
    assert "superávit" in outcome.content.financial_summary


def test_regras_deterministicas_detectam_deficit_concentracao_e_tendencia():
    analysis = deterministic_analysis({
        "total_income": "100.00",
        "total_expenses": "150.00",
        "consolidated_balance": "-25.00",
        "net_result": "-50.00",
        "expenses_by_category": [{"category": "Moradia", "total": "100.00"}],
        "monthly_flow": [
            {"month": "2026-08", "income": "100.00", "expenses": "50.00"},
            {"month": "2026-09", "income": "100.00", "expenses": "100.00"},
        ],
        "alerts": ["As despesas do período estão acima das receitas."],
    })
    combined = " ".join(analysis.attention_points).lower()
    assert "déficit" in analysis.financial_summary
    assert "negativo" in combined
    assert "concentra" in combined
    assert "cresceram" in combined


def test_llm_sem_movimentacoes_informa_dados_insuficientes_sem_chamar_provider(client, cpf):
    class MustNotRun:
        def analyze(self, _context):
            raise AssertionError("provider não deveria ser chamado")

    app.dependency_overrides[get_financial_analysis_provider] = lambda: MustNotRun()
    try:
        analysis = sucesso(client.post(f"{PREFIX}/ai/financial-analysis", headers=cpf["headers"], json={"start_date": "2026-09-01", "end_date": "2026-09-30"}))
    finally:
        app.dependency_overrides.pop(get_financial_analysis_provider, None)
    assert "Não há movimentações suficientes" in analysis["financial_summary"]
    assert analysis["data_quality_notes"]
    assert analysis["analysis_source"] == "deterministic"
    assert analysis["fallback_used"] is False

import json
import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal, Protocol

import httpx

from app.core.config import Settings
from app.schemas import FinancialAnalysisContent

logger = logging.getLogger("finchat")

DISCLAIMER = "A análise é educacional e não representa recomendação de investimento."
AnalysisSource = Literal["ollama", "deterministic"]


@dataclass(frozen=True)
class FinancialAnalysisResult:
    content: FinancialAnalysisContent
    source: AnalysisSource
    fallback_used: bool


class FinancialAnalysisProvider(Protocol):
    def analyze(self, financial_context: dict) -> FinancialAnalysisResult: ...


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _brl(value: Decimal) -> str:
    formatted = f"{value:,.2f}"
    return f"R$ {formatted.replace(',', '_').replace('.', ',').replace('_', '.')}"


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def deterministic_analysis(financial_context: dict) -> FinancialAnalysisContent:
    """Produz uma análise útil e reproduzível sem depender de serviço externo."""
    income = _decimal(financial_context.get("total_income"))
    expenses = _decimal(financial_context.get("total_expenses"))
    balance = _decimal(financial_context.get("consolidated_balance"))
    net = _decimal(financial_context.get("net_result", income - expenses))
    categories = financial_context.get("expenses_by_category") or []
    monthly_flow = financial_context.get("monthly_flow") or []

    positive: list[str] = []
    attention: list[str] = []
    recommendations: list[str] = []
    alerts = list(financial_context.get("alerts") or [])
    quality = ["Análise calculada com dados agregados; nenhuma transação ou identidade individual foi utilizada."]

    if net > 0:
        summary = f"O período terminou com superávit de {_brl(net)}, com receitas acima das despesas."
        positive.append(f"Resultado positivo de {_brl(net)} no período.")
        recommendations.append("Defina uma destinação planejada para parte do excedente e acompanhe sua execução nos próximos meses.")
    elif net < 0:
        summary = f"O período terminou com déficit de {_brl(abs(net))}, pois as despesas superaram as receitas."
        attention.append(f"As despesas excederam as receitas em {_brl(abs(net))}.")
        recommendations.append("Revise primeiro as maiores categorias de despesa e estabeleça um limite mensal realista.")
    else:
        summary = "O período terminou em equilíbrio, com receitas e despesas no mesmo valor."
        attention.append("Não houve margem financeira positiva no período.")
        recommendations.append("Crie uma pequena margem entre receitas e despesas para absorver imprevistos.")

    if balance >= 0:
        positive.append(f"O saldo consolidado permaneceu não negativo em {_brl(balance)}.")
    else:
        attention.append(f"O saldo consolidado está negativo em {_brl(abs(balance))}.")
        recommendations.append("Priorize a regularização do saldo negativo e evite novas despesas não essenciais enquanto ele persistir.")

    if income > 0:
        expense_ratio = expenses / income
        if expense_ratio <= Decimal("0.70"):
            positive.append(f"As despesas consumiram {expense_ratio:.0%} das receitas, mantendo margem no período.")
        elif expense_ratio >= Decimal("0.90"):
            attention.append(f"As despesas consumiram {expense_ratio:.0%} das receitas do período.")
            recommendations.append("Acompanhe semanalmente a relação entre despesas e receitas até recuperar uma margem segura.")
    elif expenses > 0:
        attention.append("Há despesas registradas sem receitas no período selecionado.")
        recommendations.append("Confirme se todas as receitas do período foram registradas e revise a sustentabilidade das despesas atuais.")

    if categories and expenses > 0:
        top = max(categories, key=lambda item: _decimal(item.get("total")))
        top_total = _decimal(top.get("total"))
        top_share = top_total / expenses if expenses else Decimal("0")
        if top_share >= Decimal("0.50"):
            attention.append(
                f"A categoria {top.get('category', 'principal')} concentra {top_share:.0%} das despesas ({_brl(top_total)})."
            )
            recommendations.append("Detalhe e revise a categoria com maior concentração para identificar ajustes possíveis.")
    elif expenses > 0:
        quality.append("Não foi possível avaliar a concentração das despesas porque não há categorias agregadas disponíveis.")

    if len(monthly_flow) >= 2:
        previous = _decimal(monthly_flow[-2].get("expenses"))
        current = _decimal(monthly_flow[-1].get("expenses"))
        if previous > 0:
            change = (current - previous) / previous
            if change >= Decimal("0.20"):
                attention.append(f"As despesas do último mês cresceram {change:.0%} em relação ao mês anterior.")
                recommendations.append("Compare os dois últimos meses e investigue os gastos que explicam o aumento recente.")
            elif change <= Decimal("-0.20"):
                positive.append(f"As despesas do último mês caíram {abs(change):.0%} em relação ao mês anterior.")
    else:
        quality.append("O período possui menos de dois meses; por isso, a tendência mensal não foi avaliada.")

    company = financial_context.get("company_summary")
    if company and int(company.get("contracts_due_soon_count", 0)) > 0:
        count = int(company["contracts_due_soon_count"])
        attention.append(f"Há {count} contrato(s) com vencimento próximo.")
        recommendations.append("Revise prazos, entregas e recebimentos dos contratos com vencimento próximo.")

    return FinancialAnalysisContent(
        financial_summary=summary,
        positive_points=_unique(positive),
        attention_points=_unique(attention),
        recommendations=_unique(recommendations),
        alerts=_unique(alerts),
        data_quality_notes=_unique(quality),
        disclaimer=DISCLAIMER,
    )


class DeterministicFinancialAnalysisProvider:
    def analyze(self, financial_context: dict) -> FinancialAnalysisResult:
        return FinancialAnalysisResult(
            content=deterministic_analysis(financial_context),
            source="deterministic",
            fallback_used=False,
        )


class OllamaFinancialAnalysisProvider:
    def __init__(self, settings: Settings):
        self.settings = settings

    def analyze(self, financial_context: dict) -> FinancialAnalysisResult:
        system = (
            "Você é o módulo de análise financeira educacional do FinChat. "
            "Analise somente os agregados fornecidos, não invente números e não recomende compra, "
            "venda ou investimento. Seja objetivo, prudente e use português do Brasil. "
            "Preencha todos os campos como texto simples: não use Markdown, asteriscos, títulos ou listas dentro de uma string. "
            "Limite financial_summary a três frases e cada lista a no máximo três itens curtos, sem repetir informações. "
            f"O campo disclaimer deve ser exatamente: {DISCLAIMER}"
        )
        response = httpx.post(
            f"{self.settings.ollama_base_url}/api/chat",
            timeout=self.settings.ollama_timeout_seconds,
            json={
                "model": self.settings.ollama_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(financial_context, ensure_ascii=False)},
                ],
                "stream": False,
                "format": FinancialAnalysisContent.model_json_schema(),
                "options": {"temperature": 0},
            },
        )
        response.raise_for_status()
        payload = response.json()
        content = FinancialAnalysisContent.model_validate_json(payload["message"]["content"])
        return FinancialAnalysisResult(content=content, source="ollama", fallback_used=False)


class ResilientFinancialAnalysisProvider:
    """Tenta Ollama e garante resposta determinística diante de qualquer indisponibilidade."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.ollama = OllamaFinancialAnalysisProvider(settings)
        self.fallback = DeterministicFinancialAnalysisProvider()

    def analyze(self, financial_context: dict) -> FinancialAnalysisResult:
        if not self.settings.llm_enabled:
            return self.fallback.analyze(financial_context)
        try:
            return self.ollama.analyze(financial_context)
        except Exception as exc:
            logger.warning("Ollama indisponível; usando regras determinísticas: %s", type(exc).__name__)
            fallback = self.fallback.analyze(financial_context)
            return FinancialAnalysisResult(
                content=fallback.content,
                source="deterministic",
                fallback_used=True,
            )


def insufficient_data_analysis() -> FinancialAnalysisContent:
    return FinancialAnalysisContent(
        financial_summary="Não há movimentações suficientes no período para uma análise financeira útil.",
        positive_points=[],
        attention_points=["O período não contém receitas ou despesas registradas."],
        recommendations=["Registre suas receitas e despesas para receber uma análise baseada em dados."],
        alerts=[],
        data_quality_notes=["A análise foi limitada pela ausência de movimentações no período."],
        disclaimer=DISCLAIMER,
    )

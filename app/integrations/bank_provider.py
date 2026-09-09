"""Contrato para futura Open Finance. O único provedor do CP1 é fictício."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from app.models import TransactionType


@dataclass(frozen=True)
class BankMovement:
    external_id: str
    description: str
    amount: Decimal
    date: date
    type: TransactionType
    category_name: str


class BankProvider(Protocol):
    def fetch_transactions(self, external_id: str, reference_date: date) -> list[BankMovement]: ...


class SimulatedBankProvider:
    """Não acessa banco real, internet, credenciais ou consentimento real."""

    def fetch_transactions(self, external_id: str, reference_date: date) -> list[BankMovement]:
        entries = (
            ("entrada", "Recebimento fictício CP1", Decimal("1500.00"), TransactionType.INCOME, "Serviços"),
            ("alimentacao", "Alimentação fictícia CP1", Decimal("50.00"), TransactionType.EXPENSE, "Alimentação"),
            ("transporte", "Transporte fictício CP1", Decimal("25.00"), TransactionType.EXPENSE, "Transporte"),
        )
        return [BankMovement(f"{external_id}:{key}", description, amount, reference_date, kind, category) for key, description, amount, kind, category in entries]

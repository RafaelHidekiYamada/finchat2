"""Interpretação local de texto; não envia mensagens à WhatsApp Cloud API."""

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.strip().casefold())
    return " ".join("".join(char for char in normalized if not unicodedata.combining(char)).split())


@dataclass(frozen=True)
class ParsedCommand:
    action: str
    amount: Decimal | None = None
    category: str | None = None


class WhatsAppProvider(Protocol):
    def interpret(self, command: str) -> ParsedCommand: ...


class SimulatedWhatsAppProvider:
    """Parser determinístico do CP1, sem IA externa ou automação do WhatsApp."""

    def interpret(self, command: str) -> ParsedCommand:
        text = normalize_text(command)
        if text == "saldo":
            return ParsedCommand("BALANCE")
        if text == "resumo do mes":
            return ParsedCommand("MONTHLY_SUMMARY")
        match = re.fullmatch(r"(gastei|recebi)\s+(?:r\$\s*)?([0-9]+(?:[.,][0-9]{1,2})?)\s+(?:em|por)\s+(.+)", text)
        if match:
            verb, value, category = match.groups()
            return ParsedCommand("EXPENSE" if verb == "gastei" else "INCOME", Decimal(value.replace(",", ".")), category)
        return ParsedCommand("UNKNOWN")

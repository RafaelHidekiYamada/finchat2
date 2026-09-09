import calendar
from datetime import date, datetime, timezone
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.integrations.bank_provider import BankProvider, SimulatedBankProvider
from app.integrations.whatsapp_provider import SimulatedWhatsAppProvider, WhatsAppProvider, normalize_text
from app.models import BankAccount, BankConnection, Category, ChatCommandLog, ConnectionStatus, Origin, ReconciliationStatus, Transaction, TransactionType, User
from app.repositories.finance import owned
from app.schemas import TransactionCreate
from app.services.auth import ensure_default_categories
from app.services.finance import create_resource, summary


def create_connection(db: Session, user: User, bank_account_id: int):
    account = owned(db, BankAccount, user.id, bank_account_id)
    if db.scalar(select(BankConnection.id).where(BankConnection.bank_account_id == account.id)):
        raise AppError(409, "CONFLICT", "Esta conta já possui conexão simulada.")
    connection = BankConnection(user_id=user.id, bank_account_id=account.id, institution=account.institution, status=ConnectionStatus.ACTIVE, consent_at=datetime.now(timezone.utc), external_id=f"cp1-sim-{uuid4().hex}")
    db.add(connection)
    db.flush()
    return connection


def sync_connection(db: Session, user: User, connection_id: int, provider: BankProvider | None = None):
    connection = owned(db, BankConnection, user.id, connection_id)
    if connection.status != ConnectionStatus.ACTIVE:
        raise AppError(400, "INACTIVE_CONNECTION", "Conexão simulada não está ativa.")
    provider = provider or SimulatedBankProvider()
    ensure_default_categories(db, user.id)
    categories = {(category.name, category.type): category.id for category in db.scalars(select(Category).where(Category.user_id == user.id))}
    imported = []
    for movement in provider.fetch_transactions(connection.external_id, connection.consent_at.date()):
        exists = db.scalar(select(Transaction.id).where(Transaction.user_id == user.id, Transaction.bank_account_id == connection.bank_account_id, Transaction.external_id == movement.external_id))
        if exists:
            continue
        payload = TransactionCreate(description=movement.description, amount=movement.amount, date=movement.date, type=movement.type, category_id=categories[movement.category_name, movement.type], bank_account_id=connection.bank_account_id, origin=Origin.BANK, reconciliation_status=ReconciliationStatus.RECONCILED)
        transaction = create_resource(db, user, Transaction, payload)
        transaction.external_id = movement.external_id
        db.flush()
        imported.append(transaction)
    connection.last_synced_at = datetime.now(timezone.utc)
    db.flush()
    return {"imported_count": len(imported), "transactions": imported}


def execute_command(db: Session, user: User, command: str, provider: WhatsAppProvider | None = None):
    parsed = (provider or SimulatedWhatsAppProvider()).interpret(command)
    result = {"action": parsed.action}
    if parsed.action in ("BALANCE", "MONTHLY_SUMMARY"):
        filters = {}
        if parsed.action == "MONTHLY_SUMMARY":
            today = date.today()
            filters = {"start_date": today.replace(day=1), "end_date": today.replace(day=calendar.monthrange(today.year, today.month)[1])}
        report = summary(db, user, filters)
        result.update(summary=report, reply=f"Saldo {'do resumo mensal' if filters else 'consolidado'}: R$ {report['balance']:.2f}. Receitas: R$ {report['total_income']:.2f}; despesas: R$ {report['total_expenses']:.2f}.")
    elif parsed.action in ("INCOME", "EXPENSE"):
        transaction_type = TransactionType(parsed.action)
        alias = {"servico": "servicos", "salario": "salario"}
        category_name = alias.get(parsed.category, parsed.category)
        category = next((item for item in db.scalars(select(Category).where(Category.user_id == user.id, Category.type == transaction_type)) if normalize_text(item.name) == category_name), None)
        if category is None:
            raise AppError(400, "CATEGORY_NOT_FOUND", "Categoria não encontrada para este tipo. Cadastre a categoria e tente novamente.")
        try:
            payload = TransactionCreate(description=command.strip(), amount=parsed.amount, date=date.today(), type=transaction_type, category_id=category.id, origin=Origin.CASH)
        except ValidationError:
            raise AppError(400, "INVALID_AMOUNT", "Informe um valor positivo com até duas casas decimais dentro do limite monetário.") from None
        transaction = create_resource(db, user, Transaction, payload)
        result.update(transaction=transaction, reply=f"{'Receita' if transaction_type == TransactionType.INCOME else 'Despesa'} de R$ {transaction.amount:.2f} registrada em {category.name}, em dinheiro.")
    else:
        raise AppError(400, "UNKNOWN_COMMAND", "Comando não reconhecido. Exemplos: saldo; resumo do mês; gastei 50 em alimentação; recebi 200 por serviço.")
    db.add(ChatCommandLog(user_id=user.id, command=command.strip(), action=parsed.action, response_message=result["reply"]))
    db.flush()
    return result

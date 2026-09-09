from decimal import Decimal

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_company
from app.core.exceptions import AppError
from app.models import BankAccount, BankConnection, Category, Contract, Origin, Partner, PartnerType, Transaction, TransactionType, User
from app.repositories.finance import owned, transaction_query
from app.schemas import BankAccountCreate, CategoryCreate, ContractCreate, PartnerCreate, TransactionCreate

CREATE_SCHEMAS = {BankAccount: BankAccountCreate, Category: CategoryCreate, Transaction: TransactionCreate, Partner: PartnerCreate, Contract: ContractCreate}
ZERO = Decimal("0.00")


def invalid(message: str):
    raise AppError(400, "BUSINESS_RULE_ERROR", message)


def assert_partner_type(partner: Partner, transaction_type: TransactionType):
    expected = TransactionType.INCOME if partner.type == PartnerType.CLIENT else TransactionType.EXPENSE
    if transaction_type != expected:
        invalid("Clientes recebem receitas; fornecedores recebem despesas.")


def validate_values(db: Session, user: User, model, values: dict, record=None):
    if model in (Partner, Contract):
        require_company(user)
    if model is Category:
        duplicate = select(Category.id).where(Category.user_id == user.id, func.lower(Category.name) == values["name"].lower(), Category.type == values["type"])
        if record:
            duplicate = duplicate.where(Category.id != record.id)
        if db.scalar(duplicate):
            raise AppError(409, "CONFLICT", "Categoria com este nome e tipo já existe.")
        if record and values["type"] != record.type and db.scalar(select(Transaction.id).where(Transaction.category_id == record.id).limit(1)):
            invalid("Não é possível alterar o tipo de uma categoria utilizada.")
    elif model is Partner:
        if record and values["type"] != record.type:
            used = db.scalar(select(Transaction.id).where(Transaction.partner_id == record.id).limit(1)) or db.scalar(select(Contract.id).where(Contract.partner_id == record.id).limit(1))
            if used:
                invalid("Não é possível alterar o tipo de um parceiro utilizado.")
    elif model is Contract:
        partner = owned(db, Partner, user.id, values["partner_id"])
        assert_partner_type(partner, values["type"])
        if record and (values["partner_id"] != record.partner_id or values["type"] != record.type):
            if db.scalar(select(Transaction.id).where(Transaction.contract_id == record.id).limit(1)):
                invalid("Não é possível alterar parceiro ou tipo de um contrato com transações.")
    elif model is Transaction:
        category = owned(db, Category, user.id, values["category_id"])
        if category.type != values["type"]:
            invalid("Categoria incompatível com o tipo da transação.")
        if values["bank_account_id"] is not None:
            owned(db, BankAccount, user.id, values["bank_account_id"])
        if values["origin"] == Origin.CASH and values["bank_account_id"] is not None:
            invalid("Movimentações em dinheiro não devem estar vinculadas a conta bancária.")
        if values["origin"] == Origin.BANK and values["bank_account_id"] is None:
            invalid("Uma movimentação bancária exige conta bancária.")
        if values["contract_id"] is not None or values["partner_id"] is not None:
            require_company(user)
        if values["contract_id"] is not None:
            contract = owned(db, Contract, user.id, values["contract_id"])
            if contract.type != values["type"]:
                invalid("Tipo da transação incompatível com o contrato.")
            if values["partner_id"] is None:
                values["partner_id"] = contract.partner_id
            elif values["partner_id"] != contract.partner_id:
                invalid("O parceiro da transação deve ser o mesmo do contrato.")
        if values["partner_id"] is not None:
            partner = owned(db, Partner, user.id, values["partner_id"])
            assert_partner_type(partner, values["type"])
        if record and record.external_id and (values["bank_account_id"] != record.bank_account_id or values["origin"] != Origin.BANK):
            invalid("Conta e origem de uma importação simulada não podem ser alteradas.")


def create_resource(db: Session, user: User, model, payload):
    values = payload.model_dump()
    validate_values(db, user, model, values)
    record = model(user_id=user.id, **values)
    db.add(record)
    db.flush()
    return record


def update_resource(db: Session, user: User, model, resource_id: int, payload):
    if model in (Partner, Contract):
        require_company(user)
    record = owned(db, model, user.id, resource_id)
    schema = CREATE_SCHEMAS[model]
    values = {key: getattr(record, key) for key in schema.model_fields}
    values.update(payload.model_dump(exclude_unset=True))
    try:
        values = schema.model_validate(values).model_dump()
    except ValidationError as exc:
        details = [{"field": ".".join(map(str, e["loc"])), "message": "Valor inválido para o campo."} for e in exc.errors()]
        raise AppError(422, "VALIDATION_ERROR", "Atualização inválida. Verifique os campos.", details) from None
    validate_values(db, user, model, values, record)
    for key, value in values.items():
        setattr(record, key, value)
    if model is BankAccount:
        connection = db.scalar(select(BankConnection).where(BankConnection.bank_account_id == record.id))
        if connection:
            connection.institution = record.institution
    db.flush()
    return record


def delete_resource(db: Session, user: User, model, resource_id: int):
    if model in (Partner, Contract):
        require_company(user)
    record = owned(db, model, user.id, resource_id)
    references = {
        BankAccount: [(Transaction, "bank_account_id"), (BankConnection, "bank_account_id")],
        Category: [(Transaction, "category_id")],
        Partner: [(Transaction, "partner_id"), (Contract, "partner_id")],
        Contract: [(Transaction, "contract_id")],
    }
    for child, field in references.get(model, []):
        if db.scalar(select(child.id).where(getattr(child, field) == record.id).limit(1)):
            raise AppError(409, "RESOURCE_IN_USE", "Recurso possui vínculos. Remova as dependências antes de excluir.")
    db.delete(record)
    db.flush()


def validate_filters(db: Session, user: User, filters: dict):
    start, end = filters.get("start_date"), filters.get("end_date")
    if start and end and start > end:
        invalid("Data inicial deve ser igual ou anterior à final.")
    for field, model in (("category_id", Category), ("bank_account_id", BankAccount), ("partner_id", Partner), ("contract_id", Contract)):
        if filters.get(field) is not None:
            if model in (Partner, Contract):
                require_company(user)
            owned(db, model, user.id, filters[field])


def totals(transactions):
    income = sum((item.amount for item in transactions if item.type == TransactionType.INCOME), ZERO)
    expenses = sum((item.amount for item in transactions if item.type == TransactionType.EXPENSE), ZERO)
    return income, expenses


def summary(db: Session, user: User, filters: dict | None = None):
    filters = filters or {}
    validate_filters(db, user, filters)
    transactions = list(db.scalars(transaction_query(user.id, filters)))
    account_query = select(BankAccount).where(BankAccount.user_id == user.id)
    if filters.get("bank_account_id"):
        account_query = account_query.where(BankAccount.id == filters["bank_account_id"])
    initial = sum((account.initial_balance for account in db.scalars(account_query)), ZERO)
    income, expenses = totals(transactions)
    grouped = {}
    categories = {category.id: category for category in db.scalars(select(Category).where(Category.user_id == user.id))}
    for transaction in transactions:
        grouped[transaction.category_id] = grouped.get(transaction.category_id, ZERO) + transaction.amount
    return {"initial_balance": initial, "total_income": income, "total_expenses": expenses, "balance": initial + income - expenses, "by_category": [{"category_id": key, "category_name": categories[key].name, "type": categories[key].type, "total": grouped[key]} for key in sorted(grouped)]}


def financial_summary(db: Session, user: User, model, resource_id: int):
    require_company(user)
    record = owned(db, model, user.id, resource_id)
    field = "partner_id" if model is Partner else "contract_id"
    transactions = list(db.scalars(transaction_query(user.id, {field: resource_id})))
    income, expenses = totals(transactions)
    expected = record.expected_amount if model is Contract else sum((contract.expected_amount for contract in db.scalars(select(Contract).where(Contract.user_id == user.id, Contract.partner_id == resource_id))), ZERO)
    # Valores já recebidos/pagos são movimentações, independentemente da conciliação.
    return {"total_income": income, "total_expenses": expenses, "received": income, "paid": expenses, "balance": income - expenses, "expected_amount": expected, "outstanding_amount": max(expected - income - expenses, ZERO)}

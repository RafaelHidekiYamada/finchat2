from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import (
    BankAccount,
    Category,
    Contract,
    ContractStatus,
    Partner,
    PartnerType,
    Transaction,
    TransactionType,
    User,
    UserType,
)
from app.repositories.finance import transaction_query
from app.services.finance import ZERO, invalid


def default_period(today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    return today.replace(day=1), today


def resolve_period(start_date: date | None, end_date: date | None) -> tuple[date, date]:
    default_start, default_end = default_period()
    start, end = start_date or default_start, end_date or default_end
    if start > end:
        invalid("Data inicial deve ser igual ou anterior à final.")
    if (end - start).days > 1095:
        invalid("O período máximo para o dashboard é de três anos.")
    return start, end


def _money(value) -> Decimal:
    return (value or ZERO).quantize(Decimal("0.01"))


def _period_totals(db: Session, user_id: int, start: date, end: date) -> tuple[Decimal, Decimal]:
    row = db.execute(
        select(
            func.coalesce(func.sum(case((Transaction.type == TransactionType.INCOME, Transaction.amount), else_=0)), 0),
            func.coalesce(func.sum(case((Transaction.type == TransactionType.EXPENSE, Transaction.amount), else_=0)), 0),
        ).where(Transaction.user_id == user_id, Transaction.date.between(start, end))
    ).one()
    return _money(row[0]), _money(row[1])


def _consolidated_balance(db: Session, user_id: int, end: date) -> Decimal:
    initial = db.scalar(select(func.coalesce(func.sum(BankAccount.initial_balance), 0)).where(BankAccount.user_id == user_id))
    income, expenses = db.execute(
        select(
            func.coalesce(func.sum(case((Transaction.type == TransactionType.INCOME, Transaction.amount), else_=0)), 0),
            func.coalesce(func.sum(case((Transaction.type == TransactionType.EXPENSE, Transaction.amount), else_=0)), 0),
        ).where(Transaction.user_id == user_id, Transaction.date <= end)
    ).one()
    return _money(initial) + _money(income) - _money(expenses)


def _month_keys(start: date, end: date) -> list[str]:
    current = start.replace(day=1)
    last = end.replace(day=1)
    keys = []
    while current <= last:
        keys.append(current.strftime("%Y-%m"))
        current = date(current.year + (current.month == 12), current.month % 12 + 1, 1)
    return keys


def _monthly_flow(db: Session, user_id: int, start: date, end: date) -> list[dict]:
    records = db.execute(
        select(Transaction.date, Transaction.type, Transaction.amount).where(
            Transaction.user_id == user_id,
            Transaction.date.between(start, end),
        )
    )
    grouped = {key: {"income": ZERO, "expenses": ZERO} for key in _month_keys(start, end)}
    for occurred_at, transaction_type, amount in records:
        key = occurred_at.strftime("%Y-%m")
        grouped[key]["income" if transaction_type == TransactionType.INCOME else "expenses"] += amount
    return [{"month": key, **values} for key, values in grouped.items()]


def _expenses_by_category(db: Session, user_id: int, start: date, end: date) -> list[dict]:
    rows = db.execute(
        select(Category.id, Category.name, func.sum(Transaction.amount).label("total"))
        .join(Transaction, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.EXPENSE,
            Transaction.date.between(start, end),
        )
        .group_by(Category.id, Category.name)
        .order_by(func.sum(Transaction.amount).desc(), Category.id)
    )
    return [{"category_id": row.id, "category_name": row.name, "total": _money(row.total)} for row in rows]


def _account_balances(db: Session, user_id: int, end: date) -> list[dict]:
    rows = db.execute(
        select(
            BankAccount.id,
            BankAccount.institution,
            BankAccount.nickname,
            BankAccount.initial_balance,
            func.coalesce(func.sum(case((Transaction.type == TransactionType.INCOME, Transaction.amount), else_=0)), 0).label("income"),
            func.coalesce(func.sum(case((Transaction.type == TransactionType.EXPENSE, Transaction.amount), else_=0)), 0).label("expenses"),
        )
        .outerjoin(Transaction, (Transaction.bank_account_id == BankAccount.id) & (Transaction.date <= end))
        .where(BankAccount.user_id == user_id)
        .group_by(BankAccount.id, BankAccount.institution, BankAccount.nickname, BankAccount.initial_balance)
        .order_by(BankAccount.id)
    )
    return [
        {
            "id": row.id,
            "institution": row.institution,
            "nickname": row.nickname,
            "balance": _money(row.initial_balance) + _money(row.income) - _money(row.expenses),
        }
        for row in rows
    ]


def _partner_movements(db: Session, user_id: int, start: date, end: date) -> list[dict]:
    rows = db.execute(
        select(
            Partner.id,
            Partner.name,
            Partner.type,
            func.coalesce(func.sum(case((Transaction.type == TransactionType.INCOME, Transaction.amount), else_=0)), 0).label("income"),
            func.coalesce(func.sum(case((Transaction.type == TransactionType.EXPENSE, Transaction.amount), else_=0)), 0).label("expenses"),
        )
        .outerjoin(Transaction, (Transaction.partner_id == Partner.id) & Transaction.date.between(start, end))
        .where(Partner.user_id == user_id)
        .group_by(Partner.id, Partner.name, Partner.type)
    )
    values = [
        {
            "partner_id": row.id,
            "partner_name": row.name,
            "partner_type": row.type,
            "total_income": _money(row.income),
            "total_expenses": _money(row.expenses),
            "movement": _money(row.income) + _money(row.expenses),
        }
        for row in rows
    ]
    return sorted(values, key=lambda item: (-item["movement"], item["partner_id"]))


def _company_overview(db: Session, user_id: int, start: date, end: date) -> dict:
    income, expenses = _period_totals(db, user_id, start, end)
    partners = _partner_movements(db, user_id, start, end)
    today = date.today()
    due_limit = today + timedelta(days=30)
    due_rows = db.execute(
        select(Contract.id, Contract.title, Contract.end_date, Contract.expected_amount)
        .where(
            Contract.user_id == user_id,
            Contract.status == ContractStatus.ACTIVE,
            Contract.end_date.is_not(None),
            Contract.end_date.between(today, due_limit),
        )
        .order_by(Contract.end_date, Contract.id)
    )
    return {
        "active_contracts": db.scalar(select(func.count(Contract.id)).where(Contract.user_id == user_id, Contract.status == ContractStatus.ACTIVE)) or 0,
        "received": income,
        "paid": expenses,
        "clients": [item for item in partners if item["partner_type"] == PartnerType.CLIENT],
        "suppliers": [item for item in partners if item["partner_type"] == PartnerType.SUPPLIER],
        "contracts_due_soon": [
            {"contract_id": row.id, "title": row.title, "end_date": row.end_date, "expected_amount": _money(row.expected_amount)}
            for row in due_rows
        ],
        "top_partners": partners[:5],
    }


def dashboard_overview(db: Session, user: User, start_date: date | None, end_date: date | None) -> dict:
    start, end = resolve_period(start_date, end_date)
    income, expenses = _period_totals(db, user.id, start, end)
    balance = _consolidated_balance(db, user.id, end)
    accounts = _account_balances(db, user.id, end)
    latest = list(db.scalars(transaction_query(user.id, {"start_date": start, "end_date": end}).limit(5)))
    alerts = []
    if not latest:
        alerts.append("Ainda não há transações no período selecionado.")
    if expenses > income:
        alerts.append("As despesas do período estão acima das receitas.")
    if income > ZERO and expenses >= income * Decimal("0.90"):
        alerts.append("As despesas consumiram pelo menos 90% das receitas do período.")
    if balance < ZERO:
        alerts.append("O saldo consolidado está negativo.")
    if any(account["balance"] < ZERO for account in accounts):
        alerts.append("Há conta bancária com saldo negativo.")
    return {
        "start_date": start,
        "end_date": end,
        "consolidated_balance": balance,
        "total_income": income,
        "total_expenses": expenses,
        "net_result": income - expenses,
        "monthly_flow": _monthly_flow(db, user.id, start, end),
        "expenses_by_category": _expenses_by_category(db, user.id, start, end),
        "latest_transactions": latest,
        "alerts": alerts,
        "bank_accounts": accounts,
        "company": _company_overview(db, user.id, start, end) if user.document_type == UserType.CNPJ else None,
    }


def llm_financial_context(overview: dict, user: User) -> dict:
    """Minimiza o payload: nenhuma identidade, conta ou transação bruta sai da API."""
    company = overview["company"]
    payload = {
        "profile_type": user.document_type.value,
        "period": {"start_date": overview["start_date"].isoformat(), "end_date": overview["end_date"].isoformat()},
        "total_income": str(overview["total_income"]),
        "total_expenses": str(overview["total_expenses"]),
        "consolidated_balance": str(overview["consolidated_balance"]),
        "net_result": str(overview["net_result"]),
        "expenses_by_category": [
            {"category": item["category_name"], "total": str(item["total"])}
            for item in overview["expenses_by_category"]
        ],
        "monthly_flow": [
            {"month": item["month"], "income": str(item["income"]), "expenses": str(item["expenses"])}
            for item in overview["monthly_flow"]
        ],
        "alerts": overview["alerts"],
    }
    if company:
        payload["company_summary"] = {
            "active_contracts": company["active_contracts"],
            "received": str(company["received"]),
            "paid": str(company["paid"]),
            "client_count": len(company["clients"]),
            "supplier_count": len(company["suppliers"]),
            "contracts_due_soon_count": len(company["contracts_due_soon"]),
        }
    return payload

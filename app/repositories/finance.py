from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models import Transaction


def owned(session: Session, model, user_id: int, resource_id: int):
    record = session.scalar(select(model).where(model.id == resource_id, model.user_id == user_id))
    if record is None:
        raise AppError(404, "RESOURCE_NOT_FOUND", "Recurso não encontrado.")
    return record


def list_owned(session: Session, model, user_id: int, limit: int = 100, offset: int = 0):
    return list(session.scalars(select(model).where(model.user_id == user_id).order_by(model.id).offset(offset).limit(limit)))


TRANSACTION_SORT_FIELDS = {
    "occurred_at": Transaction.date,
    "date": Transaction.date,
    "amount": Transaction.amount,
    "created_at": Transaction.created_at,
    "description": Transaction.description,
}


def transaction_query(
    user_id: int,
    filters: dict | None = None,
    sort_by: str = "occurred_at",
    order: str = "desc",
):
    query = select(Transaction).where(Transaction.user_id == user_id)
    for key, value in (filters or {}).items():
        if value is None:
            continue
        if key == "start_date":
            query = query.where(Transaction.date >= value)
        elif key == "end_date":
            query = query.where(Transaction.date <= value)
        else:
            query = query.where(getattr(Transaction, key) == value)
    sort_column = TRANSACTION_SORT_FIELDS[sort_by]
    direction = sort_column.asc() if order == "asc" else sort_column.desc()
    return query.order_by(direction, Transaction.id.asc() if order == "asc" else Transaction.id.desc())


def count_transactions(session: Session, user_id: int, filters: dict | None = None) -> int:
    query = transaction_query(user_id, filters).order_by(None).subquery()
    return session.scalar(select(func.count()).select_from(query)) or 0

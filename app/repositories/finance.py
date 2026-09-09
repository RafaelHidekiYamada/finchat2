from sqlalchemy import select
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


def transaction_query(user_id: int, filters: dict | None = None):
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
    return query.order_by(Transaction.date.desc(), Transaction.id.desc())

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.security import hash_password, verify_password
from app.models import Category, TransactionType, User
from app.schemas import UserCreate

DEFAULT_CATEGORIES = (
    ("Alimentação", TransactionType.EXPENSE),
    ("Transporte", TransactionType.EXPENSE),
    ("Moradia", TransactionType.EXPENSE),
    ("Salário", TransactionType.INCOME),
    ("Vendas", TransactionType.INCOME),
    ("Serviços", TransactionType.INCOME),
    ("Fornecedores", TransactionType.EXPENSE),
)
_DUMMY_HASH = hash_password("Credencial fictícia para verificação de tempo")


def ensure_default_categories(db: Session, user_id: int) -> None:
    existing = {(row.name, row.type) for row in db.scalars(select(Category).where(Category.user_id == user_id))}
    for name, category_type in DEFAULT_CATEGORIES:
        if (name, category_type) not in existing:
            db.add(Category(user_id=user_id, name=name, type=category_type))
    db.flush()


def register(db: Session, payload: UserCreate) -> User:
    if db.scalar(select(User.id).where(or_(User.document == payload.document, User.email == str(payload.email), User.whatsapp == payload.whatsapp))):
        raise AppError(409, "CONFLICT", "Documento, e-mail ou WhatsApp já cadastrado.")
    values = payload.model_dump(exclude={"password"})
    user = User(**values, password_hash=hash_password(payload.password), is_active=True)
    db.add(user)
    db.flush()
    ensure_default_categories(db, user.id)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    valid = verify_password(password, user.password_hash if user else _DUMMY_HASH)
    if user is None or not valid or not user.is_active:
        raise AppError(401, "INVALID_CREDENTIALS", "Credenciais inválidas ou usuário inativo.")
    return user

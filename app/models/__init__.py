"""Entidades do FinChat; nenhuma credencial bancária real é armazenada."""

from datetime import date as DateValue
from datetime import datetime, timezone
from decimal import Decimal, DecimalException
from enum import Enum as PythonEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.db.base import Base


class UserType(str, PythonEnum):
    CPF = "CPF"
    CNPJ = "CNPJ"


class TransactionType(str, PythonEnum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


class AccountType(str, PythonEnum):
    CHECKING = "CHECKING"
    SAVINGS = "SAVINGS"
    PAYMENT = "PAYMENT"


class Origin(str, PythonEnum):
    BANK = "BANK"
    CASH = "CASH"
    MANUAL = "MANUAL"


class ReconciliationStatus(str, PythonEnum):
    PENDING = "PENDING"
    RECONCILED = "RECONCILED"


class PartnerType(str, PythonEnum):
    CLIENT = "CLIENT"
    SUPPLIER = "SUPPLIER"


class ContractStatus(str, PythonEnum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ConnectionStatus(str, PythonEnum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


def enum_column(enum_class: type[PythonEnum], name: str) -> Enum:
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda values: [member.value for member in values],
    )


class Money(TypeDecorator):
    """Dinheiro exato: NUMERIC no PostgreSQL e centavos inteiros no SQLite.

    O SQLite pode converter NUMERIC para ponto flutuante. Centavos inteiros
    evitam essa conversão inclusive nas somas feitas pelo banco.
    """

    impl = Numeric(14, 2)
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect):
        if dialect.name == "sqlite":
            return dialect.type_descriptor(BigInteger())
        return dialect.type_descriptor(Numeric(14, 2, asdecimal=True))

    def process_bind_param(self, value, dialect: Dialect):
        if value is None:
            return None
        if isinstance(value, (float, bool)):
            raise ValueError("Valores monetários devem usar Decimal, inteiro ou texto decimal.")
        try:
            amount = Decimal(value)
            if not amount.is_finite() or amount.copy_abs() >= Decimal("1000000000000"):
                raise ValueError("Valor monetário fora do limite de 14 dígitos.")
            quantized = amount.quantize(Decimal("0.01"))
            if quantized != amount:
                raise ValueError("Valores monetários devem ter no máximo duas casas decimais.")
        except (DecimalException, TypeError) as exc:
            raise ValueError("Valor monetário inválido.") from exc
        if dialect.name == "sqlite":
            return int(quantized * 100)
        return quantized

    def process_result_value(self, value, dialect: Dialect):
        if value is None:
            return None
        amount = Decimal(value)
        if dialect.name == "sqlite":
            amount /= 100
        return amount.quantize(Decimal("0.01"))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EntityMixin:
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )


class User(EntityMixin, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    whatsapp: Mapped[str] = mapped_column(String(20), unique=True)
    document: Mapped[str] = mapped_column(String(14), unique=True)
    document_type: Mapped[UserType] = mapped_column(enum_column(UserType, "user_type"))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")

    bank_accounts: Mapped[list["BankAccount"]] = relationship(back_populates="user", passive_deletes="all")
    categories: Mapped[list["Category"]] = relationship(back_populates="user", passive_deletes="all")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user", passive_deletes="all")
    partners: Mapped[list["Partner"]] = relationship(back_populates="user", passive_deletes="all")
    contracts: Mapped[list["Contract"]] = relationship(back_populates="user", passive_deletes="all")
    bank_connections: Mapped[list["BankConnection"]] = relationship(back_populates="user", passive_deletes="all")
    chat_command_logs: Mapped[list["ChatCommandLog"]] = relationship(back_populates="user", passive_deletes="all")


class BankAccount(EntityMixin, Base):
    __tablename__ = "bank_accounts"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    institution: Mapped[str] = mapped_column(String(120))
    nickname: Mapped[str] = mapped_column(String(80))
    account_type: Mapped[AccountType] = mapped_column(enum_column(AccountType, "account_type"))
    initial_balance: Mapped[Decimal] = mapped_column(Money(), default=Decimal("0.00"), server_default="0")

    user: Mapped["User"] = relationship(back_populates="bank_accounts")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="bank_account", passive_deletes="all")
    connection: Mapped["BankConnection | None"] = relationship(back_populates="bank_account", passive_deletes="all")


class Category(EntityMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("user_id", "name", "type", name="uq_categories_user_name_type"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    type: Mapped[TransactionType] = mapped_column(enum_column(TransactionType, "transaction_type"))

    user: Mapped["User"] = relationship(back_populates="categories")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="category", passive_deletes="all")


class Partner(EntityMixin, Base):
    __tablename__ = "partners"
    __table_args__ = (
        Index("uq_partners_user_document", "user_id", "document", unique=True),
        Index("uq_partners_user_email", "user_id", "email", unique=True),
        Index("ix_partners_user_type", "user_id", "type"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    type: Mapped[PartnerType] = mapped_column(enum_column(PartnerType, "partner_type"))
    document: Mapped[str | None] = mapped_column(String(14))
    email: Mapped[str | None] = mapped_column(String(254))

    user: Mapped["User"] = relationship(back_populates="partners")
    contracts: Mapped[list["Contract"]] = relationship(back_populates="partner", passive_deletes="all")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="partner", passive_deletes="all")


class Contract(EntityMixin, Base):
    __tablename__ = "contracts"
    __table_args__ = (
        CheckConstraint("expected_amount >= 0", name="expected_amount_non_negative"),
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="date_range"),
        Index("ix_contracts_user_status", "user_id", "status"),
        Index("ix_contracts_user_end_date", "user_id", "end_date"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id", ondelete="RESTRICT"), index=True)
    type: Mapped[TransactionType] = mapped_column(enum_column(TransactionType, "transaction_type"))
    expected_amount: Mapped[Decimal] = mapped_column(Money())
    start_date: Mapped[DateValue] = mapped_column(Date)
    end_date: Mapped[DateValue | None] = mapped_column(Date)
    status: Mapped[ContractStatus] = mapped_column(enum_column(ContractStatus, "contract_status"), default=ContractStatus.ACTIVE, server_default="ACTIVE")

    user: Mapped["User"] = relationship(back_populates="contracts")
    partner: Mapped["Partner"] = relationship(back_populates="contracts")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="contract", passive_deletes="all")


class Transaction(EntityMixin, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        UniqueConstraint("bank_account_id", "external_id", name="uq_transactions_account_external"),
        Index("ix_transactions_user_date", "user_id", "date"),
        Index("ix_transactions_user_account_category", "user_id", "bank_account_id", "category_id"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    description: Mapped[str] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Money())
    date: Mapped[DateValue] = mapped_column(Date, index=True)
    currency: Mapped[str] = mapped_column(String(3), default="BRL", server_default="BRL")
    type: Mapped[TransactionType] = mapped_column(enum_column(TransactionType, "transaction_type"))
    origin: Mapped[Origin] = mapped_column(enum_column(Origin, "origin"), default=Origin.MANUAL, server_default="MANUAL")
    reconciliation_status: Mapped[ReconciliationStatus] = mapped_column(enum_column(ReconciliationStatus, "reconciliation_status"), default=ReconciliationStatus.PENDING, server_default="PENDING")
    bank_account_id: Mapped[int | None] = mapped_column(ForeignKey("bank_accounts.id", ondelete="RESTRICT"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), index=True)
    partner_id: Mapped[int | None] = mapped_column(ForeignKey("partners.id", ondelete="RESTRICT"), index=True)
    contract_id: Mapped[int | None] = mapped_column(ForeignKey("contracts.id", ondelete="RESTRICT"), index=True)
    external_id: Mapped[str | None] = mapped_column(String(120))

    user: Mapped["User"] = relationship(back_populates="transactions")
    bank_account: Mapped["BankAccount | None"] = relationship(back_populates="transactions")
    category: Mapped["Category"] = relationship(back_populates="transactions")
    partner: Mapped["Partner | None"] = relationship(back_populates="transactions")
    contract: Mapped["Contract | None"] = relationship(back_populates="transactions")


class BankConnection(EntityMixin, Base):
    __tablename__ = "bank_connections"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    bank_account_id: Mapped[int] = mapped_column(ForeignKey("bank_accounts.id", ondelete="RESTRICT"), unique=True)
    institution: Mapped[str] = mapped_column(String(120))
    status: Mapped[ConnectionStatus] = mapped_column(enum_column(ConnectionStatus, "connection_status"), default=ConnectionStatus.ACTIVE, server_default="ACTIVE")
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_id: Mapped[str] = mapped_column(String(120), unique=True)

    user: Mapped["User"] = relationship(back_populates="bank_connections")
    bank_account: Mapped["BankAccount"] = relationship(back_populates="connection")


class ChatCommandLog(EntityMixin, Base):
    __tablename__ = "chat_command_logs"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    command: Mapped[str] = mapped_column(String(500))
    action: Mapped[str] = mapped_column(String(50))
    response_message: Mapped[str] = mapped_column(Text)

    user: Mapped["User"] = relationship(back_populates="chat_command_logs")

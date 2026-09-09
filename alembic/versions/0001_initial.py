"""Cria as oito entidades do FinChat CP1.

Revisão: 0001_initial
Anterior: nenhuma

O esquema desta revisão é explícito e independente dos modelos atuais.
Dinheiro usa BIGINT em centavos no SQLite e NUMERIC(14, 2) no PostgreSQL.
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def money():
    return sa.Numeric(14, 2).with_variant(sa.BigInteger(), "sqlite")


def enum_type(name, *values):
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True)


def identity_columns():
    return (
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def user_id():
    return sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)


def upgrade() -> None:
    op.create_table(
        "users",
        *identity_columns(),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("whatsapp", sa.String(20), nullable=False),
        sa.Column("document", sa.String(14), nullable=False),
        sa.Column("document_type", enum_type("user_type", "CPF", "CNPJ"), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("whatsapp", name="uq_users_whatsapp"),
        sa.UniqueConstraint("document", name="uq_users_document"),
    )
    op.create_table(
        "bank_accounts",
        *identity_columns(),
        user_id(),
        sa.Column("institution", sa.String(120), nullable=False),
        sa.Column("nickname", sa.String(80), nullable=False),
        sa.Column("account_type", enum_type("account_type", "CHECKING", "SAVINGS", "PAYMENT"), nullable=False),
        sa.Column("initial_balance", money(), server_default="0", nullable=False),
    )
    op.create_index("ix_bank_accounts_user_id", "bank_accounts", ["user_id"])
    op.create_table(
        "categories",
        *identity_columns(),
        user_id(),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("type", enum_type("transaction_type", "INCOME", "EXPENSE"), nullable=False),
        sa.UniqueConstraint("user_id", "name", "type", name="uq_categories_user_name_type"),
    )
    op.create_index("ix_categories_user_id", "categories", ["user_id"])
    op.create_table(
        "partners",
        *identity_columns(),
        user_id(),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("type", enum_type("partner_type", "CLIENT", "SUPPLIER"), nullable=False),
        sa.Column("document", sa.String(14), nullable=True),
        sa.Column("email", sa.String(254), nullable=True),
    )
    op.create_index("ix_partners_user_id", "partners", ["user_id"])
    op.create_table(
        "contracts",
        *identity_columns(),
        user_id(),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("partner_id", sa.Integer(), sa.ForeignKey("partners.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("type", enum_type("transaction_type", "INCOME", "EXPENSE"), nullable=False),
        sa.Column("expected_amount", money(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", enum_type("contract_status", "ACTIVE", "COMPLETED", "CANCELLED"), server_default="ACTIVE", nullable=False),
        sa.CheckConstraint("expected_amount >= 0", name="expected_amount_non_negative"),
        sa.CheckConstraint("end_date IS NULL OR end_date >= start_date", name="date_range"),
    )
    op.create_index("ix_contracts_user_id", "contracts", ["user_id"])
    op.create_index("ix_contracts_partner_id", "contracts", ["partner_id"])
    op.create_table(
        "transactions",
        *identity_columns(),
        user_id(),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("amount", money(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(3), server_default="BRL", nullable=False),
        sa.Column("type", enum_type("transaction_type", "INCOME", "EXPENSE"), nullable=False),
        sa.Column("origin", enum_type("origin", "BANK", "CASH", "MANUAL"), server_default="MANUAL", nullable=False),
        sa.Column("reconciliation_status", enum_type("reconciliation_status", "PENDING", "RECONCILED"), server_default="PENDING", nullable=False),
        sa.Column("bank_account_id", sa.Integer(), sa.ForeignKey("bank_accounts.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("partner_id", sa.Integer(), sa.ForeignKey("partners.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("contract_id", sa.Integer(), sa.ForeignKey("contracts.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("external_id", sa.String(120), nullable=True),
        sa.CheckConstraint("amount > 0", name="amount_positive"),
        sa.UniqueConstraint("bank_account_id", "external_id", name="uq_transactions_account_external"),
    )
    for column in ("user_id", "date", "bank_account_id", "category_id", "partner_id", "contract_id"):
        op.create_index(f"ix_transactions_{column}", "transactions", [column])
    op.create_table(
        "bank_connections",
        *identity_columns(),
        user_id(),
        sa.Column("bank_account_id", sa.Integer(), sa.ForeignKey("bank_accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("institution", sa.String(120), nullable=False),
        sa.Column("status", enum_type("connection_status", "ACTIVE", "REVOKED"), server_default="ACTIVE", nullable=False),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_id", sa.String(120), nullable=False),
        sa.UniqueConstraint("bank_account_id", name="uq_bank_connections_bank_account_id"),
        sa.UniqueConstraint("external_id", name="uq_bank_connections_external_id"),
    )
    op.create_index("ix_bank_connections_user_id", "bank_connections", ["user_id"])
    op.create_table(
        "chat_command_logs",
        *identity_columns(),
        user_id(),
        sa.Column("command", sa.String(500), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("response_message", sa.Text(), nullable=False),
    )
    op.create_index("ix_chat_command_logs_user_id", "chat_command_logs", ["user_id"])


def downgrade() -> None:
    op.drop_table("chat_command_logs")
    op.drop_table("bank_connections")
    op.drop_table("transactions")
    op.drop_table("contracts")
    op.drop_table("partners")
    op.drop_table("categories")
    op.drop_table("bank_accounts")
    op.drop_table("users")

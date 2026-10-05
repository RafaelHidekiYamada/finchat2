"""Adiciona índices compostos e integridade de parceiros para o CP2.

Revisão: 0002_cp2_indexes_integrity
Anterior: 0001_initial
"""

from alembic import op


revision = "0002_cp2_indexes_integrity"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_transactions_user_date", "transactions", ["user_id", "date"])
    op.create_index(
        "ix_transactions_user_account_category",
        "transactions",
        ["user_id", "bank_account_id", "category_id"],
    )
    op.create_index("ix_contracts_user_status", "contracts", ["user_id", "status"])
    op.create_index("ix_contracts_user_end_date", "contracts", ["user_id", "end_date"])
    op.create_index("ix_partners_user_type", "partners", ["user_id", "type"])
    op.create_index("uq_partners_user_document", "partners", ["user_id", "document"], unique=True)
    op.create_index("uq_partners_user_email", "partners", ["user_id", "email"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_partners_user_email", table_name="partners")
    op.drop_index("uq_partners_user_document", table_name="partners")
    op.drop_index("ix_partners_user_type", table_name="partners")
    op.drop_index("ix_contracts_user_end_date", table_name="contracts")
    op.drop_index("ix_contracts_user_status", table_name="contracts")
    op.drop_index("ix_transactions_user_account_category", table_name="transactions")
    op.drop_index("ix_transactions_user_date", table_name="transactions")

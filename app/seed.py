"""Dados inteiramente fictícios para demonstração acadêmica; execução idempotente."""

from datetime import date

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import BankAccount, BankConnection, Category, Contract, Partner, Transaction, User
from app.schemas import BankAccountCreate, ContractCreate, PartnerCreate, TransactionCreate, UserCreate
from app.services.auth import ensure_default_categories, register
from app.services.finance import create_resource
from app.services.integrations import create_connection

DEMO_PASSWORD = "FinChatDemo!2026"
DEMO_USERS = (
    {"name": "Pessoa de demonstração", "email": "cpf@finchat.demo", "whatsapp": "5511999990001", "document": "52998224725", "document_type": "CPF"},
    {"name": "Empresa de demonstração", "email": "empresa@finchat.demo", "whatsapp": "5511999990002", "document": "11222333000181", "document_type": "CNPJ"},
)


def populate():
    today = date.today()
    with SessionLocal.begin() as db:
        for values in DEMO_USERS:
            user = db.scalar(select(User).where(User.email == values["email"]))
            if user is None:
                user = register(db, UserCreate(**values, password=DEMO_PASSWORD))
            elif user.document != values["document"] or user.document_type != values["document_type"]:
                raise RuntimeError("E-mail de demonstração já utilizado por outro perfil; seed cancelado sem alterações.")
            ensure_default_categories(db, user.id)
            categories = {(row.name.lower(), row.type): row.id for row in db.scalars(select(Category).where(Category.user_id == user.id))}
            nickname = f"Conta demo {values['document_type']}"
            account = db.scalar(select(BankAccount).where(BankAccount.user_id == user.id, BankAccount.nickname == nickname))
            if account is None:
                account = create_resource(db, user, BankAccount, BankAccountCreate(institution="Banco fictício CP1", nickname=nickname, account_type="CHECKING", initial_balance="1000.00" if values["document_type"] == "CPF" else "2000.00"))
            if not db.scalar(select(BankConnection.id).where(BankConnection.bank_account_id == account.id)):
                create_connection(db, user, account.id)
            if values["document_type"] == "CPF":
                movements = [
                    dict(description="Salário fictício de demonstração", amount="3000.00", type="INCOME", category_id=categories["salário", "INCOME"], bank_account_id=account.id),
                    dict(description="Alimentação fictícia de demonstração", amount="50.00", type="EXPENSE", category_id=categories["alimentação", "EXPENSE"], bank_account_id=account.id),
                    dict(description="Transporte em dinheiro de demonstração", amount="25.00", type="EXPENSE", category_id=categories["transporte", "EXPENSE"], origin="CASH"),
                ]
            else:
                movements = []
                for partner_name, partner_type, transaction_type, category_name, expected, paid in (
                    ("Cliente fictício CP1", "CLIENT", "INCOME", "Serviços", "3000.00", "1200.00"),
                    ("Fornecedor fictício CP1", "SUPPLIER", "EXPENSE", "Fornecedores", "500.00", "250.00"),
                ):
                    partner = db.scalar(select(Partner).where(Partner.user_id == user.id, Partner.name == partner_name, Partner.type == partner_type))
                    if partner is None:
                        partner = create_resource(db, user, Partner, PartnerCreate(name=partner_name, type=partner_type))
                    title = f"Contrato demo: {partner_name}"
                    contract = db.scalar(select(Contract).where(Contract.user_id == user.id, Contract.title == title, Contract.partner_id == partner.id))
                    if contract is None:
                        contract = create_resource(db, user, Contract, ContractCreate(title=title, partner_id=partner.id, type=transaction_type, expected_amount=expected, start_date=today.replace(day=1)))
                    movements.append(dict(description=f"Movimentação demo: {partner_name}", amount=paid, type=transaction_type, category_id=categories[category_name.lower(), transaction_type], bank_account_id=account.id, partner_id=partner.id, contract_id=contract.id))
            for movement in movements:
                if not db.scalar(select(Transaction.id).where(Transaction.user_id == user.id, Transaction.description == movement["description"])):
                    create_resource(db, user, Transaction, TransactionCreate(date=today, **movement))
    print("Seed concluído: dados fictícios CPF/CNPJ, categorias, contas, conexões, transações, parceiros e contratos.")
    print("Usuários: cpf@finchat.demo e empresa@finchat.demo")
    print("Senha de demonstração para usuários criados pelo seed: FinChatDemo!2026")


if __name__ == "__main__":
    populate()

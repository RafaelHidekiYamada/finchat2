import datetime as dt
import re
from decimal import Decimal, DecimalException
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field, StringConstraints, create_model, field_validator, model_validator

from app.models import AccountType, ConnectionStatus, ContractStatus, Origin, PartnerType, ReconciliationStatus, TransactionType, UserType


def exact_money(value):
    if isinstance(value, (float, bool)):
        raise ValueError("Envie dinheiro como string decimal, por exemplo '50.00'.")
    try:
        amount = Decimal(value)
        if not amount.is_finite() or amount.copy_abs() >= Decimal("1000000000000"):
            raise ValueError("Valor monetário fora do limite.")
        if amount != amount.quantize(Decimal("0.01")):
            raise ValueError("Informe no máximo duas casas decimais.")
        return amount.quantize(Decimal("0.01"))
    except (DecimalException, TypeError):
        raise ValueError("Valor monetário inválido.") from None


Money = Annotated[Decimal, BeforeValidator(exact_money), Field(max_digits=14, decimal_places=2)]
PositiveMoney = Annotated[Money, Field(gt=0)]
NonnegativeMoney = Annotated[Money, Field(ge=0)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
ShortName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Identifier = Annotated[int, Field(gt=0)]


def normalize_document(value: str) -> str:
    if not re.fullmatch(r"[0-9.\-/\s]+", value):
        raise ValueError("Documento deve conter somente números e máscara usual.")
    digits = re.sub(r"\D", "", value)
    if len(set(digits)) == 1:
        raise ValueError("Documento inválido.")
    if len(digits) == 11:
        base = digits[:9]
        for length in (10, 11):
            remainder = sum(int(n) * weight for n, weight in zip(base, range(length, 1, -1))) * 10 % 11
            base += str(0 if remainder == 10 else remainder)
    elif len(digits) == 14:
        base = digits[:12]
        for weights in ((5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2), (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)):
            remainder = sum(int(n) * weight for n, weight in zip(base, weights)) % 11
            base += str(0 if remainder < 2 else 11 - remainder)
    else:
        raise ValueError("Informe CPF com 11 dígitos ou CNPJ com 14 dígitos.")
    if digits != base:
        raise ValueError("Dígitos verificadores inválidos.")
    return digits


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


T = TypeVar("T")


class Success(Schema, Generic[T]):
    message: str
    data: T


class PaginationMeta(Schema):
    page: int
    page_size: int
    total: int
    total_pages: int


class Paginated(Schema, Generic[T]):
    data: list[T]
    meta: PaginationMeta


class ErrorBody(Schema):
    code: str
    message: str
    details: list[dict] = Field(default_factory=list)


class ErrorResponse(Schema):
    error: ErrorBody


class UserCreate(Schema):
    model_config = ConfigDict(json_schema_extra={"example": {"name": "Pessoa de demonstração", "email": "pessoa@example.com", "whatsapp": "+55 (11) 99999-0001", "document": "529.982.247-25", "document_type": "CPF", "password": "MinhaSenha!2026"}})
    name: Name
    email: EmailStr
    whatsapp: str = Field(max_length=30)
    document: str = Field(max_length=25)
    document_type: UserType
    password: str = Field(min_length=8, max_length=128, repr=False)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("document")
    @classmethod
    def validate_document(cls, value):
        return normalize_document(value)

    @field_validator("whatsapp")
    @classmethod
    def normalize_phone(cls, value):
        if not re.fullmatch(r"\+?[0-9() .\-]+", value):
            raise ValueError("Número de WhatsApp inválido.")
        digits = re.sub(r"\D", "", value)
        if not 10 <= len(digits) <= 15:
            raise ValueError("Informe de 10 a 15 dígitos, preferencialmente com DDI.")
        return digits

    @model_validator(mode="after")
    def document_matches_profile(self):
        if len(self.document) != (11 if self.document_type == UserType.CPF else 14):
            raise ValueError("Documento incompatível com o perfil.")
        return self


class UserRead(Schema):
    id: int
    name: str
    email: str
    whatsapp: str
    document: str
    document_type: UserType
    is_active: bool
    created_at: dt.datetime


class Login(Schema):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128, repr=False)
    model_config = ConfigDict(json_schema_extra={"example": {"email": "cpf@finchat.demo", "password": "FinChatDemo!2026"}})


class TokenRead(Schema):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class EntityRead(Schema):
    id: int
    user_id: int
    created_at: dt.datetime


class BankAccountCreate(Schema):
    institution: Name
    nickname: ShortName
    account_type: AccountType
    initial_balance: Money = Decimal("0.00")
    model_config = ConfigDict(json_schema_extra={"example": {"institution": "Banco fictício CP1", "nickname": "Conta principal", "account_type": "CHECKING", "initial_balance": "1000.00"}})


class BankAccountRead(BankAccountCreate, EntityRead):
    pass


class CategoryCreate(Schema):
    name: ShortName
    type: TransactionType
    model_config = ConfigDict(json_schema_extra={"example": {"name": "Educação", "type": "EXPENSE"}})


class CategoryRead(CategoryCreate, EntityRead):
    pass


class PartnerCreate(Schema):
    name: Name
    type: PartnerType
    document: str | None = Field(default=None, max_length=25)
    email: EmailStr | None = None
    model_config = ConfigDict(json_schema_extra={"example": {"name": "Cliente fictício", "type": "CLIENT"}})

    @field_validator("document")
    @classmethod
    def validate_document(cls, value):
        return normalize_document(value) if value is not None else None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class PartnerRead(PartnerCreate, EntityRead):
    pass


class ContractCreate(Schema):
    title: Name
    partner_id: Identifier
    type: TransactionType
    expected_amount: NonnegativeMoney
    start_date: dt.date
    end_date: dt.date | None = None
    status: ContractStatus = ContractStatus.ACTIVE
    model_config = ConfigDict(json_schema_extra={"example": {"title": "Serviços de demonstração", "partner_id": 1, "type": "INCOME", "expected_amount": "1000.00", "start_date": "2026-09-01", "status": "ACTIVE"}})

    @model_validator(mode="after")
    def dates_are_ordered(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("Data final deve ser igual ou posterior à inicial.")
        return self


class ContractRead(ContractCreate, EntityRead):
    pass


class TransactionCreate(Schema):
    description: Description
    amount: PositiveMoney
    date: dt.date
    type: TransactionType
    category_id: Identifier
    bank_account_id: Identifier | None = None
    partner_id: Identifier | None = None
    contract_id: Identifier | None = None
    currency: Literal["BRL"] = "BRL"
    origin: Origin = Origin.MANUAL
    reconciliation_status: ReconciliationStatus = ReconciliationStatus.PENDING
    model_config = ConfigDict(json_schema_extra={"example": {"description": "Almoço de demonstração", "amount": "50.00", "date": "2026-09-07", "type": "EXPENSE", "category_id": 1, "origin": "CASH"}})


class TransactionRead(TransactionCreate, EntityRead):
    external_id: str | None = None


class BankConnectionCreate(Schema):
    bank_account_id: Identifier
    model_config = ConfigDict(json_schema_extra={"example": {"bank_account_id": 1}})


class BankConnectionRead(EntityRead):
    bank_account_id: int
    institution: str
    status: ConnectionStatus
    consent_at: dt.datetime
    last_synced_at: dt.datetime | None
    external_id: str


class CategoryTotal(Schema):
    category_id: int
    category_name: str
    type: TransactionType
    total: Decimal


class BalanceRead(Schema):
    initial_balance: Decimal
    total_income: Decimal
    total_expenses: Decimal
    balance: Decimal


class SummaryRead(BalanceRead):
    by_category: list[CategoryTotal]


class FinancialSummaryRead(Schema):
    total_income: Decimal
    total_expenses: Decimal
    received: Decimal
    paid: Decimal
    balance: Decimal
    expected_amount: Decimal
    outstanding_amount: Decimal


class SyncRead(Schema):
    imported_count: int
    transactions: list[TransactionRead]


class ChatCommand(Schema):
    command: str = Field(min_length=1, max_length=300)
    model_config = ConfigDict(json_schema_extra={"example": {"command": "gastei 50 em alimentação"}})


class ChatRead(Schema):
    action: str
    reply: str
    transaction: TransactionRead | None = None
    summary: SummaryRead | None = None


class HealthRead(Schema):
    status: Literal["ok"]
    database: Literal["ok"]
    environment: Literal["CP2"]


class MonthlyFlow(Schema):
    month: str
    income: Decimal
    expenses: Decimal


class ExpenseByCategory(Schema):
    category_id: int
    category_name: str
    total: Decimal


class AccountBalance(Schema):
    id: int
    institution: str
    nickname: str
    balance: Decimal


class PartnerMovement(Schema):
    partner_id: int
    partner_name: str
    partner_type: PartnerType
    total_income: Decimal
    total_expenses: Decimal
    movement: Decimal


class ContractDue(Schema):
    contract_id: int
    title: str
    end_date: dt.date
    expected_amount: Decimal


class CompanyOverview(Schema):
    active_contracts: int
    received: Decimal
    paid: Decimal
    clients: list[PartnerMovement]
    suppliers: list[PartnerMovement]
    contracts_due_soon: list[ContractDue]
    top_partners: list[PartnerMovement]


class DashboardOverview(Schema):
    start_date: dt.date
    end_date: dt.date
    consolidated_balance: Decimal
    total_income: Decimal
    total_expenses: Decimal
    net_result: Decimal
    monthly_flow: list[MonthlyFlow]
    expenses_by_category: list[ExpenseByCategory]
    latest_transactions: list[TransactionRead]
    alerts: list[str]
    bank_accounts: list[AccountBalance]
    company: CompanyOverview | None = None


class FinancialAnalysisRequest(Schema):
    start_date: dt.date | None = None
    end_date: dt.date | None = None

    @model_validator(mode="after")
    def dates_are_ordered(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("Data inicial deve ser igual ou anterior à final.")
        return self


class AnalysisPeriod(Schema):
    start_date: dt.date
    end_date: dt.date


class FinancialAnalysisContent(Schema):
    financial_summary: str
    positive_points: list[str]
    attention_points: list[str]
    recommendations: list[str]
    alerts: list[str]
    data_quality_notes: list[str]
    disclaimer: Literal["A análise é educacional e não representa recomendação de investimento."] = "A análise é educacional e não representa recomendação de investimento."

    @model_validator(mode="after")
    def reject_investment_recommendations(self):
        prohibited = ("compre ", "comprar ", "venda ", "vender ", "invista ", "investir ", "ações", "cripto")
        if any(term in recommendation.lower() for recommendation in self.recommendations for term in prohibited):
            raise ValueError("Recomendações de compra, venda ou investimento não são permitidas.")
        return self


class FinancialAnalysisRead(FinancialAnalysisContent):
    period: AnalysisPeriod
    generated_at: dt.datetime
    analysis_source: Literal["ollama", "deterministic"]
    fallback_used: bool


def update_schema(name, schema):
    """PUT parcial: somente os campos enviados substituem os valores atuais."""
    fields = {key: (field.rebuild_annotation() | None, None) for key, field in schema.model_fields.items()}
    return create_model(name, __base__=Schema, **fields)


BankAccountUpdate = update_schema("BankAccountUpdate", BankAccountCreate)
CategoryUpdate = update_schema("CategoryUpdate", CategoryCreate)
PartnerUpdate = update_schema("PartnerUpdate", PartnerCreate)
ContractUpdate = update_schema("ContractUpdate", ContractCreate)
TransactionUpdate = update_schema("TransactionUpdate", TransactionCreate)

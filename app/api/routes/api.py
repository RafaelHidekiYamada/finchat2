from datetime import date, datetime, timezone
from math import ceil
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import CurrentUser, Db, get_financial_analysis_provider
from app.api.routes.crud import register_crud
from app.core.config import get_settings
from app.core.security import create_access_token
from app.models import BankAccount, BankConnection, Category, Contract, Origin, Partner, Transaction, TransactionType
from app.repositories.finance import count_transactions, list_owned, owned, transaction_query
from app.schemas import BankAccountCreate, BankAccountRead, BankAccountUpdate, BalanceRead, BankConnectionCreate, BankConnectionRead, CategoryCreate, CategoryRead, CategoryUpdate, ChatCommand, ChatRead, ContractCreate, ContractRead, ContractUpdate, DashboardOverview, ErrorResponse, FinancialAnalysisRead, FinancialAnalysisRequest, FinancialSummaryRead, Login, Paginated, PartnerCreate, PartnerRead, PartnerUpdate, Success, SummaryRead, SyncRead, TokenRead, TransactionCreate, TransactionRead, TransactionUpdate, UserCreate, UserRead
from app.services.auth import authenticate, register
from app.services.dashboard import dashboard_overview, llm_financial_context
from app.services.finance import create_resource, financial_summary, invalid, summary, validate_filters
from app.services.integrations import create_connection, execute_command, sync_connection
from app.integrations.llm_provider import FinancialAnalysisProvider, FinancialAnalysisResult, insufficient_data_analysis

ERROR_RESPONSES = {code: {"model": ErrorResponse, "description": description} for code, description in {400: "Regra de negócio inválida", 401: "Token ou credenciais inválidos", 403: "Perfil sem permissão", 404: "Recurso não encontrado ou pertencente a outro usuário", 409: "Registro duplicado ou recurso em uso", 422: "Campos inválidos", 500: "Erro interno sem detalhes sensíveis"}.items()}
router = APIRouter(prefix="/api/v1", responses=ERROR_RESPONSES)


@router.post("/auth/register", tags=["Autenticação"], status_code=201, response_model=Success[UserRead], summary="Cadastrar usuário CPF ou CNPJ")
def register_user(payload: UserCreate, db: Db):
    user = register(db, payload)
    db.commit()
    return {"message": "Usuário cadastrado com sucesso.", "data": user}


@router.post("/auth/login", tags=["Autenticação"], response_model=Success[TokenRead], summary="Entrar e obter token JWT")
def login(payload: Login, db: Db):
    user = authenticate(db, str(payload.email), payload.password)
    return {"message": "Login realizado com sucesso.", "data": {"access_token": create_access_token(user.id), "token_type": "bearer", "expires_in": get_settings().access_token_expire_minutes * 60}}


@router.get("/auth/me", tags=["Autenticação"], response_model=Success[UserRead], summary="Consultar usuário autenticado")
def me(user: CurrentUser):
    return {"message": "Usuário autenticado.", "data": user}


def get_filters(start_date: date | None = None, end_date: date | None = None, type: TransactionType | None = None, category_id: int | None = Query(None, gt=0), bank_account_id: int | None = Query(None, gt=0), contract_id: int | None = Query(None, gt=0), partner_id: int | None = Query(None, gt=0)) -> dict:
    return {"start_date": start_date, "end_date": end_date, "type": type, "category_id": category_id, "bank_account_id": bank_account_id, "contract_id": contract_id, "partner_id": partner_id}


Filters = Annotated[dict, Depends(get_filters)]


@router.get("/transactions", tags=["Transações"], response_model=Success[list[TransactionRead]] | Paginated[TransactionRead], summary="Listar, filtrar, ordenar e paginar transações", description="Use page/page_size para o contrato paginado do CP2. Sem esses parâmetros, mantém o envelope legado do CP1 com limit/offset, sempre limitado a 100 registros.")
def list_transactions(
    db: Db,
    user: CurrentUser,
    filters: Filters,
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1, le=100),
    sort_by: Literal["occurred_at", "date", "amount", "created_at", "description"] = "occurred_at",
    order: Literal["asc", "desc"] = "desc",
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    validate_filters(db, user, filters)
    query = transaction_query(user.id, filters, sort_by, order)
    if page is not None or page_size is not None:
        current_page, current_size = page or 1, page_size or 20
        total = count_transactions(db, user.id, filters)
        records = list(db.scalars(query.offset((current_page - 1) * current_size).limit(current_size)))
        return {"data": records, "meta": {"page": current_page, "page_size": current_size, "total": total, "total_pages": ceil(total / current_size) if total else 0}}
    records = list(db.scalars(query.offset(offset).limit(limit)))
    return {"message": "Transações consultadas.", "data": records}


@router.get("/dashboard/overview", tags=["Dashboard"], response_model=Success[DashboardOverview], summary="Consultar visão financeira consolidada")
def dashboard(db: Db, user: CurrentUser, start_date: date | None = None, end_date: date | None = None):
    return {"message": "Dashboard consolidado calculado.", "data": dashboard_overview(db, user, start_date, end_date)}


@router.post("/ai/financial-analysis", tags=["Análise inteligente"], response_model=Success[FinancialAnalysisRead], summary="Gerar análise financeira educacional com IA", description="O backend envia ao provedor somente agregados financeiros minimizados. Identidade, token, documento, contato e dados bancários não são enviados.")
def financial_analysis(
    payload: FinancialAnalysisRequest,
    db: Db,
    user: CurrentUser,
    provider: Annotated[FinancialAnalysisProvider, Depends(get_financial_analysis_provider)],
):
    overview = dashboard_overview(db, user, payload.start_date, payload.end_date)
    context = llm_financial_context(overview, user)
    has_movements = overview["total_income"] != 0 or overview["total_expenses"] != 0
    outcome = provider.analyze(context) if has_movements else FinancialAnalysisResult(
        content=insufficient_data_analysis(), source="deterministic", fallback_used=False
    )
    result = {
        **outcome.content.model_dump(),
        "period": {"start_date": overview["start_date"], "end_date": overview["end_date"]},
        "generated_at": datetime.now(timezone.utc),
        "analysis_source": outcome.source,
        "fallback_used": outcome.fallback_used,
    }
    return {"message": "Análise financeira gerada.", "data": result}


@router.get("/transactions/summary", tags=["Transações"], response_model=Success[SummaryRead], summary="Consultar resumo financeiro", description="Saldo inicial das contas + receitas − despesas filtradas, incluindo dinheiro. O filtro de período restringe as movimentações; não representa saldo histórico de fechamento. Conciliação não altera o saldo.")
def transaction_summary(db: Db, user: CurrentUser, filters: Filters):
    return {"message": "Resumo financeiro calculado.", "data": summary(db, user, filters)}


@router.post("/transactions/cash", tags=["Transações"], status_code=201, response_model=Success[TransactionRead], summary="Registrar movimentação em dinheiro")
def cash_transaction(payload: TransactionCreate, db: Db, user: CurrentUser):
    if payload.bank_account_id is not None:
        invalid("Movimentação em dinheiro não aceita conta bancária.")
    payload = payload.model_copy(update={"origin": Origin.CASH})
    record = create_resource(db, user, Transaction, payload)
    db.commit()
    return {"message": "Movimentação em dinheiro registrada.", "data": record}


@router.get("/bank-accounts/{id}/balance", tags=["Contas bancárias"], response_model=Success[BalanceRead], summary="Calcular saldo da conta")
def account_balance(db: Db, user: CurrentUser, id: int = Path(gt=0)):
    owned(db, BankAccount, user.id, id)
    result = summary(db, user, {"bank_account_id": id})
    result.pop("by_category")
    return {"message": "Saldo da conta calculado.", "data": result}


@router.get("/partners/{id}/financial-summary", tags=["Parceiros"], response_model=Success[FinancialSummaryRead], summary="Consultar resumo do parceiro (CNPJ)")
def partner_summary(db: Db, user: CurrentUser, id: int = Path(gt=0)):
    return {"message": "Resumo do parceiro calculado.", "data": financial_summary(db, user, Partner, id)}


@router.get("/contracts/{id}/financial-summary", tags=["Contratos"], response_model=Success[FinancialSummaryRead], summary="Consultar resumo do contrato (CNPJ)")
def contract_summary(db: Db, user: CurrentUser, id: int = Path(gt=0)):
    return {"message": "Resumo do contrato calculado.", "data": financial_summary(db, user, Contract, id)}


@router.post("/bank-connections", tags=["Conexões simuladas"], status_code=201, response_model=Success[BankConnectionRead], summary="Criar conexão fictícia CP1", description="Simula consentimento; não constitui autorização de Open Finance e não recebe credenciais bancárias.")
def bank_connection(payload: BankConnectionCreate, db: Db, user: CurrentUser):
    connection = create_connection(db, user, payload.bank_account_id)
    db.commit()
    return {"message": "Conexão simulada criada. Nenhum banco real foi conectado.", "data": connection}


@router.get("/bank-connections", tags=["Conexões simuladas"], response_model=Success[list[BankConnectionRead]], summary="Listar conexões fictícias")
def connections(db: Db, user: CurrentUser, limit: int = Query(100, ge=1, le=100), offset: int = Query(0, ge=0)):
    return {"message": "Conexões simuladas consultadas.", "data": list_owned(db, BankConnection, user.id, limit, offset)}


@router.post("/bank-connections/{id}/sync", tags=["Conexões simuladas"], response_model=Success[SyncRead], summary="Importar transações fictícias CP1", description="Importa três exemplos estáveis. Repetir a sincronização preserva os registros existentes sem duplicar identificadores externos.")
def sync(db: Db, user: CurrentUser, id: int = Path(gt=0)):
    result = sync_connection(db, user, id)
    db.commit()
    return {"message": "Sincronização simulada concluída.", "data": result}


@router.post("/chat/commands", tags=["Chat simulado"], response_model=Success[ChatRead], summary="Interpretar comando local", description="Comandos: saldo; resumo do mês; gastei 50 em alimentação; recebi 200 por serviço. Não envia mensagens reais.")
def chat(payload: ChatCommand, db: Db, user: CurrentUser):
    result = execute_command(db, user, payload.command)
    db.commit()
    return {"message": "Comando simulado processado.", "data": result}


register_crud(router, "/bank-accounts", BankAccount, BankAccountCreate, BankAccountUpdate, BankAccountRead, "Contas bancárias", "Conta bancária")
register_crud(router, "/categories", Category, CategoryCreate, CategoryUpdate, CategoryRead, "Categorias", "Categoria")
register_crud(router, "/transactions", Transaction, TransactionCreate, TransactionUpdate, TransactionRead, "Transações", "Transação", include_list=False)
register_crud(router, "/partners", Partner, PartnerCreate, PartnerUpdate, PartnerRead, "Parceiros", "Parceiro", company=True)
register_crud(router, "/contracts", Contract, ContractCreate, ContractUpdate, ContractRead, "Contratos", "Contrato", company=True)

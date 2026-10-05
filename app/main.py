from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.dependencies import Db
from app.api.routes.api import ERROR_RESPONSES, router
from app.core.exceptions import install_error_handlers
from app.schemas import HealthRead, Success
from app.core.config import get_settings

app = FastAPI(
    title="FinChat API",
    version="2.0.0-cp2",
    description="FinChat CP2: API financeira para CPF e CNPJ com dashboard consolidado, paginação, frontend e análise inteligente baseada somente em agregados minimizados. Banco e WhatsApp permanecem simulados.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[{"name": name, "description": description} for name, description in (
        ("Autenticação", "Cadastro, login e perfil autenticado."),
        ("Contas bancárias", "Contas locais e saldo calculado."),
        ("Categorias", "Classificação pessoal de receitas e despesas."),
        ("Transações", "Movimentações financeiras e resumo por categoria."),
        ("Parceiros", "Clientes e fornecedores, somente CNPJ."),
        ("Contratos", "Contratos empresariais e acompanhamento financeiro, somente CNPJ."),
        ("Conexões simuladas", "Demonstração fictícia da futura integração bancária."),
        ("Chat simulado", "Comandos locais sem envio ao WhatsApp."),
        ("Dashboard", "Agregados financeiros reais do usuário autenticado em uma única requisição."),
        ("Análise inteligente", "Análise educacional via Ollama local com fallback determinístico e dados minimizados."),
        ("Saúde", "Disponibilidade da API e conexão com o banco."),
    )],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
install_error_handlers(app)
app.include_router(router)


@app.get("/health", tags=["Saúde"], response_model=Success[HealthRead], responses=ERROR_RESPONSES, summary="Verificar saúde da API e do banco")
@app.get("/api/v1/health", tags=["Saúde"], response_model=Success[HealthRead], responses=ERROR_RESPONSES, summary="Verificar saúde da API e do banco")
def health(db: Db):
    db.execute(text("SELECT 1"))
    return {"message": "API disponível.", "data": {"status": "ok", "database": "ok", "environment": "CP2"}}

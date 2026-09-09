from fastapi import FastAPI
from sqlalchemy import text

from app.api.dependencies import Db
from app.api.routes.api import ERROR_RESPONSES, router
from app.core.exceptions import install_error_handlers
from app.schemas import HealthRead, Success

app = FastAPI(
    title="FinChat API",
    version="1.0.0-cp1",
    description="Backend do Checkpoint 1: controle financeiro para CPF e CNPJ, com autenticação JWT, contas, categorias, transações, parceiros e contratos. Integrações bancária e de WhatsApp são exclusivamente simulações locais, sem acesso a serviços reais. Valores monetários devem ser enviados como strings decimais em BRL.",
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
        ("Saúde", "Disponibilidade da API e conexão com o banco."),
    )],
)
install_error_handlers(app)
app.include_router(router)


@app.get("/health", tags=["Saúde"], response_model=Success[HealthRead], responses=ERROR_RESPONSES, summary="Verificar saúde da API e do banco")
@app.get("/api/v1/health", tags=["Saúde"], response_model=Success[HealthRead], responses=ERROR_RESPONSES, summary="Verificar saúde da API e do banco")
def health(db: Db):
    db.execute(text("SELECT 1"))
    return {"message": "API disponível.", "data": {"status": "ok", "database": "ok", "environment": "CP1_SIMULATION"}}

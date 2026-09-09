import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException

logger = logging.getLogger("finchat")


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: list | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []


def error_response(status: int, code: str, message: str, details: list | None = None, headers=None):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "details": details or []}}, headers=headers)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError):
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return error_response(exc.status_code, exc.code, exc.message, exc.details, headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Não devolva os valores recebidos: podem conter senha ou token.
        details = [{"field": ".".join(str(part) for part in error["loc"]), "type": error["type"], "message": "Valor inválido para o campo."} for error in exc.errors()]
        return error_response(422, "VALIDATION_ERROR", "Verifique os campos enviados.", details)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        codes = {400: "BUSINESS_RULE_ERROR", 401: "UNAUTHENTICATED", 403: "FORBIDDEN", 404: "RESOURCE_NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 409: "CONFLICT"}
        messages = {404: "Recurso não encontrado.", 405: "Método não permitido."}
        return error_response(exc.status_code, codes.get(exc.status_code, "HTTP_ERROR"), messages.get(exc.status_code, "Não foi possível processar a solicitação."), headers=exc.headers)

    @app.exception_handler(IntegrityError)
    async def integrity_error(request: Request, exc: IntegrityError):
        return error_response(409, "CONFLICT", "O registro já existe ou possui vínculos que impedem a operação.")

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception):
        # Não registrar SQL/parâmetros que possam incluir dados pessoais.
        logger.error("Erro interno em %s: %s", request.url.path, type(exc).__name__)
        return error_response(500, "INTERNAL_ERROR", "Erro interno. Tente novamente mais tarde.")

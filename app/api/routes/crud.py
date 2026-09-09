from fastapi import APIRouter, Path, Query

from app.api.dependencies import CurrentUser, Db, require_company
from app.repositories.finance import list_owned, owned
from app.schemas import Success
from app.services.finance import create_resource, delete_resource, update_resource


def register_crud(router: APIRouter, path: str, model, create_schema, update_schema, read_schema, tag: str, label: str, company: bool = False, include_list: bool = True):
    """Aplica o mesmo contrato HTTP aos cinco recursos com CRUD."""
    def create(payload, db: Db, user: CurrentUser):
        if company:
            require_company(user)
        record = create_resource(db, user, model, payload)
        db.commit()
        return {"message": f"{label} criado(a) com sucesso.", "data": record}

    def listing(db: Db, user: CurrentUser, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
        if company:
            require_company(user)
        return {"message": "Consulta realizada com sucesso.", "data": list_owned(db, model, user.id, limit, offset)}

    def retrieve(db: Db, user: CurrentUser, id: int = Path(gt=0)):
        if company:
            require_company(user)
        return {"message": "Consulta realizada com sucesso.", "data": owned(db, model, user.id, id)}

    def update(payload, db: Db, user: CurrentUser, id: int = Path(gt=0)):
        record = update_resource(db, user, model, id, payload)
        db.commit()
        return {"message": f"{label} atualizado(a) com sucesso.", "data": record}

    def delete(db: Db, user: CurrentUser, id: int = Path(gt=0)):
        delete_resource(db, user, model, id)
        db.commit()
        return {"message": f"{label} excluído(a) com sucesso.", "data": None}

    # Anotações concretas preservam os schemas completos no OpenAPI.
    create.__annotations__["payload"] = create_schema
    update.__annotations__["payload"] = update_schema
    common = {"tags": [tag]}
    router.add_api_route(path, create, methods=["POST"], status_code=201, response_model=Success[read_schema], summary=f"Criar {label.lower()}", name=f"create_{model.__name__}", **common)
    if include_list:
        router.add_api_route(path, listing, methods=["GET"], response_model=Success[list[read_schema]], summary=f"Listar {tag.lower()}", name=f"list_{model.__name__}", **common)
    router.add_api_route(path + "/{id}", retrieve, methods=["GET"], response_model=Success[read_schema], summary=f"Consultar {label.lower()}", name=f"get_{model.__name__}", **common)
    router.add_api_route(path + "/{id}", update, methods=["PUT"], response_model=Success[read_schema], summary=f"Atualizar {label.lower()}", description="Atualização parcial: campos omitidos preservam o valor atual. Campos obrigatórios não aceitam null.", name=f"update_{model.__name__}", **common)
    router.add_api_route(path + "/{id}", delete, methods=["DELETE"], response_model=Success[None], summary=f"Excluir {label.lower()}", description="Recursos com dependências retornam 409. Transações podem ser excluídas.", name=f"delete_{model.__name__}", **common)

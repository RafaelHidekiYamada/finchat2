# Arquitetura do FinChat — CP1

## Objetivo e limites

O CP1 fornece uma API REST local para finanças pessoais e empresariais. Não contém frontend e não se conecta a bancos ou ao WhatsApp. Os provedores de integração produzem resultados fictícios para demonstrar os fluxos; as regras financeiras permanecem na aplicação.

## Camadas e responsabilidades

| Diretório | Responsabilidade |
| --- | --- |
| `app/api/routes` | Rotas HTTP, status, tags Swagger e delegação das operações |
| `app/api/dependencies.py` | Sessão de banco, usuário autenticado e permissões por perfil |
| `app/core` | Configuração por ambiente, JWT, hash de senha e exceções globais |
| `app/db` | Base declarativa, engine e ciclo de vida das sessões |
| `app/models` | Entidades SQLAlchemy, relações, índices e restrições |
| `app/schemas` | Contratos Pydantic, validação e exemplos OpenAPI |
| `app/repositories` | Acesso ao banco e consultas restritas ao proprietário |
| `app/services` | Operações financeiras, compatibilidade de vínculos, resumos, chat e sincronização |
| `app/integrations` | Contratos de provedores e implementações simuladas |
| `app/main.py` | Instanciação FastAPI, inclusão de rotas e tratamento global de erros |
| `app/seed.py` | Carga idempotente de demonstração |
| `alembic` | Histórico de migrations do schema |
| `tests` | Validação automatizada com banco isolado |

```mermaid
flowchart TD
    Cliente[Cliente HTTP ou Swagger] --> API[FastAPI: rotas e schemas]
    API --> Auth[Dependências: JWT e permissões]
    Auth --> Servicos[Serviços de negócio]
    Servicos --> Repositorios[Repositórios e SQLAlchemy]
    Repositorios --> Banco[(SQLite local ou PostgreSQL configurado)]
    Servicos --> BancoFake[Provedor bancário simulado]
    Servicos --> ChatFake[Interpretador local de comandos]
    Alembic[Alembic] --> Banco
    Seed[Seed fictício] --> Banco
```

Rotas coordenam a entrada HTTP; serviços validam a operação no contexto do usuário. Os simuladores não concedem acesso direto ao banco de outro usuário nem dispensam regras de categoria, valor ou perfil.

## Modelo relacional

`User` é o proprietário dos recursos. `BankAccount` representa contas e seus saldos iniciais; `BankConnection` registra uma conexão fictícia vinculada a uma conta. `Category` classifica transações. `Transaction` registra a movimentação efetiva e pode referenciar conta, parceiro e contrato. `Partner` e `Contract` representam o domínio empresarial. `ChatCommandLog` mantém registro básico da interação simulada.

```mermaid
erDiagram
    User ||--o{ BankAccount : possui
    User ||--o{ BankConnection : possui
    User ||--o{ Category : define
    User ||--o{ Transaction : registra
    User ||--o{ Partner : cadastra
    User ||--o{ Contract : gerencia
    User ||--o{ ChatCommandLog : executa
    BankAccount ||--o| BankConnection : conecta
    BankAccount o|--o{ Transaction : movimenta
    Category ||--o{ Transaction : classifica
    Partner ||--o{ Contract : participa
    Partner o|--o{ Transaction : referencia
    Contract o|--o{ Transaction : agrupa
```

Chaves estrangeiras preservam as relações. Serviços também conferem que todos os IDs relacionados pertencem ao mesmo usuário e formam uma combinação válida. Uma chave estrangeira isolada não substitui essa regra de autorização.

## Precisão monetária e resumos

O domínio utiliza `Decimal` e valida valores com até duas casas. A persistência usa `Numeric(14, 2)` no PostgreSQL e centavos inteiros no SQLite por meio de um tipo SQLAlchemy adaptado. Essa escolha evita a afinidade numérica do SQLite produzir cálculos financeiros com ponto flutuante. A API pode representar dinheiro como strings decimais.

Saldos são derivados de saldo inicial e movimentações. O consolidado inclui transações sem conta, como dinheiro. Conciliação não muda a aritmética. Resumos com período filtram movimentações e mantêm os saldos iniciais; não implementam saldo histórico de fechamento. Valores previstos de contratos são referências de planejamento e não se somam às movimentações efetivas.

## Autenticação e isolamento

1. Cadastro normaliza identidade e persiste somente hash de senha.
2. Login compara o hash e verifica se o usuário está ativo.
3. JWT assinado identifica o usuário e expira; o padrão é 60 minutos.
4. Rotas privadas validam Bearer Token e consultam o usuário atual.
5. Consultas restringem recursos pelo dono, e operações empresariais exigem CNPJ.

`SECRET_KEY` é obrigatória por ambiente, possui tamanho mínimo de 32 caracteres e rejeita marcadores conhecidos de configuração. Hashes usam PBKDF2-HMAC-SHA256 com salt e 600.000 iterações. A aplicação não armazena credenciais de banco ou de WhatsApp.

O CP1 não entrega infraestrutura de produção. Evoluções de segurança para o CP3 incluem gestão de segredos, HTTPS no ambiente de deploy, limitação de requisições, observabilidade, proteção e verificação de webhooks, renovação/revogação de sessões e políticas de retenção de dados.

## Banco e migrations

O padrão é `sqlite:///./finchat.db`, executado a partir da raiz do projeto. O Alembic cria e versiona o schema com `python -m alembic upgrade head`; a API não depende de criar tabelas informalmente ao iniciar.

`DATABASE_URL` permite selecionar PostgreSQL com o driver psycopg: `postgresql+psycopg://usuario:senha@host:5432/finchat`. O modelo é preparado para esse dialeto, mas a validação local usa SQLite. Uma instância PostgreSQL real deve ser provisionada e testada antes de uma implantação com esse banco. Trocar a URL não transfere dados de SQLite para PostgreSQL.

O seed popula dados fictícios e pode ser repetido sem duplicar seus registros. Testes usam banco separado; não devem depender do estado do arquivo `finchat.db`.

## Execução opcional com Docker

O `Dockerfile` usa a imagem oficial Python 3.11 sobre Debian slim, instala as dependências fixadas e inclui a aplicação, migrations e testes. O processo roda com UID/GID 10001, sem root. O `.dockerignore` e as cópias explícitas excluem segredos locais, bancos, logs e o ambiente virtual da imagem.

O `compose.yaml` define o serviço `api`, recebe `SECRET_KEY` por ambiente e publica `127.0.0.1:8080` na porta interna 8000. `FINCHAT_PORT` permite mudar a porta externa. O script `scripts/docker_start.py` aplica a migration e substitui o processo por Uvicorn, permitindo encerramento por sinal. Um healthcheck consulta `/health`.

SQLite continua como banco SQL: `/app/data/finchat.db` é persistido no volume nomeado `finchat_finchat_data`. O volume é independente do arquivo SQLite da execução Python local. Reinícios e recriações preservam os dados; o seed é executado explicitamente por `docker compose exec api python -m app.seed`. O fuso do container é `America/Sao_Paulo`.

Esta configuração usa um único processo da API e não inclui servidor PostgreSQL nem múltiplas réplicas. A execução Python local e a configuração PostgreSQL existentes continuam disponíveis. Comandos completos e orientação para Docker Desktop estão no README.

## Integrações simuladas

### Provedor bancário

`app/integrations/bank_provider.py` define a fronteira para importação bancária. A implementação do CP1 devolve três fixtures de transação com identificadores externos estáveis. A aplicação cria movimentações compatíveis com o usuário e evita reimportação pelo par conta/identificador externo. A conexão mantém status, consentimento simulado, identificador fictício e última sincronização.

No CP3, um provedor poderá conversar com um sandbox oficial e mapear sua resposta para esse contrato. Consentimento real, credenciais, expiração, retentativas e verificação de origem precisam ser implementados nessa evolução. Não existe comunicação externa nesta entrega.

### Provedor de comandos

`app/integrations/whatsapp_provider.py` prepara a fronteira conversacional. Nesta fase, `POST /api/v1/chat/commands` recebe comandos diretamente por HTTP. O interpretador reconhece um conjunto pequeno de frases em português e solicita aos serviços consultas ou criação de transações.

Não há webhook, envio de mensagem, scraping, automação de WhatsApp Web ou LLM. A futura Cloud API oficial deve autenticar e verificar as requisições recebidas, resolver o usuário com segurança e então reutilizar os serviços existentes.

## Contrato HTTP e documentação

O prefixo é `/api/v1`; saúde também fica disponível em `/health`. Swagger em `/docs`, ReDoc em `/redoc` e OpenAPI em `/openapi.json` são gerados a partir das rotas e schemas. O título é `FinChat API` e a autenticação Bearer aparece em **Authorize**.

Sucessos usam `message` e `data`; falhas usam `error.code`, `error.message` e `error.details`. O tratamento global cobre validação, regras de negócio, autorização, conflitos e exceções inesperadas. Erros `500` não expõem detalhes internos ao cliente. Listas são paginadas por `limit` e `offset`; `PUT` permite atualização parcial, sujeita à validação do estado final.

## Estratégia de verificação

A suíte Pytest cobre os fluxos principais e suas negações: autenticação, usuários inativos, isolamento por dono, CPF/CNPJ, compatibilidade financeira, precisão e saldo, CRUDs, filtros, repetição da sincronização e comandos do chat. A verificação manual local complementa a suíte ao executar migrations, repetir o seed, iniciar Uvicorn e consultar `/health`, `/docs` e o contrato OpenAPI.

Os resultados devem ser registrados após a execução efetiva; este documento descreve o desenho e os critérios de validação, sem substituir a saída dos testes.

## Referências técnicas

- [FastAPI: autenticação Bearer e JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/).
- [SQLAlchemy: SQLite, tipos e chaves estrangeiras](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html).
- [FastAPI: construção e execução com Docker](https://fastapi.tiangolo.com/deployment/docker/).
- [Docker Compose: configuração de variáveis de ambiente](https://docs.docker.com/compose/how-tos/environment-variables/set-environment-variables/).

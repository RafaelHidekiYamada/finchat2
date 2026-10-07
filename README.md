# 1. FinChat — Dashboard e Assistente Financeiro Inteligente

Projeto acadêmico: **Checkpoint 2 (CP2)**. Aplicação full stack para organizar finanças pessoais e empresariais, com backend FastAPI, frontend React, dashboard consolidado e análise educacional via Ollama local com fallback determinístico. Banco e WhatsApp continuam simulados e nenhuma credencial bancária é armazenada.

## 2. Descrição

O FinChat reúne contas, categorias, receitas, despesas e consultas financeiras. Pessoas físicas usam o perfil CPF; empresas usam o perfil CNPJ, que também permite gerenciar clientes, fornecedores e contratos. O frontend consome exclusivamente a API autenticada. O chat legado continua local; a nova área **Análise inteligente** usa somente agregados financeiros minimizados.

## 3. Problema escolhido

Pessoas e pequenos negócios nem sempre registram movimentações, distinguem dinheiro de transações bancárias ou acompanham pagamentos de contratos. Ferramentas com muitas telas e cadastros podem dificultar a continuidade desse controle.

## 4. Público-alvo

- Pessoas físicas que precisam acompanhar orçamento, gastos em dinheiro e saldo consolidado.
- Microempreendedores e pequenos negócios que precisam organizar receitas, despesas, clientes, fornecedores e contratos.
- Integrantes e avaliadores do projeto acadêmico, usando dados fictícios de demonstração.

## 5. Solução proposta

Uma API autenticada concentra os registros e regras de negócio. O dashboard fornece dados reais em uma chamada, o frontend oferece os fluxos de gestão e o adaptador de IA gera orientação educacional sem poder escrever no banco.

**As conexões bancárias, consentimentos e importações são simulações. O chat não recebe nem envia mensagens reais. Não são necessárias credenciais de WhatsApp ou de bancos.**

## 6. Funcionalidades do CP1 preservadas e evolução CP2

- Cadastro CPF/CNPJ, login JWT Bearer e consulta do próprio perfil.
- CRUD de contas, categorias e transações, com isolamento por usuário.
- Movimentações em dinheiro, saldo por conta e resumo consolidado.
- Filtros de transações por período, tipo, categoria, conta, parceiro e contrato.
- CRUD e resumos financeiros de parceiros e contratos para usuários CNPJ.
- Conexão bancária fictícia e sincronização idempotente de três movimentações demonstrativas por conta.
- Chat local para `saldo`, `resumo do mês`, `gastei 50 em alimentação` e `recebi 200 por serviço`.
- Banco relacional, migration Alembic, seed idempotente e testes Pytest.
- Documentação Swagger/OpenAPI e ReDoc, com erros padronizados.
- Paginação, filtros e ordenação de transações com limite máximo de 100.
- Dashboard consolidado com saldo, fluxo mensal, categorias, alertas e contas.
- Visão empresarial com contratos ativos, vencimentos e parceiros de maior movimentação.
- Frontend React/TypeScript responsivo com login, cadastro, CRUDs e rotas por perfil.
- Análise financeira estruturada via Ollama local, com minimização de dados e fallback por regras determinísticas.
- Migration CP2 com índices compostos e integridade adicional de parceiros.

## 7. Evolução e escopo futuro

| Etapa | Escopo |
| --- | --- |
| CP1 — preservado | Backend, banco, API REST, regras, autenticação, simulações, testes e Swagger. |
| CP2 — esta entrega | Frontend, dashboard real, API otimizada, banco revisado, testes e análise via LLM. |
| CP3 | WhatsApp Cloud API oficial, Open Finance/sandbox com consentimento, notificações, relatórios avançados, melhorias de segurança e deploy. |

Credenciais bancárias, verificações de webhook, autorização do titular, rate limiting e requisitos de produção ficam para o CP3. A análise do CP2 não exige chave ou serviço de IA pago.

## 8. Regras de negócio

- `document_type` é `CPF` ou `CNPJ`. Documento, e-mail e WhatsApp são normalizados e únicos. CPF/CNPJ passam por validação de formato e dígitos verificadores; isso não verifica titularidade.
- Documentos são armazenados apenas com dígitos. WhatsApp aceita máscaras e `+`, com 10 a 15 dígitos. E-mails são normalizados.
- Senhas usam PBKDF2-HMAC-SHA256 com salt e 600.000 iterações. Usuários inativos não podem fazer login nem acessar rotas privadas.
- Todas as referências financeiras devem pertencer ao usuário autenticado. Recursos de outros usuários não ficam disponíveis por adivinhação de ID.
- Valores de transação devem ser positivos, com até duas casas decimais. Use strings decimais nos payloads, como `"50.00"`. CP1 aceita apenas BRL.
- O domínio usa `Decimal`. PostgreSQL usa `Numeric(14, 2)`; SQLite armazena centavos inteiros para preservar precisão. Dinheiro não passa por `float`.
- Categoria e transação devem ter o mesmo tipo: `INCOME` ou `EXPENSE`.
- Origens: `MANUAL`, `CASH` ou `BANK`. Conciliação: `PENDING` ou `RECONCILED`; alterar a conciliação não altera o saldo.
- Saldo de uma conta = saldo inicial + receitas vinculadas − despesas vinculadas.
- Saldo consolidado = soma dos saldos iniciais das contas + todas as receitas − todas as despesas, incluindo dinheiro e registros sem conta.
- Um resumo com período limita as movimentações, mas mantém os saldos iniciais das contas. Não representa um saldo histórico de fechamento nem transporta automaticamente movimentações anteriores ao período.
- CPF não pode acessar as rotas empresariais de parceiros e contratos; a API retorna `403`.
- Parceiro `CLIENT` só pode receber vínculos de receita; `SUPPLIER`, de despesa. O tipo do contrato precisa ser compatível com o parceiro e com a transação.
- Ao informar um contrato e omitir o parceiro da transação, o parceiro é inferido do contrato. Quando ambos são informados, devem corresponder.
- Atualizações de tipos não podem tornar referências existentes incompatíveis. Exclusão de contas, categorias, parceiros ou contratos em uso retorna `409`; transações podem ser excluídas.
- Os endpoints `PUT` aceitam atualização parcial: campos omitidos mantêm seu valor. A possibilidade de enviar `null` depende do schema do campo.

Detalhamento: [regras de negócio](docs/regras_de_negocio.md).

## 9. Tecnologias utilizadas

| Tecnologia | Uso |
| --- | --- |
| Python 3.11+ | Linguagem do backend |
| FastAPI e Uvicorn | API REST, servidor e documentação OpenAPI |
| Pydantic | Validação de entrada, saída e configuração |
| SQLAlchemy | Modelos, relacionamentos, consultas e persistência |
| SQLite | Banco local padrão |
| PostgreSQL e psycopg | Alternativa configurável por `DATABASE_URL` |
| Alembic | Versionamento do schema do banco |
| JWT Bearer | Autenticação das rotas privadas |
| Pytest | Testes automatizados do backend |
| React, TypeScript e Vite | Frontend e build de produção |
| Tailwind CSS | Design system responsivo |
| React Router e Axios | Rotas, autenticação e cliente HTTP centralizado |
| Recharts | Gráficos do dashboard |
| Ollama | Execução local do modelo de linguagem, sem chave paga |
| Regras determinísticas | Fallback financeiro reproduzível e sempre disponível |
| Vitest e Testing Library | Testes básicos do frontend |
| Docker e Docker Compose | Execução opcional da API com SQLite em volume persistente |

As dependências estão em [requirements.txt](requirements.txt). [requirements-lock.txt](requirements-lock.txt) registra as versões exatas verificadas em Python 3.11 no Windows e no container Linux. A execução local e a suíte usam SQLite; o suporte a PostgreSQL é configurável, mas não equivale a uma validação contra uma instância PostgreSQL real.

## 10. Arquitetura atual

```text
finchat/
├── app/
│   ├── api/              # Rotas REST e dependências de autenticação
│   ├── core/             # Configuração, segurança e erros
│   ├── db/               # Base declarativa e sessões
│   ├── models/           # Entidades e relacionamentos
│   ├── schemas/          # Contratos Pydantic de entrada e saída
│   ├── repositories/     # Consultas e acesso ao banco
│   ├── services/         # Regras e operações de negócio
│   ├── integrations/     # Interfaces e provedores simulados
│   ├── main.py           # Aplicação FastAPI
│   └── seed.py           # Dados fictícios idempotentes
├── alembic/              # Migrations
├── docs/                 # Documentação e apresentação
├── frontend/             # React, TypeScript, Vite, Tailwind e testes
├── tests/                # Testes automatizados
├── scripts/docker_start.py # Migrations e inicialização no container
├── Dockerfile
├── compose.yaml
├── .dockerignore
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

Fluxo: React → Axios/JWT → rota/schema → serviço → repositório/modelos → banco. O Ollama recebe somente o payload agregado pelo serviço e, se estiver indisponível, o mesmo payload é processado por regras locais. Consulte [arquitetura do CP2](docs/arquitetura_cp2.md), [otimizações](docs/otimizacoes_api_cp2.md), [revisão do banco](docs/revisao_banco_cp2.md) e [LLM](docs/llm_cp2.md).

## 11. Diagrama das entidades

```mermaid
erDiagram
    User ||--o{ BankAccount : possui
    User ||--o{ BankConnection : possui
    User ||--o{ Category : define
    User ||--o{ Transaction : registra
    User ||--o{ Partner : cadastra
    User ||--o{ Contract : gerencia
    User ||--o{ ChatCommandLog : executa
    BankAccount ||--o| BankConnection : recebe
    BankAccount o|--o{ Transaction : movimenta
    Category ||--o{ Transaction : classifica
    Partner ||--o{ Contract : participa
    Partner o|--o{ Transaction : referencia
    Contract o|--o{ Transaction : agrupa
```

`Transaction` sempre tem usuário e categoria; conta, parceiro e contrato são opcionais. Parceiros e contratos pertencem a usuários CNPJ.

## 12. Instalação no Windows

Para obter o projeto pelo GitHub:

```powershell
git clone https://github.com/RafaelHidekiYamada/finchat2.git
cd finchat2
```

O README, `app/`, `compose.yaml` e os demais arquivos ficam na raiz do repositório. Após clonar, execute os comandos nessa pasta; os caminhos absolutos `finchat` mostrados abaixo são exemplos do ambiente original. Para usar Docker, siga a opção da seção 16; para execução Python local, siga os passos a seguir.

Pré-requisitos: Python 3.11+ e Node.js 20+ com npm. Abra o PowerShell na pasta do projeto:

```powershell
cd "C:\caminho\para\finchat2"
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
Copy-Item .env.example .env
```

Se a versão instalada for superior a 3.11, use `py -3 --version` para conferir e `py -3 -m venv .venv` para criar o ambiente. Ajuste o caminho do `cd` se copiar o projeto para outra pasta. Os comandos usam o executável do ambiente diretamente; não é necessário ativá-lo ou alterar a política de execução do PowerShell. Copie `.env.example` apenas na primeira configuração, preservando um `.env` já configurado.

## 13. Configuração do `.env`

O arquivo [.env.example](.env.example) lista a configuração local. Gere uma chave própria:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copie o valor gerado para `JWT_SECRET_KEY` no `.env`. Exemplo:

```dotenv
DATABASE_URL=sqlite:///./finchat.db
JWT_SECRET_KEY=SUBSTITUA_POR_UMA_CHAVE_ALEATORIA_DE_PELO_MENOS_32_CARACTERES
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ORIGINS=http://localhost:5173
LLM_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:1b
OLLAMA_TIMEOUT_SECONDS=300
VITE_AI_REQUEST_TIMEOUT_MS=310000
```

**A chave JWT acima é um marcador, não uma configuração utilizável.** `JWT_SECRET_KEY` é obrigatória, exige pelo menos 32 caracteres e não aceita marcadores conhecidos. `SECRET_KEY` continua aceito somente para compatibilidade com o CP1. `LLM_ENABLED=false` desativa apenas a tentativa de usar o Ollama; as regras determinísticas continuam funcionando.

Para executar sem Docker, instale o [Ollama](https://ollama.com/download), abra o aplicativo e baixe o modelo uma vez:

```powershell
ollama pull gemma3:1b
```

Se o Ollama não estiver instalado ou iniciado, a rota de análise continua respondendo por meio do fallback determinístico.

Para uma instância PostgreSQL preparada por você, substitua a URL por:

```dotenv
DATABASE_URL=postgresql+psycopg://usuario:senha@localhost:5432/finchat
```

Os valores dessa URL são ilustrativos. O projeto não cria servidor PostgreSQL nem migra automaticamente dados de SQLite. Execute as migrations no banco escolhido.

## 14. Executar migrations

Na raiz `finchat`, com `.env` configurado:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

O comando cria o schema do banco selecionado. Consulte a revisão aplicada com:

```powershell
.\.venv\Scripts\python.exe -m alembic current
```

Mantenha o diretório de execução em `finchat`, pois o caminho padrão do SQLite é relativo a ele. A API não substitui o fluxo de migrations.

## 15. Popular dados de demonstração

```powershell
.\.venv\Scripts\python.exe -m app.seed
```

O seed é idempotente: pode ser executado novamente sem duplicar seus dados de demonstração. Inclui usuários, categorias, contas e transações; no perfil CNPJ, também parceiros e contratos.

| Perfil | E-mail | Documento fictício | Senha fictícia |
| --- | --- | --- | --- |
| CPF | `cpf@finchat.demo` | `52998224725` | `FinChatDemo!2026` |
| CNPJ | `empresa@finchat.demo` | `11222333000181` | `FinChatDemo!2026` |

Os números servem somente como exemplos que passam na validação de dígitos; não representam uma confirmação de identidade ou titularidade. Categorias de demonstração incluem Alimentação, Transporte, Moradia, Salário, Vendas, Serviços e Fornecedores.

## 16. Iniciar a API

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

A API ficará em `http://127.0.0.1:8000`. Em outro PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Use `Ctrl+C` para encerrar. `--reload` é destinado ao desenvolvimento local.

### Iniciar o frontend

Em outro PowerShell:

```powershell
cd frontend
Copy-Item .env.example .env
npm.cmd install
npm.cmd run dev
```

Abra `http://localhost:5173`. `VITE_API_BASE_URL` deve apontar para `http://localhost:8000/api/v1`. Para gerar a versão de produção:

```powershell
npm.cmd test
npm.cmd run build
```

Se a porta estiver ocupada, acrescente `--port 8010` ao comando e acesse `http://127.0.0.1:8010/docs`. Na verificação desta entrega, as portas 8000 e 8001 já estavam ocupadas, portanto foi usada a porta **8010**.

### Executar com Docker no Windows

Esta é uma alternativa à instalação Python local: requer **Docker Desktop iniciado, usando containers Linux**, com Docker Compose. O Compose inicia a API, o Ollama e baixa o modelo configurado automaticamente; o banco continua sendo **SQLite SQL**. Não é necessário criar containers, imagens, modelos ou volumes manualmente no aplicativo.

Na pasta do projeto, mantenha o `.env` com `JWT_SECRET_KEY` configurado. O Compose desta entrega executa a API; rode o frontend separadamente com Vite.

```powershell
docker run --rm python:3.11-slim-bookworm python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copie a saída para `JWT_SECRET_KEY` no `.env`. Depois execute:

```powershell
cd "C:\caminho\para\finchat2"
docker compose up -d --build --wait
docker compose exec api python -m app.seed
```

Na primeira execução, o comando também baixa o modelo `gemma3:1b`, otimizado para uso local em CPU, o que pode levar alguns minutos. Depois ele constrói a API, aplica `alembic upgrade head`, inicia Uvicorn e aguarda o healthcheck. O segundo comando popula os dados fictícios de demonstração e pode ser repetido sem duplicação.

- [Swagger no Docker](http://127.0.0.1:8080/docs)
- [ReDoc no Docker](http://127.0.0.1:8080/redoc)
- [Saúde da API no Docker](http://127.0.0.1:8080/health)

Os usuários e senhas são os mesmos da seção 15. A porta padrão é **8080**, publicada somente em `127.0.0.1`. Para alterar, defina `FINCHAT_PORT=8081` no `.env`, execute `docker compose up -d` novamente e ajuste a URL. A porta interna continua 8000. O container usa o fuso `America/Sao_Paulo`, preservando as datas locais dos comandos e do seed.

**Persistência:** o Compose usa `sqlite:////app/data/finchat.db` no volume `finchat_finchat_data` e armazena os modelos no volume `finchat_ollama_data`. O banco começa separado do `finchat.db` da execução Python local; reiniciar ou recriar os containers mantém registros e modelo. A variável `DATABASE_URL` do `.env` continua disponível para execução local; no Compose, o caminho SQLite é definido explicitamente.

Comandos de operação:

```powershell
docker compose ps
docker compose logs --tail 100 api
docker compose logs --tail 100 ollama
docker compose exec api python -m pytest -q -p no:cacheprovider
docker compose stop
docker compose start --wait
```

Para remover somente o container e a rede, use `docker compose down`; o volume e seus dados são preservados. **`docker compose down --volumes` também remove o banco**, portanto não o use para apenas parar a aplicação.

No Docker Desktop, o projeto aparece em **Containers → finchat**, com os serviços `api`, `ollama` e `ollama-model`. O aplicativo permite consultar logs e parar/iniciar os serviços; as configurações já estão no `compose.yaml`. Se ocorrer erro de conexão com `dockerDesktopLinuxEngine`, abra o Docker Desktop e aguarde o mecanismo ficar pronto. Em máquinas ainda sem WSL 2 ou virtualização configurados, siga a configuração inicial solicitada pelo próprio Docker Desktop.

O processo roda como usuário sem privilégios de administrador. `.env`, banco local, logs e `.venv` ficam fora da imagem. O seed é uma ação explícita, e não é executado automaticamente a cada reinício.

## 17. Swagger e autenticação

- [Swagger: http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- [ReDoc: http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- [OpenAPI JSON](http://127.0.0.1:8000/openapi.json)

No Swagger, abra `POST /api/v1/auth/login`, clique em **Try it out** e envie JSON:

```json
{
  "email": "cpf@finchat.demo",
  "password": "FinChatDemo!2026"
}
```

A resposta contém `data.access_token`, `data.token_type` e `data.expires_in`. Copie apenas o valor de `access_token`, clique em **Authorize**, cole o token e confirme. O esquema Bearer acrescenta o prefixo ao cabeçalho. Em clientes HTTP, envie `Authorization: Bearer SEU_TOKEN`. O prazo padrão é 60 minutos; faça login novamente quando expirar. O cadastro devolve o usuário sem expor sua senha ou hash.

## 18. Principais endpoints e exemplos

As rotas da tabela usam o prefixo **`/api/v1`**. Autenticação é exigida, exceto em cadastro, login e saúde. Recursos empresariais exigem CNPJ.

| Grupo | Método e caminho |
| --- | --- |
| Autenticação | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| Contas | `POST /bank-accounts`, `GET /bank-accounts`, `GET /bank-accounts/{id}`, `PUT /bank-accounts/{id}`, `DELETE /bank-accounts/{id}`, `GET /bank-accounts/{id}/balance` |
| Conexões simuladas | `POST /bank-connections`, `GET /bank-connections`, `POST /bank-connections/{id}/sync` |
| Categorias | `POST /categories`, `GET /categories`, `GET /categories/{id}`, `PUT /categories/{id}`, `DELETE /categories/{id}` |
| Transações | `POST /transactions`, `GET /transactions`, `GET /transactions/{id}`, `PUT /transactions/{id}`, `DELETE /transactions/{id}`, `POST /transactions/cash`, `GET /transactions/summary` |
| Dashboard | `GET /dashboard/overview` |
| Análise inteligente | `POST /ai/financial-analysis` |
| Parceiros — CNPJ | `POST /partners`, `GET /partners`, `GET /partners/{id}`, `PUT /partners/{id}`, `DELETE /partners/{id}`, `GET /partners/{id}/financial-summary` |
| Contratos — CNPJ | `POST /contracts`, `GET /contracts`, `GET /contracts/{id}`, `PUT /contracts/{id}`, `DELETE /contracts/{id}`, `GET /contracts/{id}/financial-summary` |
| Chat simulado | `POST /chat/commands` |
| Saúde pública | `GET /health` (também disponível em `/health`, sem prefixo) |

As listagens legadas retornam a lista em `data` e aceitam `limit/offset`, com máximo 100. Transações também aceitam `page`, `page_size` (máximo 100), período, tipo, categoria, conta, `sort_by` e `order`; nesse modo retornam `data` e `meta`. Use sempre IDs do próprio usuário.

Cadastro de um usuário, se não estiver usando o seed:

```json
{
  "name": "Pessoa de Demonstração",
  "email": "pessoa@example.com",
  "whatsapp": "+55 (11) 99999-0003",
  "document": "111.444.777-35",
  "document_type": "CPF",
  "password": "MinhaSenhaDemo!2026"
}
```

Conta bancária (`POST /bank-accounts`):

```json
{
  "institution": "Banco Fictício CP1",
  "nickname": "Conta principal",
  "account_type": "CHECKING",
  "initial_balance": "1000.00"
}
```

Tipos de conta: `CHECKING`, `SAVINGS` e `PAYMENT`. Categoria (`POST /categories`):

```json
{
  "name": "Lazer",
  "type": "EXPENSE"
}
```

Despesa (`POST /transactions`; use IDs do seu próprio usuário):

```json
{
  "description": "Almoço de demonstração",
  "amount": "50.00",
  "date": "2026-09-07",
  "type": "EXPENSE",
  "category_id": 1,
  "bank_account_id": 1,
  "origin": "MANUAL",
  "reconciliation_status": "PENDING"
}
```

Para receita, use `INCOME` e uma categoria de receita. Para dinheiro, use `POST /transactions/cash` com os campos da movimentação e sem conta bancária; a origem é `CASH`. No CNPJ, `partner_id` e `contract_id` são vínculos opcionais. A categoria do exemplo precisa ser de despesa.

Os filtros de `GET /transactions` e `GET /transactions/summary` são `start_date`, `end_date`, `type`, `category_id`, `bank_account_id`, `contract_id` e `partner_id`. Datas usam `YYYY-MM-DD`; os limites de período são inclusivos. Exemplo: `/api/v1/transactions?start_date=2026-09-01&end_date=2026-09-30&type=EXPENSE&limit=20&offset=0`. Resumos não alteram nem conciliam registros.

Parceiro CNPJ (`POST /partners`):

```json
{
  "name": "Cliente fictício de demonstração",
  "type": "CLIENT"
}
```

Contrato (`POST /contracts`, substituindo o ID pelo cliente criado):

```json
{
  "title": "Prestação de serviço fictícia",
  "partner_id": 1,
  "type": "INCOME",
  "expected_amount": "1000.00",
  "start_date": "2026-09-01",
  "end_date": "2026-12-31",
  "status": "ACTIVE"
}
```

Use `SUPPLIER` e `EXPENSE` para um contrato de fornecedor. O valor previsto não pode ser negativo e não cria movimentação automática.

O seed já cria uma conexão para cada conta de demonstração: consulte `GET /bank-connections` e use o ID retornado em `POST /bank-connections/{id}/sync`. Para uma conta nova ainda sem conexão, use `POST /bank-connections`:

```json
{
  "bank_account_id": 1
}
```

Cada conta aceita uma conexão simulada. A instituição vem da conta; status, consentimento fictício e identificador externo são preenchidos pelo serviço. Execute `POST /bank-connections/{id}/sync`. O provedor retorna três fixtures fictícias com identificadores externos estáveis; a resposta contém `imported_count` e `transactions`. Sincronizar novamente a mesma conta não duplica movimentações existentes. Uma transação importada excluída pode ser recriada na próxima sincronização; conta e origem de importações existentes não podem ser alteradas.

No chat, envie um comando por vez em `POST /chat/commands`:

```json
{
  "command": "gastei 50 em alimentação"
}
```

São exemplos aceitos:

```text
saldo
resumo do mês
gastei 50 em alimentação
recebi 200 por serviço
```

Os comandos financeiros registram dinheiro (`CASH`), sem conta bancária, usando a data local de execução e categorias do usuário. O seed prepara Alimentação e Serviços para esses exemplos. Valor precisa ser positivo, com até duas casas decimais; categoria desconhecida ou comando não reconhecido retorna `400`. A resposta contém `action`, `reply` e, conforme o comando, `transaction` ou `summary`. O chat não chama LLMs ou serviços de mensageria.

Respostas de sucesso seguem o envelope:

```json
{
  "message": "Transação criada com sucesso.",
  "data": {}
}
```

Erros seguem:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Recurso não encontrado.",
    "details": []
  }
}
```

| HTTP | Significado |
| --- | --- |
| `400` | Regra de negócio ou comando inválido |
| `401` | Autenticação ausente, inválida, expirada ou usuário inativo |
| `403` | Perfil sem permissão para a funcionalidade |
| `404` | Recurso não encontrado ou indisponível ao usuário |
| `409` | Conflito de unicidade ou recurso ainda em uso |
| `422` | Payload ou parâmetro inválido |
| `500` | Erro interno; detalhes técnicos não são expostos ao cliente |

## 19. Executar os testes

```powershell
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm.cmd test
npm.cmd run build
```

A suíte do backend usa banco isolado e não chama serviços externos reais: o adaptador Ollama é simulado nos testes e o fallback determinístico é exercitado diretamente. Ela cobre CP1, dashboard, paginação, índices, vencimentos, sanitização da IA e falhas controladas. A validação CP2 aprovou **93 testes de backend**. O frontend aprovou **2 testes** de proteção de rota e renderização do dashboard; o build TypeScript/Vite valida a aplicação completa.

Também são verificados migrations em SQLite temporário, seed idempotente, `/health`, Swagger, login, dashboard, CRUD financeiro, área CNPJ, resposta estruturada do Ollama e fallback determinístico. Consulte as evidências em `docs/evidencias/` e a [auditoria de conformidade do CP2](docs/evidencias/auditoria_cp2_2026-10-06.md).

O Docker continua executando a API sem root, com migrations automáticas e SQLite em volume. O frontend é executado separadamente nesta entrega.

## 20. Integrantes do grupo

**Turma: 1TIAPF**

| Integrante | RM |
| --- | --- |
| Rafael Yamada | 571041 |
| Lethícia Dias | 571431 |
| Lucas Santos | 572695 |
| Yuri Yoshigue | 571217 |

## 21. Organização no Trello ou Notion

**Link do quadro:** `https://trello.com/b/v6yK2Ik4/ruizstartup`.

Sugestão de colunas e cartões do CP2: [docs/trello_notion_cp2.md](docs/trello_notion_cp2.md). Roteiro de demonstração: [docs/roteiro_apresentacao_cp2.md](docs/roteiro_apresentacao_cp2.md).

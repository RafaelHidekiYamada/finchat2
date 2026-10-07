# Regras de negócio — FinChat CP1

Este documento descreve as regras do backend local. Contas, instituições, transações importadas e mensagens da demonstração são fictícias. O CP1 não processa pagamentos nem conecta contas bancárias reais.

## 1. Identidade e acesso

1. Cada usuário possui exatamente um perfil: `CPF` ou `CNPJ`.
2. Documento, e-mail e WhatsApp são normalizados antes da consulta e persistência. São únicos no sistema; duplicidade retorna `409`.
3. CPF e CNPJ aceitam máscara e são persistidos somente com dígitos. A validação inclui comprimento e dígitos verificadores, rejeitando sequências inválidas. Não existe consulta cadastral externa ou verificação de titularidade.
4. WhatsApp aceita `+` e caracteres de máscara, conservando de 10 a 15 dígitos após normalização. O cadastro não verifica se o número tem uma conta WhatsApp.
5. Senhas não são persistidas em texto puro. O hash usa PBKDF2-HMAC-SHA256 com salt por senha e 600.000 iterações.
6. Login recebe JSON com `email` e `password`. O retorno contém token JWT Bearer e tempo de expiração; o padrão é 60 minutos.
7. `SECRET_KEY` deve ser configurada por ambiente, ter pelo menos 32 caracteres e não ser um marcador de exemplo. Tokens expirados, inválidos e usuários inativos não acessam rotas privadas.
8. A identidade vem do token validado. Payloads de recursos não autorizam escolher o dono por um `user_id` arbitrário.
9. Todas as consultas e alterações ficam limitadas ao usuário autenticado. Recursos de outro usuário retornam `404`, evitando expor sua existência.

## 2. Contas bancárias e conexões

Uma conta pertence a um único usuário e contém instituição, apelido, tipo (`CHECKING`, `SAVINGS` ou `PAYMENT`) e saldo inicial. O saldo inicial é a referência informada para começar o controle; receitas e despesas alteram o saldo calculado:

```text
saldo da conta = saldo inicial + receitas vinculadas − despesas vinculadas
```

Transações sem conta não entram no saldo individual de nenhuma conta. Alterar o saldo inicial modifica os cálculos futuros; o CP1 não mantém uma trilha contábil de versões desse valor.

Conexões bancárias guardam instituição, status, data de consentimento simulado, última sincronização e identificador externo fictício. Pertencem ao usuário e a uma conta dele; cada conta aceita no máximo uma conexão simulada. Na criação, informe `bank_account_id`; a instituição vem da conta e os demais metadados são preenchidos pelo serviço. O consentimento registrado serve apenas à demonstração e não representa autorização de Open Finance.

O sincronizador importa três transações fictícias estáveis por conta e utiliza identificadores externos para impedir duplicação de registros existentes em novas sincronizações. O mesmo conjunto pode ser demonstrado em contas diferentes. Se uma transação importada for excluída, a próxima sincronização poderá importá-la novamente. Conta e origem de uma importação existente não podem ser alteradas. Nunca é solicitada senha bancária ou token real. A sincronização exige conexão ativa e atualiza a informação da última execução.

## 3. Categorias

Categorias pertencem ao usuário e têm nome e tipo `INCOME` (receita) ou `EXPENSE` (despesa). Toda transação precisa de uma categoria do mesmo tipo. Uma categoria referenciada não pode ter seu tipo alterado de forma a invalidar as transações existentes e não pode ser excluída enquanto estiver em uso.

O seed inclui categorias para demonstração, como Alimentação, Transporte, Moradia, Salário, Vendas, Serviços e Fornecedores. O chat procura categorias do usuário; não usa categorias de outra pessoa nem cria silenciosamente uma categoria desconhecida.

## 4. Transações e dinheiro

| Campo ou conceito | Regra |
| --- | --- |
| Dono | Sempre o usuário autenticado |
| Descrição e data | Descrição da movimentação e data no formato `YYYY-MM-DD` |
| Valor | Maior que zero, com no máximo duas casas decimais |
| Moeda | Apenas BRL no CP1 |
| Tipo | `INCOME` ou `EXPENSE` |
| Categoria | Obrigatória, do mesmo usuário e compatível com o tipo |
| Conta bancária | Opcional, sempre do mesmo usuário |
| Origem | `BANK`, `CASH` ou `MANUAL` |
| Conciliação | `PENDING` ou `RECONCILED` |
| Parceiro e contrato | Opcionais, restritos ao perfil CNPJ e ao mesmo usuário |

Valores monetários são tratados com `Decimal`, sem conversão para `float`. No PostgreSQL, a coluna usa `Numeric(14, 2)`; no SQLite, um tipo de persistência armazena centavos inteiros e reconstrói `Decimal`. Envie valores como strings decimais, por exemplo `"12.90"`.

Conciliação é uma classificação operacional: os dois status participam dos cálculos. Alterar `PENDING` para `RECONCILED` não representa uma nova entrada nem saída. Registros em dinheiro usam a origem `CASH` e não podem informar conta bancária. A origem `BANK` exige uma conta, enquanto `MANUAL` permite conta opcional. O endpoint `/transactions/cash` define a origem `CASH` independentemente da origem enviada.

Atualização e exclusão exigem que a transação pertença ao usuário autenticado. Ao atualizar campos relacionados, a combinação final é validada novamente; não basta verificar apenas cada campo isolado. Transações podem ser excluídas, refletindo imediatamente nos resumos.

## 5. Consultas e cálculo financeiro

```text
total de receitas = soma das transações INCOME
total de despesas = soma das transações EXPENSE
saldo consolidado = soma dos saldos iniciais + total de receitas − total de despesas
```

O consolidado inclui movimentações de todas as contas e também as sem conta, como dinheiro. Ele não deve ser calculado somando apenas os saldos bancários, pois isso omitiria dinheiro.

A consulta de transações permite `start_date`, `end_date`, `type`, `category_id`, `bank_account_id`, `contract_id` e `partner_id`, combinados por interseção. Os limites de data são inclusivos; período com início posterior ao fim é inválido. Listagens aceitam `limit` (padrão 100, entre 1 e 500) e `offset` (padrão 0, não negativo).

O resumo oferece totais e movimentações agrupadas em `by_category`, com tipo e total de cada categoria, permitindo identificar os gastos nas categorias `EXPENSE`. Ao selecionar um período, somente as movimentações do período compõem os totais; os saldos iniciais continuam considerados. Ao filtrar uma conta, somente seu saldo inicial entra no cálculo. Esse resultado **não é um fechamento histórico**: não acumula receitas e despesas anteriores ao início do período.

Exemplo: duas contas com saldos iniciais de R$ 100,00 e R$ 200,00, receita de R$ 500,00 e despesa em dinheiro de R$ 50,00 resultam em saldo consolidado de R$ 750,00. A despesa em dinheiro reduz o consolidado sem modificar o saldo de uma conta específica.

## 6. Perfil CPF

O perfil CPF pode gerenciar contas, conexões simuladas, categorias e transações, registrar dinheiro, consultar resumos e utilizar o chat. Todas as rotas de parceiros e contratos, incluindo listagens e resumos, são bloqueadas com `403`. O CPF também não pode contornar essa regra informando vínculos empresariais em transações.

## 7. Perfil CNPJ, parceiros e contratos

O perfil CNPJ recebe as funcionalidades pessoais e as operações empresariais.

| Parceiro | Tipo financeiro permitido |
| --- | --- |
| `CLIENT` — cliente | `INCOME` — receita |
| `SUPPLIER` — fornecedor | `EXPENSE` — despesa |

Cada contrato pertence ao usuário e referencia um parceiro dele. Contém título (`title`), tipo (`type`: `INCOME`/`EXPENSE`), valor previsto não negativo (`expected_amount`), início (`start_date`), término opcional (`end_date`) e status `ACTIVE`, `COMPLETED` ou `CANCELLED`. A data final não pode anteceder a inicial. O tipo deve ser compatível com o parceiro.

Uma transação pode informar somente parceiro, somente contrato ou ambos. Se informar apenas contrato, o serviço infere seu parceiro. Se informar ambos, o parceiro precisa ser o do contrato. Tipo da transação, categoria, parceiro e contrato devem ser compatíveis.

Alterações em parceiro e contrato verificam as referências existentes. Não se pode trocar um cliente com receitas vinculadas para fornecedor ou mudar um contrato de forma que suas transações deixem de ser compatíveis. O status do contrato descreve seu ciclo de vida; receitas e despesas registradas continuam compondo os resumos.

Resumos de parceiro e contrato mostram `total_income`, `total_expenses`, `received`, `paid` e `balance` (`receitas − despesas`). Recebido equivale às receitas registradas e pago às despesas, sem depender da conciliação. `expected_amount` é a previsão do contrato ou a soma das previsões dos contratos do parceiro, incluindo seus diferentes status. `outstanding_amount` é o maior valor entre zero e `previsto − receitas − despesas`; não representa uma cobrança bancária ou conta a pagar gerada automaticamente. Previsão não cria uma transação e não entra no saldo consolidado. Como os tipos são compatíveis com um único lado financeiro, um cliente normalmente apresenta receitas e um fornecedor, despesas.

## 8. Chat simulado

O endpoint `POST /api/v1/chat/commands` é interno e autenticado. Recebe `{"command": "saldo"}` e devolve uma resposta estruturada com `action`, `reply` e `transaction` ou `summary`, conforme a operação. Não envia mensagens ao número cadastrado.

| Comando | Efeito |
| --- | --- |
| `saldo` | Consulta o saldo consolidado do usuário |
| `resumo do mês` | Consulta as movimentações do mês corrente |
| `gastei 50 em alimentação` | Registra despesa na categoria Alimentação do usuário |
| `recebi 200 por serviço` | Registra receita na categoria Serviços do usuário |

O interpretador usa regras determinísticas para os comandos previstos, com tratamento de acentos e dos exemplos em português. Não é um assistente de linguagem geral. Valores devem ser positivos, com até duas casas; categorias não reconhecidas ou incompatíveis e comandos não suportados retornam `400`. Operações de criação usam as mesmas validações financeiras do CRUD, a origem `CASH` sem conta e a data local da execução. Há registro básico dos comandos bem-sucedidos para rastreabilidade da demonstração, sem mensageria externa.

## 9. Atualização, exclusão e erros

Os endpoints `PUT` aceitam atualização parcial. Campos omitidos são mantidos e o estado resultante precisa continuar válido. Campos obrigatórios não passam a aceitar `null` por isso; consulte o schema para limpar um vínculo opcional.

Contas, categorias, parceiros e contratos referenciados não são apagados em cascata para contornar integridade: a exclusão retorna `409`. Remova ou ajuste os vínculos permitidos antes. Transações são excluíveis pelo próprio dono.

Sucesso usa `{ "message": "...", "data": ... }`. Erros usam `{ "error": { "code": "...", "message": "...", "details": [] } }`. Os códigos HTTP são `400` para regra inválida, `401` para autenticação, `403` para perfil sem permissão, `404` para recurso indisponível, `409` para conflito, `422` para validação e `500` para falha interna. Respostas `500` não revelam SQL, caminhos internos ou rastreamento de exceções.

## 10. Limites desta fase

O CP2 inclui frontend React, dashboard consolidado e análise financeira com Ollama local e fallback determinístico. Não há pagamento, consulta de titularidade, câmbio, conciliação bancária automática real, consulta Open Finance ou envio de WhatsApp. PostgreSQL é configurável, mas a validação local usa SQLite. O CP3 poderá incorporar provedores oficiais, consentimento, notificações, relatórios e preparação para produção.

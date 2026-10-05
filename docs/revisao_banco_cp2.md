# Revisão do banco de dados — CP2

## Entidades

`users` é a raiz de propriedade. `bank_accounts`, `categories`, `transactions`, `partners`, `contracts`, `bank_connections` e `chat_command_logs` carregam `user_id`. Transações referenciam categoria obrigatória e, opcionalmente, conta, parceiro e contrato.

## Normalização

- Categorias são entidades por usuário e tipo; o nome não é copiado para transações.
- Instituição pertence à conta. A conexão simulada mantém o retrato necessário para integração, sem credenciais.
- Parceiros concentram clientes e fornecedores com um discriminador.
- Contratos referenciam parceiros; transações podem referenciar contrato e parceiro para rastreabilidade.
- Valores usam `Money`: centavos inteiros em SQLite e `NUMERIC(14,2)` em PostgreSQL. `float` é rejeitado.

## Integridade

- E-mail, WhatsApp e documento do usuário são únicos.
- Índices únicos garantem documento e e-mail de parceiro únicos dentro do usuário; `NULL` continua permitido.
- Categoria é única por usuário, nome e tipo.
- Identificador bancário simulado é único por conta.
- FKs usam `RESTRICT`; a aplicação devolve 409 para recurso em uso.
- `amount > 0`, `expected_amount >= 0` e `end_date >= start_date` são constraints do banco.
- Serviços verificam que conta, categoria, parceiro e contrato pertencem ao mesmo usuário.

## Índices adicionados pela migration `0002`

| Índice | Finalidade |
| --- | --- |
| `ix_transactions_user_date` | dashboard e filtros cronológicos |
| `ix_transactions_user_account_category` | filtros combinados por proprietário, conta e categoria |
| `ix_contracts_user_status` | contagem de contratos ativos |
| `ix_contracts_user_end_date` | vencimentos próximos |
| `ix_partners_user_type` | resumos de clientes e fornecedores |

## Migração segura

`0002_cp2_indexes_integrity` somente adiciona índices. Não apaga nem transforma dados e não precisa recriar tabelas no SQLite. O downgrade remove apenas os índices criados no CP2. Em bases que já contenham parceiros duplicados, a duplicidade deve ser saneada antes do upgrade para que os índices únicos possam ser aplicados.

## Evolução sobre o CP1

O CP1 já possuía FKs, constraints monetárias, unicidade do usuário e índices simples. O CP2 acrescenta índices alinhados às consultas reais, unicidade de contato de parceiros e testes automatizados que inspecionam os índices e exercitam os conflitos.

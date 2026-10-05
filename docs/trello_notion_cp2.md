# Estrutura sugerida para Trello ou Notion — CP2

## Colunas

1. **Backlog CP2** — histórias ainda não priorizadas.
2. **Pronto para desenvolver** — critérios de aceite definidos.
3. **Em desenvolvimento** — responsável e branch registrados.
4. **Em revisão** — PR, testes e evidências anexados.
5. **Validação integrada** — frontend/API/banco em conjunto.
6. **Concluído CP2** — aceite e documentação completos.
7. **Roadmap CP3** — integrações reais e melhorias futuras.

## Cartões sugeridos

| Cartão | Checklist principal | Evidência |
| --- | --- | --- |
| Paginação de transações | filtros, ordenação, máximo 100, isolamento | testes CP2 + Swagger |
| Dashboard consolidado | agregados CPF, CNPJ, alertas, contas | tela + endpoint |
| Revisão do banco | migration, índices, constraints, downgrade | Alembic + documento |
| Autenticação frontend | login, cadastro, logout, 401, proteção | testes React |
| Gestão financeira | transações, contas, categorias, detalhe | demonstração E2E |
| Área empresarial | parceiros, contratos, bloqueio CPF | testes 403 + tela CNPJ |
| Análise inteligente | payload mínimo, schema, erros, disclaimer | testes de provider |
| Qualidade frontend | loading, vazio, erro, responsividade, build | Vitest + build |
| Documentação | README, arquitetura, banco, API, LLM | revisão do grupo |
| Apresentação | roteiro, dados demo, tempo 6–8 min | ensaio gravado |

## Modelo de cartão

- **Objetivo:** resultado observável, em uma frase.
- **Responsável:** uma pessoa.
- **Critérios de aceite:** itens verificáveis.
- **Dependências:** cartões ou decisões anteriores.
- **Riscos:** privacidade, compatibilidade, prazo.
- **Testes:** comandos e cenários.
- **Evidências:** link de PR, screenshot, Swagger ou log.
- **Definição de pronto:** código revisado, testes verdes e documentação atualizada.

## Etiquetas

`backend`, `frontend`, `banco`, `segurança`, `IA`, `documentação`, `teste`, `bloqueado` e `CP3`.

O quadro informado pelo grupo permanece: <https://trello.com/b/v6yK2Ik4/ruizstartup>.

# graphiti-memory — regras do fork

`CLAUDE.md` na raiz é espelho do upstream (getzep/graphiti) e não se edita: tudo que é
nosso mora aqui. Correção de fato: o guia do MCP citado lá vive em
`mcp_server/docs/cursor_rules.md`.

## Edição

- **Copie o idioma local mesmo quando ruim** (naming, transporte de erro, logger, estilo
  de teste, docstring). Não refatore linha que o pedido não tocou — cada linha alterada em
  código do upstream é conflito no próximo `/fork-sync`.
- **Arquivo fora do escopo pedido → sinalize e espere aprovação** antes de editar.

## Contexto de fork

- `origin` = fabiosiqueira/graphiti; `upstream` = getzep/graphiti. `main` espelha o
  upstream; a branch de trabalho e de deploy é `local/all-fixes`.
- Cada mudança nossa nasce numa branch `fix/…`/`feat/…` e entra em `local/all-fixes` por
  `merge: carry <branch>`. Mudança direta em `local/all-fixes` perde a rota de volta ao
  upstream. Reconciliação: `/fork-sync`.
- Issues do fork estão desativadas; issue é sempre do upstream.

## Testes (o que `make test` não diz)

- `make test` na raiz **trava sem Neo4j local**: `test_edge_int`/`test_node_int` não têm
  marker `integration`, e `test_add_triplet.py`/`test_graphiti_mock.py` parametrizam por
  provider. `DISABLE_NEO4J=1` (upstream, `helpers_test.py`) tira o provider e os pula. Gate
  unitário real está em `.claude/done.md` §Stages (`-k "not _int"` + `DISABLE_*=1`).
- `mcp_server/.venv` resolve `graphiti-core` do **PyPI**, não do fork. Teste que depende de
  mudança nossa no core falha com `TypeError: unexpected keyword` até aplicar o overlay, o
  mesmo que o `Dockerfile.fork` faz:
  `cd mcp_server && uv pip install --python .venv/bin/python --no-deps -e ..`
  (`uv sync` desfaz; repita depois de sincronizar).
- `mcp_server/` é pacote próprio: testes rodam de dentro dele (`uv run --no-sync pytest`),
  com `sys.path.insert(0, 'src')` no topo de cada arquivo — copie o cabeçalho de um teste
  vizinho, não invente conftest.
- Teste novo de carry vai em `mcp_server/tests/test_<assunto>.py`, um assunto por arquivo,
  com docstring de módulo dizendo qual contrato ele pina.

## Idioma do fork

- Docstring de módulo e comentário inline explicam o **porquê** da decisão, não o quê
  (ex.: `utils/http_auth.py` justifica ASGI puro vs `BaseHTTPMiddleware`, path exato vs
  prefixo). Código sem justificativa da escolha não passa no `/issue-qa`.
- Único, 100 colunas, ruff + pyright — o do upstream. `mcp_server` usa pyright `standard`.

## Runtime

- `llm.reasoning` (config do MCP) manda no esforço de reasoning; sem valor explícito,
  `factories.reasoning_effort_for_model` decide por família de modelo, e gpt-5.5 roda com
  reasoning **off** por custo. Medição de qualidade pendente no STATE.md.
- Deploy é Coolify com `Dockerfile.fork` (sem stack torch); nunca o `Dockerfile` do
  upstream. Config em `.claude/done.md`.

# /done — config (graphiti-memory, fork de getzep/graphiti)

Onboarding 2026-09-05. Auditoria `/claude-md` feita em 2026-09-04: CLAUDE.md fica como
espelho do upstream; regras do fork em `.claude/rules/fork.md`.

## Deploy
backend: coolify-git
prod-uuid: k653injkiktg1t4vi8spbyip        # app `graphiti-mcp`, build pack dockerfile
build-context: https://github.com/fabiosiqueira/graphiti   # branch local/all-fixes
dockerfile: /mcp_server/docker/Dockerfile.fork
coolify-mcp: coolify-prod
fqdn: https://graphiti-mcp.fabiosiqueira.dev
deploy-host: (não declarado — host Coolify 10.0.1.1 sem alias ssh conhecido; app sem basicauth, patch §5.4 não se aplica)
deploy-autonomo: nenhum
# Branch de deploy é `local/all-fixes`, NÃO main: main espelha o upstream; merge de feature
# vai para local/all-fixes.

## Tracking
backend: none                              # fork com issues desativadas; upstream é getzep/graphiti

## Stages
tests: .=DISABLE_NEO4J=1 DISABLE_FALKORDB=1 DISABLE_KUZU=1 DISABLE_NEPTUNE=1 uv run pytest tests -q -m "not integration" -k "not _int" -p no:cacheprovider, mcp_server=uv run --no-sync pytest tests -q -m "not integration" -k "not _int" --ignore=tests/test_async_operations.py --ignore=tests/test_cross_encoder_factory.py --ignore=tests/test_stress_load.py
# `make test` trava sem Neo4j local: test_edge_int/test_node_int não têm marker integration
# e o driver fica em retry de conexão (medido 2026-09-05, 10min a 0% CPU). Unit = -k "not _int".
# DISABLE_NEO4J=1 (helpers_test.py do upstream) tira o provider da parametrização: sem ela,
# test_add_triplet/test_graphiti_mock travam do mesmo jeito (medido 2026-09-04, 10min).
# mcp_server: o venv resolve graphiti-core do PyPI; testes que dependem do core do fork
# (ex. kwarg `reasoning`) só passam com o overlay editable — ver .claude/rules/fork.md §Testes.
# version: inaplicável — o fork acompanha a versão do upstream (pyproject) e a tag mcp-vX é
# do release do mcp_server, não bump por rodada.

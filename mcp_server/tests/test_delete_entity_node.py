"""Unit tests for the delete_entity_node MCP tool.

Deleting an entity node is the only way to drop a summary that graphiti-core consolidated on
the node itself: delete_entity_edge removes the fact but leaves the summary text behind. The
tool is destructive and takes its fact edges with it (DETACH DELETE), so these tests pin the
fail-closed contract: the node must belong to the requested group, checked by comparing
group_id explicitly — on Neo4j the per-group driver clone is a no-op and offers no isolation.
A refusal never reaches node.delete().
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import graphiti_mcp_server as server


@pytest.fixture(autouse=True)
def fresh_group_drivers(monkeypatch):
    monkeypatch.setattr(server, '_group_drivers', {})


class FakeDriver:
    """Returns a distinct driver per database, like FalkorDB's clone()."""

    def __init__(self, database: str = 'default_db'):
        self.database = database

    def clone(self, database: str):
        return FakeDriver(database=database)


class FakeNode:
    def __init__(self, uuid: str, group_id: str, calls: list):
        self.uuid = uuid
        self.group_id = group_id
        self.calls = calls

    async def delete(self, driver):
        self.calls.append(('delete', driver.database))


def install(monkeypatch, *, node_group: str, default_group_id: str | None = 'main', facts=2):
    calls: list = []
    client = SimpleNamespace(driver=FakeDriver())
    monkeypatch.setattr(
        server, 'graphiti_service', SimpleNamespace(get_client=lambda: _async_return(client))
    )
    monkeypatch.setattr(
        server,
        'config',
        SimpleNamespace(graphiti=SimpleNamespace(group_id=default_group_id)),
        raising=False,
    )

    async def fake_get_node(driver, uuid):
        calls.append(('get', driver.database))
        return FakeNode(uuid, node_group, calls)

    async def fake_get_edges(driver, node_uuid):
        return [object()] * facts

    monkeypatch.setattr(server.EntityNode, 'get_by_uuid', staticmethod(fake_get_node))
    monkeypatch.setattr(server.EntityEdge, 'get_by_node_uuid', staticmethod(fake_get_edges))
    return calls


async def _async_return(value):
    return value


async def test_deletes_node_of_the_requested_group_on_its_driver(monkeypatch):
    calls = install(monkeypatch, node_group='group-y', facts=3)

    response = await server.delete_entity_node('uuid-1', group_id='group-y')

    assert calls == [('get', 'group-y'), ('delete', 'group-y')]
    assert 'deleted successfully' in response['message']
    assert '3 fact(s)' in response['message']


async def test_refuses_node_of_another_group_without_deleting(monkeypatch):
    calls = install(monkeypatch, node_group='group-x')

    response = await server.delete_entity_node('uuid-1', group_id='group-y')

    assert ('delete', 'group-y') not in calls
    assert all(call[0] != 'delete' for call in calls)
    assert 'group-x' in response['error']


async def test_falls_back_to_default_group_and_still_compares(monkeypatch):
    calls = install(monkeypatch, node_group='other', default_group_id='main')

    response = await server.delete_entity_node('uuid-1')

    assert all(call[0] != 'delete' for call in calls)
    assert 'error' in response


async def test_refuses_all_groups_wildcard(monkeypatch):
    calls = install(monkeypatch, node_group='*')

    response = await server.delete_entity_node('uuid-1', group_id=server.ALL_GROUPS)

    assert calls == []
    assert 'error' in response


async def test_refuses_when_no_group_is_known(monkeypatch):
    calls = install(monkeypatch, node_group='', default_group_id=None)

    response = await server.delete_entity_node('uuid-1')

    assert calls == []
    assert 'error' in response

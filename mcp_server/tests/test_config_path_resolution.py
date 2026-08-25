#!/usr/bin/env python3
"""Unit tests for where the YAML config path comes from.

`config.schema` reads `$CONFIG_PATH` to pick the YAML file, and the shipped
Docker Compose files set that variable — but the CLI parser used to overwrite it
with argparse's own default on every run, so the variable never took effect. It
only looked like it worked because the default and the container's value named
the same file. Point a container at a different config and it silently loaded
the packaged one instead: wrong database, wrong models, no error.

These pin the precedence that makes the variable real: CLI > env > packaged
default.
"""

import sys
from pathlib import Path

# Add the src directory to the path (mirrors the other unit tests)
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import graphiti_mcp_server as server  # noqa: E402

PACKAGED = Path('/pkg/config/config.yaml')


def test_cli_flag_wins_over_environment():
    resolved = server.resolve_config_path(
        Path('/cli/chosen.yaml'), {'CONFIG_PATH': '/env/other.yaml'}, PACKAGED
    )
    assert resolved == '/cli/chosen.yaml'


def test_environment_is_used_when_no_flag():
    """The case that was broken: a container sets the variable and nothing else."""
    resolved = server.resolve_config_path(None, {'CONFIG_PATH': '/env/other.yaml'}, PACKAGED)
    assert resolved == '/env/other.yaml'


def test_packaged_default_when_neither_is_set():
    assert server.resolve_config_path(None, {}, PACKAGED) == str(PACKAGED)


def test_empty_environment_value_falls_back():
    """An unset-but-present variable must not resolve to the empty path."""
    assert server.resolve_config_path(None, {'CONFIG_PATH': ''}, PACKAGED) == str(PACKAGED)

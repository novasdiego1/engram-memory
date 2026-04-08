"""Tests for workspace isolation in entity conflict detection.

Verifies that SQLiteStorage filters entity conflict queries by workspace_id,
preventing cross-workspace false positives in Tier 0 and Tier 2b detection.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
import pytest_asyncio

from engram.storage import SQLiteStorage


def _make_fact(
    scope: str = "auth",
    entities: list | None = None,
    workspace_id: str | None = None,
) -> dict:
    """Build a minimal fact dict for insertion."""
    now = datetime.now(timezone.utc).isoformat()
    fact = {
        "id": uuid.uuid4().hex,
        "lineage_id": uuid.uuid4().hex,
        "content": f"test fact {uuid.uuid4().hex[:8]}",
        "content_hash": uuid.uuid4().hex,
        "scope": scope,
        "confidence": 0.9,
        "fact_type": "observation",
        "agent_id": "agent-1",
        "engineer": None,
        "provenance": None,
        "keywords": "[]",
        "entities": json.dumps(entities or []),
        "artifact_hash": None,
        "embedding": None,
        "embedding_model": "test",
        "embedding_ver": "1.0",
        "committed_at": now,
        "valid_from": now,
        "valid_until": None,
        "ttl_days": None,
        "memory_op": "add",
        "supersedes_fact_id": None,
        "durability": "durable",
    }
    if workspace_id is not None:
        fact["workspace_id"] = workspace_id
    return fact


@pytest_asyncio.fixture
async def ws_alpha(tmp_path: Path):
    """Storage instance for workspace 'alpha'."""
    s = SQLiteStorage(db_path=tmp_path / "shared.db", workspace_id="alpha")
    await s.connect()
    yield s
    await s.close()


@pytest_asyncio.fixture
async def ws_beta(tmp_path: Path):
    """Storage instance for workspace 'beta', sharing the same database file."""
    s = SQLiteStorage(db_path=tmp_path / "shared.db", workspace_id="beta")
    await s.connect()
    yield s
    await s.close()


@pytest.mark.asyncio
async def test_find_entity_conflicts_isolated_by_workspace(ws_alpha, ws_beta):
    """Tier 0: entity conflicts must not leak across workspaces."""
    entity = {"name": "rate_limit", "type": "numeric", "value": 500}

    # Insert a fact with rate_limit=500 in workspace alpha
    fact_a = _make_fact(scope="auth", entities=[entity], workspace_id="alpha")
    await ws_alpha.insert_fact(fact_a)

    # Insert a fact with rate_limit=1000 in workspace beta (different value)
    entity_b = {"name": "rate_limit", "type": "numeric", "value": 1000}
    fact_b = _make_fact(scope="auth", entities=[entity_b], workspace_id="beta")
    await ws_beta.insert_fact(fact_b)

    # From workspace alpha's perspective, searching for conflicts against
    # rate_limit=1000 should NOT find fact_a (different workspace).
    conflicts_from_beta = await ws_beta.find_entity_conflicts(
        entity_name="rate_limit",
        entity_type="numeric",
        entity_value="1000",
        scope="auth",
        exclude_id=fact_b["id"],
    )
    assert len(conflicts_from_beta) == 0, (
        "Workspace beta must not see workspace alpha's facts as conflicts"
    )

    # From workspace alpha's perspective, searching for conflicts against
    # rate_limit=500 should also NOT find fact_b.
    conflicts_from_alpha = await ws_alpha.find_entity_conflicts(
        entity_name="rate_limit",
        entity_type="numeric",
        entity_value="500",
        scope="auth",
        exclude_id=fact_a["id"],
    )
    assert len(conflicts_from_alpha) == 0, (
        "Workspace alpha must not see workspace beta's facts as conflicts"
    )


@pytest.mark.asyncio
async def test_find_entity_conflicts_within_same_workspace(ws_alpha):
    """Tier 0: conflicts within the same workspace must still be detected."""
    entity_500 = {"name": "rate_limit", "type": "numeric", "value": 500}
    entity_1000 = {"name": "rate_limit", "type": "numeric", "value": 1000}

    fact_1 = _make_fact(scope="auth", entities=[entity_500], workspace_id="alpha")
    await ws_alpha.insert_fact(fact_1)

    fact_2 = _make_fact(scope="auth", entities=[entity_1000], workspace_id="alpha")
    await ws_alpha.insert_fact(fact_2)

    conflicts = await ws_alpha.find_entity_conflicts(
        entity_name="rate_limit",
        entity_type="numeric",
        entity_value="1000",
        scope="auth",
        exclude_id=fact_2["id"],
    )
    assert len(conflicts) == 1, "Conflict within the same workspace must be detected"
    assert conflicts[0]["id"] == fact_1["id"]


@pytest.mark.asyncio
async def test_cross_scope_entity_matches_isolated_by_workspace(ws_alpha, ws_beta):
    """Tier 2b: cross-scope entity matches must not leak across workspaces."""
    entity = {"name": "rate_limit", "type": "numeric", "value": 500}

    # Insert in workspace alpha, scope=auth
    fact_a = _make_fact(scope="auth", entities=[entity], workspace_id="alpha")
    await ws_alpha.insert_fact(fact_a)

    # Insert in workspace beta, scope=payments (different scope AND workspace)
    entity_b = {"name": "rate_limit", "type": "numeric", "value": 1000}
    fact_b = _make_fact(scope="payments", entities=[entity_b], workspace_id="beta")
    await ws_beta.insert_fact(fact_b)

    # Beta should not find alpha's fact in cross-scope search
    matches_from_beta = await ws_beta.find_cross_scope_entity_matches(
        entity_name="rate_limit",
        entity_type="numeric",
        entity_value="1000",
        exclude_id=fact_b["id"],
    )
    assert len(matches_from_beta) == 0, (
        "Workspace beta must not see workspace alpha's facts in cross-scope matches"
    )


@pytest.mark.asyncio
async def test_cross_scope_entity_matches_within_same_workspace(ws_alpha):
    """Tier 2b: cross-scope matches within the same workspace must still work."""
    entity_500 = {"name": "rate_limit", "type": "numeric", "value": 500}
    entity_1000 = {"name": "rate_limit", "type": "numeric", "value": 1000}

    fact_auth = _make_fact(scope="auth", entities=[entity_500], workspace_id="alpha")
    await ws_alpha.insert_fact(fact_auth)

    fact_payments = _make_fact(scope="payments", entities=[entity_1000], workspace_id="alpha")
    await ws_alpha.insert_fact(fact_payments)

    matches = await ws_alpha.find_cross_scope_entity_matches(
        entity_name="rate_limit",
        entity_type="numeric",
        entity_value="1000",
        exclude_id=fact_payments["id"],
    )
    assert len(matches) == 1, "Cross-scope match within the same workspace must be detected"
    assert matches[0]["id"] == fact_auth["id"]

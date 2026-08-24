from __future__ import annotations

import asyncio

from eval.enterprise_runtime_fixtures import (
    DB_PATH,
    Runtime,
    _hash_schema,
    controlled_action_and_hitl_matrix,
    production_retrieval_on_contract_kb,
    provision,
)


def test_enterprise_fixture_schema_is_stable_and_evaluation_owned() -> None:
    assert DB_PATH.name == "eval_enterprise.db"
    assert DB_PATH.parent.name == "data"
    assert len(_hash_schema()) == 64


def test_enterprise_action_and_hitl_controls_use_real_services() -> None:
    async def run() -> dict[str, object]:
        runtime: Runtime = await provision()
        try:
            with production_retrieval_on_contract_kb():
                return await controlled_action_and_hitl_matrix(runtime)
        finally:
            await runtime.engine.dispose()

    result = asyncio.run(run())

    assert result["ticket_status"] == "PASS"
    assert result["close_ticket"] == "closed"
    assert result["reopen_ticket"] == "waiting_for_agent"
    assert result["approval_result"] == "in_progress"

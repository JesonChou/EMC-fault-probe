from __future__ import annotations

from pathlib import Path

import pytest
from emc_core.domain.events import AgentEvent, AgentEventType
from emc_core.domain.session import MessageRole
from emc_core.persistence.jsonl_store import JsonlSessionStore


def test_jsonl_store_creates_lists_and_restores_full_session(tmp_path: Path) -> None:
    store = JsonlSessionStore(tmp_path)
    session = store.create()
    store.append_message(
        session.session_id,
        role=MessageRole.USER,
        content="辐射发射超标怎么办？",
        metadata={"hit_ids": [1, 2], "workspace_path": str(tmp_path)},
    )
    store.append_event(
        session.session_id,
        AgentEvent(
            type=AgentEventType.TOOL_COMPLETED,
            session_id=session.session_id,
            step=1,
            data={"tool_name": "search_cases", "output": "两条案例"},
        ),
    )
    store.append_message(
        session.session_id,
        role=MessageRole.ASSISTANT,
        content="建议检查屏蔽。",
        thinking="先判断干扰路径。",
    )

    restored = store.load(session.session_id)
    summaries = store.list_summaries()

    assert len(restored.messages) == 2
    assert restored.messages[0].metadata == {
        "hit_ids": [1, 2],
        "workspace_path": str(tmp_path),
    }
    assert restored.messages[1].thinking == "先判断干扰路径。"
    assert restored.events[0].session_id == session.session_id
    assert summaries[0].title == "辐射发射超标怎么办？"
    assert summaries[0].turns == 1
    assert summaries[0].workspace_path == str(tmp_path)


def test_jsonl_store_skips_corrupt_trailing_line(tmp_path: Path) -> None:
    store = JsonlSessionStore(tmp_path)
    session = store.create()
    path = tmp_path / f"{session.session_id}.jsonl"
    with path.open("a", encoding="utf-8") as stream:
        stream.write('{"type":"message"')

    assert store.load(session.session_id).session_id == session.session_id


def test_jsonl_store_rejects_path_traversal(tmp_path: Path) -> None:
    store = JsonlSessionStore(tmp_path)

    with pytest.raises(ValueError, match="session_id"):
        store.load("../other-file")

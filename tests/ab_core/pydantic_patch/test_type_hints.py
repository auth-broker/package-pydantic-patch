from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from ab_core.pydantic_patch.core.type_hints import get_resolved_type_hints


class RecursiveForwardRefModel(BaseModel):
    id: UUID | None = None
    children: list[RecursiveForwardRefModel] = []


def test_get_resolved_type_hints_handles_recursive_forward_refs() -> None:
    hints = get_resolved_type_hints(RecursiveForwardRefModel)

    assert "id" in hints
    assert "children" in hints
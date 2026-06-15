from __future__ import annotations

from sqlalchemy.orm import registry
from sqlmodel import Field, Relationship, SQLModel

from ab_core.pydantic_patch.orm_patch import recursive_patch_orm_scalar
from ab_core.pydantic_patch.patch import Patch, PatchConfig

mapper_registry = registry()


class ForeignKeySyncSQLModel(SQLModel, registry=mapper_registry):
    __abstract__ = True


class TreeNode(ForeignKeySyncSQLModel, table=True):
    __tablename__ = "orm_patch_fk_sync_tree_node"

    id: int | None = Field(default=None, primary_key=True)
    parent_id: int | None = Field(
        default=None,
        foreign_key="orm_patch_fk_sync_tree_node.id",
    )

    name: str = ""
    sort_order: int = 0

    parent: TreeNode | None = Relationship(
        back_populates="children",
        sa_relationship_kwargs={
            "remote_side": "TreeNode.id",
        },
    )
    children: list[TreeNode] = Relationship(back_populates="parent")


TreeNodePatch = Patch[TreeNode](
    name="TreeNodeForeignKeySyncPatch",
    pick={
        "id",
        "parent_id",
        "name",
        "sort_order",
        "children",
    },
    partial={
        "id",
        "parent_id",
        "name",
        "sort_order",
        "children",
    },
    child_models={
        TreeNode: PatchConfig(
            pick={
                "id",
                "parent_id",
                "name",
                "sort_order",
                "children",
            },
            partial={
                "id",
                "parent_id",
                "name",
                "sort_order",
                "children",
            },
        ),
    },
)


def test_recursive_patch_orm_scalar_reparents_nested_child_when_foreign_key_changes() -> None:
    source_parent = TreeNode(id=10, parent_id=1, name="Source parent", sort_order=0)
    target_parent = TreeNode(id=11, parent_id=1, name="Target parent", sort_order=1)
    child = TreeNode(id=100, parent_id=10, name="Child", sort_order=0)

    root = TreeNode(
        id=1,
        name="Root",
        children=[
            source_parent,
            target_parent,
        ],
    )
    source_parent.children = [child]

    patch = TreeNodePatch(
        id=1,
        children=[
            {
                "id": 10,
                "children": [
                    {
                        "id": 100,
                        "parent_id": 11,
                        "sort_order": 2,
                        "name": "Moved child",
                    }
                ],
            }
        ],
    )

    recursive_patch_orm_scalar(root, patch)

    assert child.parent_id == 11
    assert child.parent is target_parent
    assert child not in source_parent.children
    assert child in target_parent.children

    assert source_parent.children == []
    assert target_parent.children == [child]

    assert child.name == "Moved child"
    assert child.sort_order == 2


def test_recursive_patch_orm_scalar_can_reparent_to_none_when_foreign_key_is_nullable() -> None:
    source_parent = TreeNode(id=10, parent_id=1, name="Source parent")
    child = TreeNode(id=100, parent_id=10, name="Child")

    root = TreeNode(
        id=1,
        name="Root",
        children=[source_parent],
    )
    source_parent.children = [child]

    patch = TreeNodePatch(
        id=1,
        children=[
            {
                "id": 10,
                "children": [
                    {
                        "id": 100,
                        "parent_id": None,
                    }
                ],
            }
        ],
    )

    recursive_patch_orm_scalar(root, patch)

    assert child.parent_id is None
    assert child.parent is None
    assert child not in source_parent.children
    assert source_parent.children == []


def test_recursive_patch_orm_scalar_keeps_existing_relationship_when_foreign_key_is_unchanged() -> None:
    source_parent = TreeNode(id=10, parent_id=1, name="Source parent")
    child = TreeNode(id=100, parent_id=10, name="Child", sort_order=0)

    root = TreeNode(
        id=1,
        name="Root",
        children=[source_parent],
    )
    source_parent.children = [child]

    patch = TreeNodePatch(
        id=1,
        children=[
            {
                "id": 10,
                "children": [
                    {
                        "id": 100,
                        "parent_id": 10,
                        "sort_order": 5,
                    }
                ],
            }
        ],
    )

    recursive_patch_orm_scalar(root, patch)

    assert child.parent_id == 10
    assert child.parent is source_parent
    assert source_parent.children == [child]
    assert child.sort_order == 5


class Project(ForeignKeySyncSQLModel, table=True):
    __tablename__ = "orm_patch_fk_sync_project"

    id: int | None = Field(default=None, primary_key=True)
    name: str = ""

    milestones: list[Milestone] = Relationship(back_populates="project")


class Milestone(ForeignKeySyncSQLModel, table=True):
    __tablename__ = "orm_patch_fk_sync_milestone"

    id: int | None = Field(default=None, primary_key=True)
    project_id: int | None = Field(
        default=None,
        foreign_key="orm_patch_fk_sync_project.id",
    )

    name: str = ""

    project: Project | None = Relationship(back_populates="milestones")
    tasks: list[Task] = Relationship(back_populates="milestone")


class Task(ForeignKeySyncSQLModel, table=True):
    __tablename__ = "orm_patch_fk_sync_task"

    id: int | None = Field(default=None, primary_key=True)
    milestone_id: int | None = Field(
        default=None,
        foreign_key="orm_patch_fk_sync_milestone.id",
    )

    title: str = ""

    milestone: Milestone | None = Relationship(back_populates="tasks")


ProjectPatch = Patch[Project](
    name="ProjectForeignKeySyncPatch",
    pick={
        "id",
        "name",
        "milestones",
    },
    partial={
        "id",
        "name",
        "milestones",
    },
    child_models={
        Milestone: PatchConfig(
            pick={
                "id",
                "project_id",
                "name",
                "tasks",
            },
            partial={
                "id",
                "project_id",
                "name",
                "tasks",
            },
        ),
        Task: PatchConfig(
            pick={
                "id",
                "milestone_id",
                "title",
            },
            partial={
                "id",
                "milestone_id",
                "title",
            },
        ),
    },
)


def test_recursive_patch_orm_scalar_reparents_non_self_referencing_child_when_foreign_key_changes() -> None:
    source_milestone = Milestone(id=10, project_id=1, name="Source milestone")
    target_milestone = Milestone(id=11, project_id=1, name="Target milestone")
    task = Task(id=100, milestone_id=10, title="Original task")

    project = Project(
        id=1,
        name="Website refresh",
        milestones=[
            source_milestone,
            target_milestone,
        ],
    )
    source_milestone.tasks = [task]

    patch = ProjectPatch(
        id=1,
        milestones=[
            {
                "id": 10,
                "tasks": [
                    {
                        "id": 100,
                        "milestone_id": 11,
                        "title": "Moved task",
                    }
                ],
            }
        ],
    )

    recursive_patch_orm_scalar(project, patch)

    assert task.milestone_id == 11
    assert task.milestone is target_milestone
    assert task not in source_milestone.tasks
    assert task in target_milestone.tasks

    assert source_milestone.tasks == []
    assert target_milestone.tasks == [task]

    assert task.title == "Moved task"


def test_recursive_patch_orm_scalar_rejects_foreign_key_move_to_unloaded_target_in_strict_graph_mode() -> None:
    source_milestone = Milestone(id=10, project_id=1, name="Source milestone")
    task = Task(id=100, milestone_id=10, title="Original task")

    project = Project(
        id=1,
        name="Website refresh",
        milestones=[source_milestone],
    )
    source_milestone.tasks = [task]

    patch = ProjectPatch(
        id=1,
        milestones=[
            {
                "id": 10,
                "tasks": [
                    {
                        "id": 100,
                        "milestone_id": 999,
                    }
                ],
            }
        ],
    )

    try:
        recursive_patch_orm_scalar(project, patch)
    except ValueError as exc:
        assert "999" in str(exc)
    else:
        raise AssertionError("Expected missing FK relationship target to raise ValueError")


def teardown_module() -> None:
    mapper_registry.dispose(cascade=True)
    mapper_registry.metadata.clear()
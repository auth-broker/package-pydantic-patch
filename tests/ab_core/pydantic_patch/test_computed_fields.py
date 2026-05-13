import pytest
from pydantic import BaseModel, computed_field
from sqlmodel import Field, Relationship, SQLModel

from ab_core.pydantic_patch.core.errors import ConflictingPatchConfigError, InvalidPatchFieldError
from ab_core.pydantic_patch.omit import Omit, OmitConfig
from ab_core.pydantic_patch.partial import Partial, PartialConfig
from ab_core.pydantic_patch.patch import Patch, PatchConfig
from ab_core.pydantic_patch.pick import Pick, PickConfig
from ab_core.pydantic_patch.required import Required, RequiredConfig
from tests.helpers.assert_model import assert_field_names, assert_optional, get_list_item_type


class Child(BaseModel):
    name: str
    score: int

    @computed_field
    @property
    def label(self) -> str:
        return f"{self.name}: {self.score}"


class Parent(BaseModel):
    title: str
    child: Child
    children: list[Child]

    @computed_field
    @property
    def summary(self) -> str:
        return self.title

    @computed_field
    @property
    def best_child(self) -> Child:
        return self.child

    @computed_field
    @property
    def child_labels(self) -> list[str]:
        return [child.label for child in self.children]


class Milestone(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str | None = None
    project_id: int | None = Field(default=None, foreign_key="project.id")


class Project(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str | None = None

    milestones: list[Milestone] = Relationship()

    @computed_field
    @property
    def label(self) -> str:
        return f"{self.id}: {self.name}"


# Pick

def test_pick_can_include_only_computed_field():
    picked = Pick[Parent](fields={"summary"})

    assert_field_names(picked, {"summary"})



def test_pick_can_include_computed_and_normal_fields():
    picked = Pick[Parent](fields={"title", "summary"})

    assert_field_names(picked, {"title", "summary"})



def test_pick_unknown_computed_field_name_still_raises():
    with pytest.raises(InvalidPatchFieldError):
        Pick[Parent](fields={"not_a_real_computed_field"})



def test_pick_recursively_transforms_computed_field_returning_child_model():
    picked = Pick[Parent](
        fields={"best_child"},
        child_models={Child: PickConfig(fields={"label"})},
    )

    best_child_model = picked.model_fields["best_child"].annotation
    assert_field_names(best_child_model, {"label"})


# Omit

def test_omit_can_remove_computed_field():
    omitted = Omit[Parent](fields={"summary"})

    assert "summary" not in omitted.model_fields
    assert "best_child" in omitted.model_fields



def test_omit_can_remove_child_computed_field():
    omitted = Omit[Parent](child_models={Child: OmitConfig(fields={"label"})})

    child_model = omitted.model_fields["child"].annotation
    children_item_model = get_list_item_type(omitted.model_fields["children"].annotation)

    assert "label" not in child_model.model_fields
    assert "label" not in children_item_model.model_fields


# Partial

def test_partial_includes_computed_fields():
    partial_parent = Partial[Parent]()

    assert "summary" in partial_parent.model_fields
    assert partial_parent.model_fields["summary"].annotation == str | None
    assert_optional(partial_parent, "title")



def test_partial_applies_to_child_computed_fields():
    partial_parent = Partial[Parent](child_models={Child: PartialConfig()})

    child_model = partial_parent.model_fields["child"].annotation
    assert "label" in child_model.model_fields
    assert child_model.model_fields["label"].annotation == str | None


# Required

def test_required_rejects_computed_field():
    with pytest.raises(ConflictingPatchConfigError):
        Required[Parent](fields={"summary"})



def test_required_rejects_child_computed_field():
    with pytest.raises(ConflictingPatchConfigError):
        Required[Parent](child_models={Child: RequiredConfig(fields={"label"})})


# Patch

def test_patch_excludes_computed_fields_by_default():
    patched = Patch[Parent]()

    assert "summary" not in patched.model_fields
    assert "best_child" not in patched.model_fields
    assert "child_labels" not in patched.model_fields



def test_patch_can_pick_computed_field_explicitly():
    patched = Patch[Parent](pick={"summary"})

    assert_field_names(patched, {"summary"})



def test_patch_rejects_required_computed_field():
    with pytest.raises(ConflictingPatchConfigError):
        Patch[Parent](required={"summary"})



def test_patch_transforms_computed_field_returning_child_model_when_picked():
    patched = Patch[
        Parent
    ](pick={"best_child"}, child_models={Child: PatchConfig(pick={"label"})})

    best_child_model = patched.model_fields["best_child"].annotation
    assert_field_names(best_child_model, {"label"})



def test_patch_applies_child_model_config_to_child_computed_fields():
    patched = Patch[Parent](child_models={Child: PatchConfig(pick={"label"})})

    child_model = patched.model_fields["child"].annotation
    children_item_model = get_list_item_type(patched.model_fields["children"].annotation)

    assert_field_names(child_model, {"label"})
    assert_field_names(children_item_model, {"label"})


# SQLModel

def test_sqlmodel_computed_field_is_valid_pick_field():
    picked = Pick[Project](fields={"label"})

    assert_field_names(picked, {"label"})



def test_sqlmodel_relationships_and_computed_fields_are_both_available():
    picked = Pick[Project](fields={"label", "milestones"})

    assert_field_names(picked, {"label", "milestones"})

"""Pydantic model transformation helpers for pick/omit/partial/required/patch."""

try:
    from sqlalchemy.ext.hybrid import hybrid_property
    from sqlmodel import SQLModel
except ImportError:
    pass
else:
    ignored_types = SQLModel.model_config.get("ignored_types", ())
    if hybrid_property not in ignored_types:
        SQLModel.model_config["ignored_types"] = (*ignored_types, hybrid_property)

from ab_core.pydantic_patch.null import Null, NullConfig, create_null_model
from ab_core.pydantic_patch.omit import Omit, OmitConfig, create_omit_model
from ab_core.pydantic_patch.partial import Partial, PartialConfig, create_partial_model
from ab_core.pydantic_patch.patch import Patch, PatchConfig, create_patch_model
from ab_core.pydantic_patch.pick import Pick, PickConfig, create_pick_model
from ab_core.pydantic_patch.required import Required, RequiredConfig, create_required_model

__all__ = [
    "Pick",
    "PickConfig",
    "create_pick_model",
    "Omit",
    "OmitConfig",
    "create_omit_model",
    "Partial",
    "PartialConfig",
    "create_partial_model",
    "Required",
    "RequiredConfig",
    "create_required_model",
    "Patch",
    "PatchConfig",
    "create_patch_model",
    "Null",
    "NullConfig",
    "create_null_model",
]

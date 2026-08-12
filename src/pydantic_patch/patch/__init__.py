"""Patch aggregation operation."""

from pydantic_patch.patch.api import Patch
from pydantic_patch.patch.config import PatchConfig
from pydantic_patch.patch.operation import create_patch_model

__all__ = ["Patch", "PatchConfig", "create_patch_model"]

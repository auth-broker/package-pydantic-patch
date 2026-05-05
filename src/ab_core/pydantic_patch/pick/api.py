"""Public Pick API."""

from collections.abc import Collection
from typing import Generic, TypeVar, cast

from generic_preserver.wrapper import generic_preserver
from generic_preserver.utils import canonical_key
from pydantic import BaseModel

from ab_core.pydantic_patch.pick.config import PickConfig
from ab_core.pydantic_patch.pick.operation import create_pick_model


@generic_preserver
class Pick[T: BaseModel]():
    """Create a model containing only selected fields."""

    def __new__(
        cls,
        *,
        fields: Collection[str] | None = None,
        child_models: dict[type[BaseModel], PickConfig] | None = None,
        name: str | None = None,
    ) -> type[BaseModel]:
        # NOTE: `generic-preserver` allows us to retrieve the type instance passed to the generic class,
        #       which is how we get the source model.
        #
        #       Whilst this is really convenient, `generic-preserver` intended us to access the generic
        #       arg via self[T]. However, since we are in the `__new__` part of the object instantiation
        #       lifecycle, the instance (self) has not yet been created, so we cannot access self[T].
        #
        #       Instead, we can read the `generic-preserver` state directly from the class (cls) via
        #       `cls.__generic_map__`. Since the GenericMeta actually creates a new class for each unique
        #       set of generic args, the `cls` in this context is already the unique class, therefore we
        #       don't need to worry about conflicts between different generic args.
        #
        #       Whilst this isn't ideal, and it should be noted that this isn't how `generic-preserver` is
        #       intended to be used, it works and allows us to have a really clean API for users of our library,
        #       so it's a worthwhile tradeoff IMO.
        #
        #       It should also be noted that this relies on string serialisation of the generic arg (canonical_key(T))
        #       to retrieve the source model, which feels a bit hacky, but important to note that this canonical_key
        #       method comes from the same generic-preserver library, so I don't anticipate it breaking.
        # 
        #       Just being cautious since we've observed this happening between Python 3.11 and 3.12, where the string
        #       serialisation of generic args changed from "~T" to "T", respectively.
        #
        #       However, since this is an internal implementation detail of our library, we can easily update our code
        #       to accommodate any changes in the string serialisation of generic args in future versions of Python, so
        #       it's not a major concern.
        #

        generic_map = cast(
            dict[str, type[BaseModel]],
            getattr(cls, "__generic_map__", None),
        )
        source_model = generic_map[canonical_key(T)]
        return create_pick_model(
            source_model,
            fields=fields,
            child_models=child_models,
            name=name,
        )

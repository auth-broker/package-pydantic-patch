"""Support Pydantic Models as a JSON Serialisable Column in Postgres.

As per: https://github.com/fastapi/sqlmodel/issues/63

This is relatively common requirement that sqlmodel has not implemented for us :(

Basically, we don't always want to use relationships and overcomplicate the ORM. Instead,
we just wwant to serialise the pydantic dependency as JSON withhin that column.

However, if we use JSONB directly, it requires that we define

   supplier_address: dict = Field(
       default_factory=SupplierAddress,
       description="Supplier business address extracted from the quote.",
       sa_column=Column(JSONB, nullable=False),
   )

Which isn't clean, and no long type-driven.

To preserve the type driven nature for these cases, PydanticJSONB is our friend:

   supplier_address: SupplierAddress = Field(
       default_factory=SupplierAddress,
       description="Supplier business address extracted from the quote.",
       sa_column=Column(PydanticJSONB(SupplierAddress), nullable=False),
   )

TODO: This does cause some incompaibility with alembic (I think), so we will need
to address that once alembic is added to this codebase. It looks something like this:

```python
   from typing import TYPE_CHECKING, Any, Literal
   from knowledgeburst.fencing.quote_stateful.pydantic_jsonb import PydanticJSONB

   if TYPE_CHECKING:
       from alembic.autogenerate.api import AutogenContext

   def render_item(
       type_: str,
       obj: Any,  # noqa: ANN401
       autogen_context: AutogenContext,
   ) -> str | Literal[False]:
       if type_ == "type" and isinstance(obj, PydanticJSONB):
           autogen_context.imports.add("import sqlalchemy as sa")
           autogen_context.imports.add("from sqlalchemy.dialects import postgresql")
           return "postgresql.JSONB(astext_type=sa.Text())"
       return False
```

In that case, we probably want to move this module into a more central db module. Right now
it is just coupled with fencing as we are keeping the fencing module as independent as possible.
"""

from typing import Any, cast, override

from pydantic import TypeAdapter
from sqlalchemy import Dialect, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB


class PydanticJSONB[T](TypeDecorator):
   impl = JSONB
   cache_ok = True

   def __init__(self, pydantic_type: type[T]) -> None:
       super().__init__()
       self.adapter = TypeAdapter(pydantic_type)

   @override
   def process_bind_param(self, value: T | None, dialect: Dialect) -> Any:
       if value is None:
           return None
       return self.adapter.dump_python(value, mode="json")

   @override
   def process_result_value(self, value: Any, dialect: Dialect) -> T | None:
       if value is None:
           return None
       return self.adapter.validate_python(value)

   def coerce_compared_value(self, op: Any, value: Any) -> Any:
       return cast(JSONB, self.impl).coerce_compared_value(op, value)

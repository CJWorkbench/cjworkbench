from typing import Any, FrozenSet

from cjwmodule.spec.paramschema import ParamSchema


def gather_param_tab_slugs(schema: ParamSchema, value: Any) -> FrozenSet[str]:
    """Find all tabs nested within `value`, recursively."""
    if isinstance(schema, ParamSchema.List):
        return frozenset().union(
            *(gather_param_tab_slugs(schema.inner_schema, v) for v in value)
        )
    elif isinstance(schema, ParamSchema.Dict):
        return frozenset().union(
            *(
                gather_param_tab_slugs(inner_schema, value[name])
                for name, inner_schema in schema.properties.items()
            )
        )
    elif isinstance(schema, ParamSchema.Map):
        return frozenset().union(
            *(gather_param_tab_slugs(schema.value_schema, v) for v in value.values())
        )
    elif isinstance(schema, ParamSchema.Tab) and value:
        return frozenset([value])
    elif isinstance(schema, ParamSchema.Multitab):
        return frozenset(value)
    else:
        return frozenset()

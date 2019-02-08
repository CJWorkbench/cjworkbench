from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from cjworkbench.types import Column, ColumnType


class ColumnsField(JSONField):
    """
    Maps a List[Column] to a database JSON column.
    """
    description = 'List of Column metadata, stored as JSON'

    def from_db_value(self, value, *args, **kwargs):
        if value is None:
            return None

        return [Column(c['name'], ColumnType(c['type'])) for c in value]

    def validate(self, value, model_instance):
        super().validate(value, model_instance)

        if value is None:
            return

        if not isinstance(value, list):
            raise ValidationError('not a list', code='invalid',
                                  params={'value': value})

        for item in value:
            if not isinstance(item, Column):
                raise ValidationError('list item is not a column',
                                      code='invalid', params={'value': value})

    def get_prep_value(self, value):
        if value is None:
            return None

        arr = [{'name': c.name, 'type': c.type.value} for c in value]
        return super().get_prep_value(arr)  # JSONField: arr->bytes

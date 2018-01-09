from django.db import models
from django.contrib.auth import get_user_model
from oauth2client.contrib.django_util.models import CredentialsField
from django.contrib import admin
import base64
import pickle

from django.utils import encoding
import jsonpickle

from django.utils.encoding import smart_bytes, smart_text

import oauth2client

User = get_user_model()

class FlowField(models.Field):

    def __init__(self, *args, **kwargs):
        if 'null' not in kwargs:
            kwargs['null'] = True
        super(FlowField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'TextField'

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)

    def to_python(self, value):
        if value is None:
            return None
        if isinstance(value, oauth2client.client.Flow):
            return value
        return pickle.loads(base64.b64decode(value))

    def get_prep_value(self, value):
        if value is None:
            return None
        return smart_text(base64.b64encode(pickle.dumps(value)))

    def value_to_string(self, obj):
        """Convert the field value from the provided model to a string.
        Used during model serialization.
        Args:
            obj: db.Model, model object
        Returns:
            string, the serialized field value
        """
        value = self._get_val_from_obj(obj)
        return self.get_prep_value(value)

class GoogleCredentials(models.Model):
    user = models.ForeignKey(User, related_name='google_credentials', null=True)
    credential = CredentialsField()
    flow = FlowField()

admin.site.register(GoogleCredentials)

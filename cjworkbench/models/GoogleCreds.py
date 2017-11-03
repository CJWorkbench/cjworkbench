from django.db import models
from django.contrib.auth import get_user_model
from oauth2client.contrib.django_util.models import CredentialsField
from django.contrib import admin

User = get_user_model()

class GoogleCredentials(models.Model):
    id = models.ForeignKey(User, primary_key=True, related_name='google_credentials')
    credential = CredentialsField()

admin.site.register(GoogleCredentials)

from django.urls import path

from tusdhooks.views.health import healthz
from tusdhooks.views.tusd_hooks import tusd_hooks

urlpatterns = [
    path("tusd-hooks", tusd_hooks),
    path("healthz", healthz),  # kubernetes
]

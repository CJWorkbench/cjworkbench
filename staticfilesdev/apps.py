from django.contrib.staticfiles.apps import StaticFilesConfig

__all__ = ["StaticFilesDevConfig"]


class StaticFilesDevConfig(StaticFilesConfig):
    ignore_patterns = [
        "admin/js/vendor/select2*",  # we don't use autocomplete fields
    ]

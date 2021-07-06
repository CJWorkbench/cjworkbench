from .debug import DEBUG, I_AM_TESTING

__all__ = ("LOGGING",)


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plaintext": {
            "format": ("%(levelname)s %(asctime)s %(name)s %(thread)d %(message)s")
        },
        "json": {"class": "cjworkbench.logging.json.JsonFormatter"},
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "plaintext" if DEBUG else "json",
        }
    },
    "loggers": {
        "": {"handlers": ["console"], "level": "DEBUG", "propagate": True},
        # It's nice to have level=DEBUG, but we have experience with lots of
        # modules that we think are now better off as INFO.
        "asyncio": {"level": "INFO"},
        "botocore": {"level": "INFO"},
        "botocore.credentials": {"level": "WARNING"},
        "carehare": {"level": "INFO"},
        "channels_rabbitmq": {"level": "INFO"},
        "intercom": {"level": "INFO"},
        "oauthlib": {"level": "INFO"},
        "urllib3": {"level": "INFO"},
        "requests_oauthlib": {"level": "INFO"},
        "s3transfer": {"level": "INFO"},
        "django.request": {
            # Django prints WARNINGs for 400-level HTTP responses. That's
            # wrong: our code is _meant_ to output 400-level HTTP responses in
            # some cases -- that's exactly why 400-level HTTP responses exist!
            # Ignore those WARNINGs and only log ERRORs.
            "level": "ERROR"
        },
        # DEBUG only gets messages when settings.DEBUG==True
        "django.db.backends": {"level": "INFO"},
        "websockets.protocol": {"level": "INFO"},
        "websockets.server": {"level": "INFO"},
        "cjwstate.models.module_registry": {
            "level": ("WARNING" if I_AM_TESTING else "INFO")
        },
        "cjworkbench.pg_render_locker": {"level": "INFO"},
        "server.utils": {"level": "INFO"},
        "stripe": {"level": "INFO"},
    },
}

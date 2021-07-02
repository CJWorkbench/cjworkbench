import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tusdhooks.settings")

import django

django.setup()

from django.core.asgi import get_asgi_application

from cjworkbench.middleware.rabbitmqlifespan import RabbitmqLifespanMiddleware


async def init_module_system():
    # we need the module system *just* so we can migrate_params() to set
    # new files.
    import cjwstate.modules

    cjwstate.modules.init_module_system()


application = RabbitmqLifespanMiddleware(
    get_asgi_application(), extra_init=init_module_system
)

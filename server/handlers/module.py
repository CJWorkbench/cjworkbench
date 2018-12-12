from channels.db import database_sync_to_async
from ..serializers import ModuleSerializer
from .decorators import register_websockets_handler, websockets_handler


@register_websockets_handler
@websockets_handler('read')
@database_sync_to_async
def list(**kwargs):
    modules = Module.objects.all()
    serializer = ModuleSerializer(modules, many=True)
    return serializer.data

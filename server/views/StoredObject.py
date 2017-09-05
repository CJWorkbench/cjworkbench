from rest_framework import viewsets, renderers
from rest_framework.parsers import MultiPartParser
from server.serializers import StoredObjectSerializer
from server.models import StoredObject

class StoredObjectView(viewsets.ModelViewSet):
    renderer_classes = [renderers.JSONRenderer]
    queryset = StoredObject.objects.all()
    serializer_class = StoredObjectSerializer
    parser_classes = (MultiPartParser,)
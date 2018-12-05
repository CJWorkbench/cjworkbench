import json
from django.http import JsonResponse
from rest_framework.decorators import api_view
from server.models import WfModule, StoredObject, UploadedFile


@api_view(['GET'])
def get_uploadedfile(request, wf_module_id):
    wf_module = WfModule.objects.get(pk=wf_module_id, is_deleted=False)

    # the UploadedFile is converted to a StoredObject when the UploadFile
    # module first renders
    so = StoredObject.objects.filter(
        wf_module=wf_module,
        stored_at=wf_module.stored_data_version
    ).first()
    if so and so.metadata:
        metadata = json.loads(so.metadata)[0]
        try:
            uploaded_file = UploadedFile.objects.get(uuid=metadata['uuid'])
        except UploadedFile.DoesNotExist:
            # Seen on production 2018-10-19T00:49:12Z
            return JsonResponse([], safe=False)

        return JsonResponse([{
            'name': uploaded_file.name,
            'uuid': uploaded_file.uuid,
            's3Key': uploaded_file.key,
            's3Bucket': uploaded_file.bucket,
            'size': uploaded_file.size,
        }], safe=False)
    else:
        # no file has yet been uploaded
        return JsonResponse([], safe=False)

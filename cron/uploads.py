import logging
from cjworkbench.sync import database_sync_to_async
from django.utils import timezone
from server.models import InProgressUpload, Tab, WfModule, Workflow


logger = logging.getLogger(__name__)


@database_sync_to_async
def delete_stale_inprogress_file_uploads():
    delete_stale_inprogress_file_uploads_sync()


def delete_stale_inprogress_file_uploads_sync() -> None:
    """
    Delete incomplete/erroneous uploads in S3.

    Rationale: we give users permission to upload files for a while. Once that
    permit expires, nobody can write to that file any more -- so we can clean
    up any errors the user wrote. This saves space (and deletes user data).

    This is essentially a no-op if the user uploads successfully.
    """
    expire_at = timezone.now() - InProgressUpload.MaxAge

    for ipu in InProgressUpload.objects.filter(updated_at__lt=expire_at):
        try:
            wf_module = ipu.wf_module
            with wf_module.workflow.cooperative_lock():
                ipu.delete_s3_data()
                ipu.delete()
        except (WfModule.DoesNotExist, Tab.DoesNotExist, Workflow.DoesNotExist):
            # The Workflow or WfModule was deleted during our loop
            pass

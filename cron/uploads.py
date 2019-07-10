import logging
from cjworkbench.sync import database_sync_to_async
from django.utils import timezone
from server.models import WfModule, Workflow


logger = logging.getLogger(__name__)


@database_sync_to_async
def delete_stale_inprogress_file_uploads():
    delete_stale_inprogress_file_uploads_sync()


def delete_stale_inprogress_file_uploads_sync() -> None:
    """
    Delete day-old incomplete uploads from S3.

    Rationale: we don't actually store enough data on our servers to help users
    resume day-old uploads; their browsers are the only place where that's
    stored. But browsers tend to go away within a day. So stale uploads are
    virtually guaranteed to be garbage data -- which costs space (and exposes
    user data).
    """
    yesterday = timezone.now() - timezone.timedelta(hours=24)

    for wf_module in WfModule.objects.filter(
        inprogress_file_upload_last_accessed_at__lt=yesterday
    ):
        try:
            with wf_module.workflow.cooperative_lock():
                wf_module.refresh_from_db()
                if wf_module.inprogress_file_upload_last_accessed_at >= yesterday:
                    # we're racing with a user who just started another upload
                    continue
                logger.info(
                    "Aborting stale upload on wf-%d/wfm-%d",
                    wf_module.workflow_id,
                    wf_module.id,
                )
                wf_module.abort_inprogress_upload()
        except Workflow.DoesNotExist:
            # The Workflow or WfModule was deleted during our loop
            pass

from datetime import timedelta
from functools import partial
import logging
import os
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.db import DatabaseError, InterfaceError
from django.utils import timezone
import msgpack
from server.models import LoadedModule, Params, WfModule
from server.worker import save
from .util import benchmark


# Minimum amount of time between when a fetch is queued on a workflow and when
# the next fetch is queued on the same workflow.
MinFetchInterval = 5 * 60  # 5min


logger = logging.getLogger(__name__)


@database_sync_to_async
def _get_params(wf_module: WfModule) -> Params:
    return wf_module.get_params()


@database_sync_to_async
def _get_input_dataframe(workflow_id: int, wf_module_position: int):
    try:
        # Let's not worry about locks and races too much. All failures should
        # throw DoesNotExist, which is fine.
        wf_module = WfModule.objects.get(tab__workflow_id=workflow_id,
                                         tab__is_deleted=False,
                                         order=wf_module_position - 1,
                                         is_deleted=False)
    except WfModule.DoesNotExist:
        return None

    crr = wf_module.get_cached_render_result(only_fresh=True)
    if not crr:
        return None
    else:
        return crr.result.dataframe


@database_sync_to_async
def _get_stored_dataframe(wf_module_id: int):
    try:
        wf_module = WfModule.objects.get(pk=wf_module_id)
    except WfModule.DoesNotExist:
        return None

    return wf_module.retrieve_fetched_table()


@database_sync_to_async
def _get_workflow_owner(workflow_id: int):
    try:
        return User.objects.get(owned_workflows__id=workflow_id)
    except User.DoesNotExist:
        return None


async def fetch_wf_module(wf_module, now):
    """Fetch `wf_module` and notify user of changes via email/websockets."""
    logger.debug('fetch_wf_module(%d, %d) at interval %d',
                 wf_module.workflow_id, wf_module.id,
                 wf_module.update_interval)
    try:
        params = await _get_params(wf_module)

        lm = await LoadedModule.for_module_version(wf_module.module_version)
        result = await lm.fetch(
            params,
            workflow_id=wf_module.workflow_id,
            get_input_dataframe=partial(_get_input_dataframe,
                                        wf_module.workflow_id,
                                        wf_module.order),
            get_stored_dataframe=partial(_get_stored_dataframe, wf_module.id),
            get_workflow_owner=partial(_get_workflow_owner,
                                       wf_module.workflow_id),
        )

        await save.save_result_if_changed(wf_module, result)
    except Exception as e:
        # Log exceptions but keep going
        logger.exception(f'Error fetching {wf_module}')

    update_next_update_time(wf_module, now)


def update_next_update_time(wf_module, now):
    """Schedule next update, skipping missed updates if any."""
    tick = timedelta(seconds=max(wf_module.update_interval, MinFetchInterval))
    wf_module.last_update_check = now

    if wf_module.next_update:
        while wf_module.next_update <= now:
            wf_module.next_update += tick
    wf_module.save(update_fields=['last_update_check', 'next_update'])


async def fetch(*, wf_module_id: int) -> None:
    try:
        wf_module = WfModule.objects.get(id=wf_module_id)
    except WfModule.DoesNotExist:
        logger.info('Skipping fetch of deleted WfModule %d', wf_module_id)
        return

    now = timezone.now()
    # most exceptions caught elsewhere
    try:
        task = fetch_wf_module(wf_module, now)
        await benchmark(logger, task, 'fetch_wf_module(%d)', wf_module_id)
    except DatabaseError:
        # Two possibilities:
        #
        # 1. There's a bug in module_dispatch_fetch. This may leave the event
        # loop's executor thread's database connection in an inconsistent
        # state. [2018-11-06 saw this on production.] The best way to clear
        # up the leaked, broken connection is to die. (Our parent process
        # should restart us, and RabbitMQ will give the job to someone
        # else.)
        #
        # 2. The database connection died (e.g., Postgres went away.) The
        # best way to clear up the leaked, broken connection is to die.
        # (Our parent process should restart us, and RabbitMQ will give the
        # job to someone else.)
        #
        # 3. There's some design flaw we haven't thought of, and we
        # shouldn't ever render this workflow. If this is the case, we're
        # doomed.
        #
        # If you're seeing this error that means there's a bug somewhere
        # _else_. If you're staring at a case-3 situation, please remember
        # that cases 1 and 2 are important, too.
        logger.exception('Fatal database error; exiting')
        os._exit(1)
    except InterfaceError:
        logger.exception('Fatal database error; exiting')
        os._exit(1)


async def handle_fetch(message):
    with message.process():
        kwargs = msgpack.unpackb(message.body, raw=False)
        try:
            await fetch(**kwargs)
        except:
            logger.exception('Error during fetch')

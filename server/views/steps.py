import asyncio
import io
import json
import subprocess
from http import HTTPStatus as status
from typing import Awaitable, Literal, Tuple

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, HttpRequest, HttpResponse, JsonResponse
from django.template.response import TemplateResponse
from django.utils.cache import patch_response_headers
from django.views.decorators.http import require_GET

from cjwkernel.types import ColumnType
from cjworkbench.middleware.clickjacking import xframe_options_exempt
from cjworkbench.sync import database_sync_to_async
from cjwstate import rabbitmq
from cjwstate.models import AclEntry, Step, Workflow
from cjwstate.models.fields import Role
from cjwstate.models.module_registry import MODULE_REGISTRY
from cjwstate.rendercache import (
    CorruptCacheError,
    downloaded_parquet_file,
    open_cached_render_result,
    read_cached_render_result_slice_as_text,
)

from ..serializers import (
    JsonizeContext,
    jsonize_clientside_step,
    jsonize_clientside_workflow,
)

_MaxNRowsPerRequest = 300


def _load_workflow_and_step_sync(
    request: HttpRequest, workflow_id: int, step_slug: str
) -> Tuple[Workflow, Step]:
    """Load (Workflow, Step) from database, or raise Http404 or PermissionDenied.

    `Step.tab` will be loaded. (`Step.tab.workflow_id` is needed to access the render
    cache.)

    To avoid PermissionDenied:

    * The workflow must be public; OR
    * The user must be workflow owner, editor or viewer; OR
    * The user must be workflow report-viewer and the step must be a chart or
      table in the report.
    """
    try:
        with Workflow.lookup_and_cooperative_lock(id=workflow_id) as workflow_lock:
            workflow = workflow_lock.workflow
            if workflow.public or workflow.request_authorized_owner(request):
                need_report_auth = False
            elif request.user is None or request.user.is_anonymous:
                raise PermissionDenied()
            else:
                try:
                    acl_entry = workflow.acl.filter(email=request.user.email).get()
                except AclEntry.DoesNotExist:
                    raise PermissionDenied()
                if acl_entry.role in {Role.VIEWER, Role.EDITOR}:
                    need_report_auth = False
                elif acl_entry.role == Role.REPORT_VIEWER:
                    need_report_auth = True
                else:
                    raise PermissionDenied()  # role we don't handle yet

            step = (
                Step.live_in_workflow(workflow_id)
                .select_related("tab")
                .get(slug=step_slug)
            )  # or Step.DoesNotExist

            if need_report_auth:  # user is report-viewer
                if workflow.has_custom_report:
                    if workflow.blocks.filter(step_id=step.id).count():
                        pass  # the step is a chart
                    elif workflow.blocks.filter(
                        tab_id=step.tab_id
                    ).count() and not step.tab.live_steps.filter(order__gt=step.order):
                        pass  # step is a table (last step of a report-included tab)
                    else:
                        raise PermissionDenied()
                else:
                    # Auto-report: all Charts are allowed; everything else is not
                    try:
                        if (
                            MODULE_REGISTRY.latest(step.module_id_name)
                            .get_spec()
                            .html_output
                        ):
                            pass
                        else:
                            raise PermissionDenied()
                    except KeyError:  # not a module
                        raise PermissionDenied()

            return workflow, step
    except (Workflow.DoesNotExist, Step.DoesNotExist):
        raise Http404()


_load_workflow_and_step = database_sync_to_async(_load_workflow_and_step_sync)


@database_sync_to_async
def _load_step_by_id_oops_where_is_workflow(
    request: HttpRequest, step_id: int
) -> Tuple[Workflow, Step]:
    """Load (Workflow, Step) from database, or raise Http404 or PermissionDenied.

    Don't use this in new code. Put workflow ID in the URL instead.
    """
    try:
        workflow_id, step_slug = Step.objects.values_list(
            "tab__workflow_id", "slug"
        ).get(id=step_id)
    except Step.DoesNotExist:
        raise Http404("step not found")

    return _load_workflow_and_step_sync(request, workflow_id, step_slug)


def int_or_none(x):
    return int(x) if x is not None else None


async def result_table_slice(
    request: HttpRequest, workflow_id: int, step_slug: str, delta_id: int
) -> HttpResponse:
    # Get first and last row from query parameters, or default to all if not
    # specified
    try:
        startrow = int_or_none(request.GET.get("startrow"))
        endrow = int_or_none(request.GET.get("endrow"))
    except ValueError:
        return JsonResponse(
            {"message": "bad row number", "status_code": 400},
            status=status.BAD_REQUEST,
        )

    # raise Http404, PermissionDenied
    _, step = await _load_workflow_and_step(request, workflow_id, step_slug)
    cached_result = step.cached_render_result
    if cached_result is None or cached_result.delta_id != delta_id:
        # assume we'll get another request after execute finishes
        return JsonResponse([], safe=False)

    # startrow/endrow can be None, and these still work
    startrow = max(0, startrow or 0)
    endrow = max(
        startrow,
        min(
            cached_result.table_metadata.n_rows,
            endrow or 2 ** 60,
            startrow + _MaxNRowsPerRequest,
        ),
    )

    try:
        # Return one more column than configured, so client can detect "too many
        # columns"
        output = await _step_to_text_stream(
            step,
            "json",
            "--column-range",
            "0-%d" % (settings.MAX_COLUMNS_PER_CLIENT_REQUEST + 1),
            "--row-range",
            "%d-%d" % (startrow, endrow),
        )
    except CorruptCacheError:
        # assume we'll get another request after execute finishes
        return JsonResponse([], safe=False)

    response = FileResponse(
        output, as_attachment=False, content_type="application/json"
    )
    patch_response_headers(response, cache_timeout=600)
    return response


# /tiles/:slug/v:delta_id/:tile_row,:tile_column.json: table data
@require_GET
def tile(
    request: HttpRequest,
    workflow_id: int,
    step_slug: str,
    delta_id: int,
    tile_row: int,
    tile_column: int,
):
    workflow, step = _load_workflow_and_step_sync(request, workflow_id, step_slug)
    # No need for cooperative lock: the cache may always be corrupt (lock or no), and
    # we don't read from the database
    row_begin = tile_row * settings.BIG_TABLE_ROWS_PER_TILE
    row_end = row_begin + settings.BIG_TABLE_ROWS_PER_TILE  # one past end
    column_begin = tile_column * settings.BIG_TABLE_COLUMNS_PER_TILE
    column_end = column_begin + settings.BIG_TABLE_COLUMNS_PER_TILE  # one past end

    cached_result = step.cached_render_result
    if cached_result is None or cached_result.delta_id != delta_id:
        return JsonResponse(
            {"error": "delta_id result not cached"}, status=status.NOT_FOUND
        )

    if (
        cached_result.table_metadata.n_rows <= row_begin
        or len(cached_result.table_metadata.columns) <= column_begin
    ):
        return JsonResponse({"error": "tile out of bounds"}, status=status.NOT_FOUND)

    try:
        record_json = read_cached_render_result_slice_as_text(
            cached_result,
            "json",
            only_rows=range(row_begin, row_end),
            only_columns=range(column_begin, column_end),
        )
    except CorruptCacheError:
        # A different 404 message to help during debugging
        return JsonResponse(
            {"error": "result went away; please try again with another delta_id"},
            status=status.NOT_FOUND,
        )

    # Convert from [{"a": "b", "c": "d"}, ...] to [["b", "d"], ...]
    rows = json.loads(
        record_json, object_pairs_hook=lambda pairs: [v for k, v in pairs]
    )

    response = JsonResponse({"rows": rows})
    patch_response_headers(response, cache_timeout=600)
    return response


@xframe_options_exempt
async def deprecated_output(request: HttpRequest, step_id: int):
    # raise Http404, PermissionDenied
    _, step = await _load_step_by_id_oops_where_is_workflow(request, step_id)
    try:
        module_zipfile = await database_sync_to_async(MODULE_REGISTRY.latest)(
            step.module_id_name
        )
        html = module_zipfile.get_optional_html()
    except KeyError:
        html = None
    return HttpResponse(content=html)


async def result_json(
    request: HttpRequest, workflow_id: int, step_slug: str, delta_id: int
) -> HttpResponse:
    # raise Http404, PermissionDenied
    _, step = await _load_workflow_and_step(request, workflow_id, step_slug)
    cached_result = step.cached_render_result
    if cached_result is None or cached_result.delta_id != delta_id:
        return JsonResponse(
            {"error": "render result not in cache"}, status=status.NOT_FOUND
        )
    if not cached_result.json:
        return JsonResponse(
            {"error": "render result has no JSON"}, status=status.NOT_FOUND
        )

    response = JsonResponse(cached_result.json, safe=False)
    patch_response_headers(response, cache_timeout=600)
    return response


async def result_column_value_counts(
    request: HttpRequest, workflow_id: int, step_slug: str, delta_id: int
) -> JsonResponse:
    try:
        colname = request.GET["column"]
    except KeyError:
        return JsonResponse(
            {"error": 'Missing a "column" parameter'}, status=status.BAD_REQUEST
        )

    if not colname:
        # User has not yet chosen a column. Empty response.
        return JsonResponse({"values": {}})

    # raise Http404, PermissionDenied
    _, step = await _load_workflow_and_step(request, workflow_id, step_slug)
    cached_result = step.cached_render_result
    if cached_result is None or cached_result.delta_id != delta_id:
        # assume we'll get another request after execute finishes
        return JsonResponse({"values": {}})

    try:
        column_index, column = next(
            (i, c)
            for i, c in enumerate(cached_result.table_metadata.columns)
            if c.name == colname
        )
    except StopIteration:
        return JsonResponse(
            {"error": f'column "{colname}" not found'}, status=status.NOT_FOUND
        )

    if not isinstance(column.type, ColumnType.Text):
        # We only return text values.
        #
        # Rationale: this is only used in Refine and Filter by Value. Both
        # force text. The user can query a column before it's converted to
        # text; but if he/she does, we shouldn't format as text unless we have
        # a viable workflow that needs it. (Better would be to force the user
        # to convert to text before doing anything else, no?)
        return JsonResponse({"values": {}})

    try:
        # raise CorruptCacheError
        with open_cached_render_result(cached_result) as result:
            arrow_table = result.table.table
            chunked_array = arrow_table.column(column_index)
    except CorruptCacheError:
        # We _could_ return an empty result set; but our only goal here is
        # "don't crash" and this 404 seems to be the simplest implementation.
        # (We assume that if the data is deleted, the user has moved elsewhere
        # and this response is going to be ignored.)
        return JsonResponse(
            {"error": f'column "{colname}" not found'}, status=status.NOT_FOUND
        )

    if chunked_array.num_chunks == 0:
        value_counts = {}
    else:
        pyarrow_value_counts = chunked_array.value_counts()
        # Assume type is text. (We checked column.type is ColumnType.Text above.)
        #
        # values can be either a StringArray or a DictionaryArray. In either case,
        # .to_pylist() converts to a Python List[str].
        values = pyarrow_value_counts.field("values").to_pylist()
        counts = pyarrow_value_counts.field("counts").to_pylist()

        value_counts = {v: c for v, c in zip(values, counts) if v is not None}

    response = JsonResponse({"values": value_counts})
    patch_response_headers(response, cache_timeout=600)
    return response


@xframe_options_exempt
async def deprecated_embed(request: HttpRequest, step_id: int):
    # raise Http404, PermissionDenied
    workflow, step = await _load_step_by_id_oops_where_is_workflow(request, step_id)

    try:
        module_zipfile = await database_sync_to_async(MODULE_REGISTRY.latest)(
            step.module_id_name
        )
        if not module_zipfile.get_spec().html_output:
            raise Http404("Module is not embeddable")
    except KeyError:
        raise Http404("Step has no module")

    @database_sync_to_async
    def build_init_state():
        ctx = JsonizeContext(
            user=AnonymousUser(),
            user_profile=None,
            session=None,
            locale_id=request.locale_id,
            module_zipfiles={module_zipfile.module_id: module_zipfile},
        )
        return {
            "workflow": jsonize_clientside_workflow(
                workflow.to_clientside(
                    include_tab_slugs=False,
                    include_block_slugs=False,
                    include_acl=False,
                ),
                ctx,
                is_init=True,
            ),
            "step": jsonize_clientside_step(step.to_clientside(), ctx),
        }

    return TemplateResponse(
        request, "embed.html", {"initState": await build_init_state()}
    )


class SubprocessOutputFileLike(io.RawIOBase):
    """Run a subrocess; .read() reads its stdout and stderr (combined).

    On close(), kill the subprocess (if it's still running) and wait for it.

    close() is the only way to wait for the subprocess. Don't worry: __del__()
    calls close().

    If the process cannot be started, raise OSError.

    If read() is called after the subprocess terminates and the subprocess's
    exit code is not 0, raise IOError.

    Not thread-safe.

    HACK: this is only safe for Django 3.1 async-view responses.
    `django.core.handlers.asgi.ASGIHandler#send_response()` has this loop:

        for part in response:  # calls .read() -- SYNCHRONOUS!!!
            await send(...)  # async (safe)

    We make assumptions about Django, the caller, the client....:

        * The caller can `await filelike.stdout_ready()` to ensure the first
          bytes of stdout are available. This ensures the streaming has begun:
          the subprocess's has started up (which may be slow). If the subprocess
          opened temporary files, it's safe to delete them now.
        * The process must stream stdout _quickly_. Django calls `.readinto()`
          synchronously in the event-loop thread: it stalls the web server.
        * Django `send()` must back-pressure. That's when other HTTP request
          processing happens.
        * The process must not consume much RAM/disk/CPU; or the caller must
          arrange throttling. Django won't limit the number of concurrent
          ASGI requests.
    """

    def __init__(self, args):
        super().__init__()

        # Raises OSError
        self.process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )

    async def stdout_ready(self) -> Awaitable[None]:
        """Return when `self.process.stdout.read()` is guaranteed not to block.

        After this returns, the subprocess is "started up". If it's streaming
        from a file, it has certainly opened that file -- and so on UNIX, that
        file may be safely deleted.

        This uses loop.add_reader() to watch the file descriptor. That only
        works because [2020-12-22] Django 3.1 _doesn't_ use loop.add_reader()!
        When Django allows streaming async output, let's use that.
        """
        loop = asyncio.get_running_loop()
        event = asyncio.Event()
        fd = self.process.stdout.fileno()

        def ready():
            event.set()
            loop.remove_reader(fd)

        loop.add_reader(fd, ready)

        try:
            await event.wait()
        finally:
            loop.remove_reader(fd)  # in case ready() was never called

    def readable(self):
        return True

    def fileno(self):
        return self.process.stdout.fileno()

    def readinto(self, b):
        # Assume this is fast. (It's called synchronously.)
        ret = self.process.stdout.readinto(b)
        return ret

    def close(self):
        if self.closed:
            return

        self.process.stdout.close()
        self.process.kill()
        # wait() should not deadlock, because process will certainly die.
        self.process.wait()  # ignore exit code
        super().close()  # sets self.closed


async def _step_to_text_stream(
    step: Step, format: Literal["csv", "json"], *args
) -> Awaitable[SubprocessOutputFileLike]:
    """Download the step's cached result and streaming it as CSV/JSON.

    Raise CorruptCacheError if there is no cached result or it is invalid.

    Raise OSError if `/usr/bin/parquet-to-text-stream` cannot start.
    """
    cached_result = step.cached_render_result
    if not cached_result:
        raise CorruptCacheError

    # raise CorruptCacheError
    with downloaded_parquet_file(cached_result) as parquet_path:
        output = SubprocessOutputFileLike(
            ["/usr/bin/parquet-to-text-stream", str(parquet_path), format, *args]
        )
        await output.stdout_ready()
        # It's okay to delete the file now (i.e., exit the context manager)

        return output


async def _render_result_table_json(workflow: Workflow, step: Step) -> HttpResponse:
    try:
        output = await _step_to_text_stream(step, "json")
    except CorruptCacheError:
        # Schedule a render and return a response asking the user to retry.
        #
        # We don't have a cached result, and we don't know how long it'll
        # take to get one. The user will simply need to try again....
        #
        # It is a *bug* that we publish URLs that aren't guaranteed to work.
        # Because we publish URLs that do not work, let's be transparent and
        # give them the 500-level error code they deserve.
        await rabbitmq.queue_render(workflow.id, workflow.last_delta_id)
        response = JsonResponse([], safe=False, status=status.SERVICE_UNAVAILABLE)
        response["Retry-After"] = "30"
        return response

    return FileResponse(
        output,
        as_attachment=True,
        filename=(
            "Workflow %d - %s-%d.json" % (workflow.id, step.module_id_name, step.id)
        ),
        content_type="application/json",
    )


async def current_result_table_json(
    request: HttpRequest, workflow_id: int, step_slug: str
) -> HttpResponse:
    # raise Http404, PermissionDenied
    workflow, step = await _load_workflow_and_step(request, workflow_id, step_slug)
    return await _render_result_table_json(workflow, step)


async def deprecated_public_json(request: HttpRequest, step_id: int) -> HttpResponse:
    # raise Http404, PermissionDenied
    workflow, step = await _load_step_by_id_oops_where_is_workflow(request, step_id)
    # TODO turn this into a redirect. This will break things for API users
    # because their HTTP clients might not follow redirects.
    return await _render_result_table_json(workflow, step)


async def _render_result_table_csv(workflow: Workflow, step: Step) -> HttpResponse:
    try:
        output = await _step_to_text_stream(step, "csv")
    except CorruptCacheError:
        # Schedule a render and return a response asking the user to retry.
        #
        # We don't have a cached result, and we don't know how long it'll
        # take to get one. The user will simply need to try again....
        #
        # It is a *bug* that we publish URLs that aren't guaranteed to work.
        # Because we publish URLs that do not work, let's be transparent and
        # give them the 500-level error code they deserve.
        await rabbitmq.queue_render(workflow.id, workflow.last_delta_id)
        response = HttpResponse(
            b"", content_type="text/csv", status=status.SERVICE_UNAVAILABLE
        )
        response["Retry-After"] = "30"
        return response

    return FileResponse(
        output,
        as_attachment=True,
        filename=(
            "Workflow %d - %s-%d.csv" % (workflow.id, step.module_id_name, step.id)
        ),
        content_type="text/csv; charset=utf-8; header=present",
    )


async def current_result_table_csv(
    request: HttpRequest, workflow_id: int, step_slug: str
) -> HttpResponse:
    # raise Http404, PermissionDenied
    workflow, step = await _load_workflow_and_step(request, workflow_id, step_slug)
    return await _render_result_table_csv(workflow, step)


async def deprecated_public_csv(request: HttpRequest, step_id: int) -> FileResponse:
    # raise Http404, PermissionDenied
    workflow, step = await _load_step_by_id_oops_where_is_workflow(request, step_id)
    # TODO turn this into a redirect. This will break things for API users
    # because their HTTP clients might not follow redirects.
    return await _render_result_table_csv(workflow, step)

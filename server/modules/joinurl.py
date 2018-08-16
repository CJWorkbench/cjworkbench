from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.db import transaction
from .moduleimpl import ModuleImpl
from .types import ProcessResult
from server.models.Workflow import Workflow

#------ For now, only load workbench urls and 1 key to join on from left table

_join_type_map = 'Left|Inner|Right'.lower().split('|')

def get_id_from_url(url):
    #TODO: Environment check
    path = url.split('/')
    try:
        _id = int(path[path.index('workflows') + 1])
        return _id
    except ValueError:
        raise ValueError
    except Exception as e:
        raise Exception(str(e.args[0]))


def get_right_wf_module(right_wf_id):
    # select_for_update(nowait=True) is the simplest way to fail fast on deadlock.
    # (We could consider nowait=False and letting Postgres handle the deadlock, but
    # let's save that for another day.)
    try:
        with transaction.atomic():
            return Workflow.objects.select_for_update(nowait=True).get(id=right_wf_id)
    except Workflow.DoesNotExist:
        raise Exception('Target workflow does not exist')
    except Exception as e:
        raise e

def check_cols_right(right, columns):
    diff = set(columns) - set(right.columns)
    if diff:
        raise Exception(
            f'{len(diff)} columns not in target workflow: {diff}'
        )
    return

def join_tables(left, right, type, key):
    #TODO: Cast astype if types to not match
    return left.join(right.set_index(key), on=key, how=type)
    # Save for typecasting
    #else:
    #    raise TypeError(f'Key column "{key}" types do not match.' \
    #                    f'Left: {left[key].dtype} Right: {left[key].dtype}')

class JoinURL(ModuleImpl):
    @staticmethod
    def render(wf_module, table):
        right_table = wf_module.retrieve_fetched_table()
        if right_table.empty:
            return ProcessResult(table,
                          wf_module.error_msg)

        key_cols = [wf_module.get_param('key', 'column')]
        join_type_idx = wf_module.get_param('type', 'menu')
        join_type = _join_type_map[join_type_idx]

        try:
            # TODO decide on import columns
            # Check if import columns exists in right table
            if wf_module.get_param_string('importcols').strip():
                import_cols = wf_module.get_param_string('importcols').strip().split(',')
                check_cols_right(right_table, import_cols + key_cols)
                right_table = right_table[key_cols + import_cols]
            else:
                check_cols_right(right_table, key_cols)

            table = join_tables(table, right_table, join_type, key_cols)
        except Exception as err:
            return ProcessResult(table, error=(str(err.args[0])))

        return ProcessResult(table,
                         wf_module.error_msg)

    # Load Workbench workflow and join
    @staticmethod
    def event(wf_module, **kwargs):
        url = wf_module.get_param_string('url').strip()
        key_cols = wf_module.get_param('key', 'column')

        if not (key_cols or url):
            return

        try:
            validate = URLValidator()
            validate(url)
        except ValidationError:
            wf_module.set_error('Invalid URL')
            return

        try:
            right_wf_id = get_id_from_url(url)
        except ValueError:
            wf_module.set_error((
                f'Error fetching {url}: '
                'Invalid workflow URL'
            ))
            return
        except Exception as err:
            wf_module.set_error(str(err.args[0]))
            return

        # fetching could take a while so notify clients/users we're working
        wf_module.set_busy()

        try:
            right_wf_module = get_right_wf_module(right_wf_id)
        except Exception as err:
            wf_module.set_error(str(err.args[0]))
            return

        # Check to see if workflow_id the same
        if wf_module.workflow_id == right_wf_module.id:
            wf_module.set_error('Cannot join workflow to itself')
            return

        # Make sure _this_ workflow's owner has access permissions to the _other_ workflow
        user = wf_module.workflow.owner
        if not right_wf_module.user_session_authorized_read(user, None):
            wf_module.set_error(
                'Access denied to the target workflow'
            )
            return

        right_wf_module = right_wf_module.wf_modules.last()

        # Always pull the cached result, so we can't execute() an infinite loop
        right_result = right_wf_module.get_cached_render_result().result
        result = ProcessResult(dataframe=right_result.dataframe)

        result.truncate_in_place_if_too_big()
        result.sanitize_in_place()
        ModuleImpl.commit_result(wf_module, result)

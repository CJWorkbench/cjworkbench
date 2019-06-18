from cjworkbench.models.userprofile import UserProfile
from cjworkbench.sync import database_sync_to_async
from server.models import Workflow, WfModule
from .decorators import register_websockets_handler, websockets_handler
from .types import HandlerError


def isoformat(dt) -> str:
    return dt.isoformat()[:-len('000+00:00')] + 'Z'


@register_websockets_handler
@websockets_handler(role='read')  # for logging, error handling
@database_sync_to_async
def list_autofetches(scope, **kwargs):
    autofetches = list(WfModule.objects.filter(
        auto_update_data=True,
        is_deleted=False,
        tab__is_deleted=False,
        tab__workflow_id__in=Workflow.owned_by_user_session(scope['user'],
                                                            scope['session']),
    ).order_by('tab__workflow__creation_date', 'tab__id', 'id').values(
        'tab__workflow_id',
        'tab__workflow__name',
        'tab__workflow__creation_date',
        'tab__workflow__last_viewed_at',
        'tab__slug',
        'tab__name',
        'id',
        'update_interval',
    ))

    if not scope['user'].is_anonymous and scope['user'].user_profile:
        max_fetches_per_day = scope['user'].user_profile.max_fetches_per_day
    else:
        max_fetches_per_day = (
            UserProfile._meta.get_field('max_fetches_per_day').default
        )

    return {
        'maxFetchesPerDay': max_fetches_per_day,
        'autofetches': [
            {
                'workflow': {
                    'id': row['tab__workflow_id'],
                    'name': row['tab__workflow__name'],
                    'createdAt': (
                        isoformat(row['tab__workflow__creation_date'])
                    ),
                    'lastViewedAt': (
                        isoformat(row['tab__workflow__last_viewed_at'])
                    ),
                },
                'tab': {
                    'slug': row['tab__slug'],
                    'name': row['tab__name'],
                },
                'wfModule': {
                    'id': row['id'],
                    'fetchInterval': row['update_interval'],
                },
            } for row in autofetches
        ]
    }

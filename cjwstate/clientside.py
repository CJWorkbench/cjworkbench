"""
State that will be seen in Redux clients.

This state is created within the `cjwstate` package and passed to
`server.websockets`. It is language-agnostic: the Websockets module
will translate it differently for each client.

A note on architecture: Django ORM hobbles us with its Active Model design
pattern. Active Model is incompatible with async code, because any property
access from the event-loop thread can cause a database query. A few classes
in this module are the models we'd be using if our ORM used Data Access Objects
instead. (For instance: AclEntry and UploadedFile.) Long-term, we'll move
away from Django ORM; once we do, we can nix these models and use ORM objects
instead.
"""
from dataclasses import dataclass, field
import datetime
from typing import Optional
from cjwkernel.types import RenderError
from cjwstate.modules.module_loader import ModuleSpec


@dataclass(frozen=True)
class _Null:
    pass


Null = _Null()
"""
Sentinel indicating that the web browser should change the value to
JavaScript `null`.

We don't use `None` for this purpose: `None` means there is no update.
"""


@dataclass(frozen=True)
class AclEntry:
    email: str
    can_edit: str


@dataclass(frozen=True)
class UploadedFile:
    name: str
    uuid: str
    size: int
    created_at: datetime.datetime


@dataclass(frozen=True)
class FetchVersion:
    created_at: datetime.datetime
    is_seen: bool


@dataclass(frozen=True)
class FetchVersionList:
    versions: List[FetchVersion]
    selected: Optional[datetime.datetime]


@dataclass(frozen=True)
@dataclass(frozen=True)
class WorkflowUpdate:
    """
    Updates to clients' `workflow` state.

    The following fields cannot be represented here:

    * `id`: cannot be updated
    * `url_id`: cannot be updated
    * `is_anonymous`: cannot be updated
    * `owner_email`: cannot be updated
    * `owner_name`: cannot be updated
    * `read_only`: has a different value for different users
    * `is_owner`: has a different value for different users
    * `selected_tab_position`: has a different value for different users

    Every field of an Update is Optional, default `None`. `None` means there
    is no update, and the client should keep whichever value it already had.
    A value of type Optional[Union[Null, ...]] can be set to `Null`, which
    indicates that the client should change its value to `null`.
    """

    name: Optional[str] = None
    """Workflow name, user-editable."""

    tab_slugs: Optional[List[str]] = None
    """Ordered list of tab slugs."""

    public: Optional[bool] = None
    """True means anybody can see it."""

    last_update: Optional[datetime.datetime] = None
    """Time of last modification."""

    acl: Optional[List[AclEntry]] = None
    """Non-owners' permissions."""


@dataclass(frozen=True)
class StepUpdate:
    """
    Data for a new or existing Step with the given id (TODO use slug, nix id).
    """

    id: int
    """
    Step identifier. TODO nix this and use slug as identifier.
    """

    slug: str
    """
    Step identifier.
    """

    module_slug: Optional[str] = None
    """
    Module identifier.

    Required for creation, and must be None afterwards.
    """

    tab_slug: Optional[str] = None
    """
    Tab identifier.

    TODO nix this -- it's redundant.
    """

    is_busy: Optional[bool] = None
    """
    True during fetch.

    TODO nix this and track fetches as separate objects.
    """

    last_relevant_delta_id: Optional[int] = None
    """
    Delta ID that ought to be rendered.

    This may get out of sync with cached_render_result_delta_id.
    """

    render_result: Optional[Union[Null, CachedRenderResult]] = None
    """
    Cached, maybe-stale render result.

    Null if there is no cached render result.

    If the cached-result delta ID is different from the _relevant_ delta ID,
    then the result is obsolete. The client may render obsolete data plus a
    progress indicator.
    """

    files: Optional[List[UploadedFile]] = None
    """
    List of all files uploaded by the user to this Step.
    """

    params: Optional[Dict[str, Any]] = None
    """
    User-supplied params.
    """

    secrets: Optional[Dict[str, Dict[str, str]]] = None
    """
    User-supplied secrets.

    Each secret is a Dict with just a "name" (str) value.
    """

    is_collapsed: Optional[bool] = None
    """
    True if the module should occupy fewer pixels on the screen.
    """

    notes: Optional[str] = None
    """
    User-entered notes. May be `""`.
    """

    is_auto_fetch: Optional[bool] = None
    """
    True if the user wants this module to fetch as a cronjob.
    """

    fetch_interval: Optional[int] = None
    """
    Number of seconds between fetches, if is_auto_update is set.

    (If is_auto_update _isn't_ set, number of seconds to default it to when it
    does become set.)
    """

    last_fetched_at: Optional[Union[Null, datetime.datetime]] = None
    """
    Time of last fetch, or Null.

    This time may be more recent than the latest FetchVersion, if we polled a
    website and then decided not to create a new FetchVersion.
    """

    is_notify_on_change: Optional[bool] = None
    """
    True if we are to email the user when the result changes.
    """

    has_unseen_notification: Optional[bool] = None
    """
    True if no user has viewed a notification.

    TODO revisit this feature. It's not multi-user friendly.
    """

    versions: Optional[FetchVersion]
    """
    Information about fetched versions.

    TODO redesign "versions" from scratch. They currently conflate all these
    cases:

    * We sometimes create new versions when remote websites change.
    * We sometimes create new versions when users change parameters.
    * We sometimes create new versions when module code changes.
    """


@dataclass(frozen=True)
class TabUpdate:
    """
    Data for a new or existing Tab with the given slug.
    """

    slug: str
    """
    Tab identifier.
    """

    name: Optional[str] = None
    """
    User-supplied name.
    """

    step_ids: Optional[List[int]] = None
    """
    Step IDs, in order.

    TODO change this to Step slugs.
    """

    selected_step_index: Optional[int] = None
    """
    Position (0 = "first") of the last step selected by any editor.

    This is only used during page load. We probably ought to make it per-user,
    but it's too subtle to be a priority.
    """


@dataclass(frozen=True)
class Update:
    """
    New data to pass to the client.

    Every field of an Update is Optional, default `None`. `None` means there
    is no update, and the client should keep whichever value it already had.
    A value of type Optional[Union[Null, ...]] can be set to `Null`, which
    indicates that the client should change its value to `null`.
    """

    workflow: Optional[WorkflowUpdate] = None
    """Workflow-wide data to replace."""

    modules: Dict[str, ModuleSpec] = field(default_factory=dict)
    """Modules to add or replace, keyed by slug."""

    steps: Dict[int, StepUpdate] = field(default_factory=dict)
    """Steps to add or update, keyed by ID. TODO use slugs, not IDs."""

    tabs: Dict[str, TabUpdate] = field(default_factory=dict)
    """Tabs to add or update, keyed by slug."""

    clear_tabs: List[str] = field(default_factory=list)
    """Tab slugs the client should forget about."""

    clear_steps: List[int] = field(default_factory=list)
    """Step IDs the client should forget about. TODO use slugs, not IDs."""

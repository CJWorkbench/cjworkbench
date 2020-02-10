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
from __future__ import annotations
from dataclasses import dataclass, field, replace
import datetime
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Union
from cjwstate.modules.types import ModuleSpec


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
class FetchedVersion:
    created_at: datetime.datetime
    is_seen: bool


@dataclass(frozen=True)
class FetchedVersionList:
    versions: List[FetchedVersion]
    selected: Optional[datetime.datetime]


@dataclass(frozen=True)
class Module:
    spec: ModuleSpec
    js_module: str


@dataclass(frozen=True)
class WorkflowUpdate:
    """
    Updates to clients' `workflow` state.

    The following fields cannot be represented here:

    * `read_only`: has a different value for different users
    * `is_owner`: has a different value for different users
    * `selected_tab_position`: has a different value for different users

    Every field of an Update is Optional, default `None`. `None` means there
    is no update, and the client should keep whichever value it already had.
    A value of type Optional[Union[_Null, ...]] can be set to `Null`, which
    indicates that the client should change its value to `null`.
    """

    id: Optional[int] = None
    """
    ID of the workflow in the database.

    Required for init, and must be None afterwards.
    """

    url_id: Optional[int] = None
    """
    ID of the workflow in URLs.

    Required for init, and must be None afterwards.
    """

    owner: Optional["User"] = None
    """
    Workflow owner, maybe anonymous. (Django model -- TODO use something else.)

    Required for init, and must be None afterwards.

    This does not follow the `Optional[_Null, ...]]` convention. The `owner` is
    useful during `Init` and it must be `None` during `Update`. (An anonymous
    workflow may have `owner is None`.)
    """

    is_example: Optional[bool] = None
    """True if this is an 'example' workflow."""

    selected_tab_position: Optional[int] = None
    """
    Position of initial tab for the user to display.

    Required for init, and must be None afterwards.
    """

    name: Optional[str] = None
    """Workflow name, user-editable."""

    tab_slugs: Optional[List[str]] = None
    """Ordered list of tab slugs."""

    public: Optional[bool] = None
    """True means anybody can see it."""

    updated_at: Optional[datetime.datetime] = None
    """Time of last modification."""

    acl: Optional[List[AclEntry]] = None
    """Non-owners' permissions."""


@dataclass(frozen=True)
class StepUpdate:
    """
    Data for a new or existing Step with the given id (TODO use slug, nix id).

    Every field of an Update is Optional, default `None`. `None` means there
    is no update, and the client should keep whichever value it already had.
    A value of type Optional[Union[_Null, ...]] can be set to `Null`, which
    indicates that the client should change its value to `null`.
    """

    id: Optional[int] = None
    """
    Step identifier. TODO nix this and use slug as identifier.

    Required for creation, and must be None afterwards.
    """

    slug: Optional[str] = None
    """
    Step identifier.

    Required for creation, and must be None afterwards.
    """

    module_slug: Optional[str] = None
    """
    Module identifier.

    Required for creation and whenever `render_result` is not empty.
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

    render_result: Optional[Union[_Null, "CachedRenderResult"]] = None
    """
    Cached, maybe-stale render result.

    Null if there is no cached render result.

    If the cached-result delta ID is different from the _relevant_ delta ID,
    then the result is obsolete. The client may render obsolete data plus a
    progress indicator.
    
    When a `render_result` is provided, you must also pass a `module_slug`.
    This is so that `I18nMessage`s with source `"module"` in the result
    can be interpreted relative to their source module.
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

    last_fetched_at: Optional[Union[_Null, datetime.datetime]] = None
    """
    Time of last fetch, or Null.

    This time may be more recent than the latest FetchedVersion, if we polled a
    website and then decided not to create a new FetchedVersion.
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

    versions: Optional[FetchedVersionList] = None
    """
    Information about fetched versions.

    TODO redesign "versions" from scratch. They currently conflate all these
    cases:

    * We sometimes create new versions when remote websites change.
    * We sometimes create new versions when users change parameters.
    * We sometimes create new versions when module code changes.
    """

    def __post_init__(self):
        if self.render_result is not None:
            assert self.module_slug is not None  # (otherwise i18n will break)


@dataclass(frozen=True)
class TabUpdate:
    """
    Data for a new or existing Tab with the given slug.

    Every field of an Update is Optional, default `None`. `None` means there
    is no update, and the client should keep whichever value it already had.
    A value of type Optional[Union[_Null, ...]] can be set to `Null`, which
    indicates that the client should change its value to `null`.
    """

    slug: Optional[str] = None
    """
    Tab identifier.

    Required for creation, and must be None afterwards.
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
    A value of type Optional[Union[_Null, ...]] can be set to `Null`, which
    indicates that the client should change its value to `null`.

    This object is immutable. The update_xxx(), replace_xxx() and clear_xxx()
    methods return new objects. They do not modify the existing object.
    """

    workflow: Optional[WorkflowUpdate] = None
    """Workflow-wide data to replace."""

    modules: Dict[str, Module] = field(default_factory=dict)
    """Modules to add or replace, keyed by slug."""

    steps: Dict[int, StepUpdate] = field(default_factory=dict)
    """Steps to add or update, keyed by ID. TODO key by slug, not ID."""

    tabs: Dict[str, TabUpdate] = field(default_factory=dict)
    """Tabs to add or update, keyed by slug."""

    clear_tab_slugs: FrozenSet[str] = field(default_factory=frozenset)
    """Tab slugs the client should forget about."""

    clear_step_ids: FrozenSet[int] = field(default_factory=frozenset)
    """Step IDs the client should forget about. TODO use slugs, not IDs."""

    def update_tab(self, slug: str, **kwargs) -> Update:
        """Return an Update with added/modified tab values."""
        tabs = dict(self.tabs)  # shallow copy
        old_tab = tabs.get(slug, TabUpdate())
        tabs[slug] = replace(old_tab, **kwargs)
        return replace(self, tabs=tabs)

    def update_step(self, id: int, **kwargs) -> Update:
        """Return an Update with added/modified step values. TODO key by slug, not id."""
        steps = dict(self.steps)  # shallow copy
        old_step = steps.get(id, StepUpdate())
        steps[id] = replace(old_step, **kwargs)
        return replace(self, steps=steps)

    def update_workflow(self, **kwargs) -> Update:
        """Return an Update with modified workflow values."""
        if self.workflow is None:
            workflow = WorkflowUpdate()
        else:
            workflow = self.workflow
        return replace(self, workflow=replace(workflow, **kwargs))

    def replace_tab(self, slug: str, update: TabUpdate) -> Update:
        """Return an Update with a new Tab."""
        assert slug == update.slug
        return replace(self, tabs={**self.tabs, update.slug: update})

    def replace_step(self, id: int, update: StepUpdate) -> Update:
        """Return an Update with a new Step."""
        assert id == update.id
        return replace(self, steps={**self.steps, id: update})

    def replace_steps(self, updates: Dict[int, StepUpdate]) -> Update:
        """Return an Update with new or replaced Steps. TODO key by slug, not id."""
        return replace(self, steps={**self.steps, **updates})

    def clear_tab(self, slug: str) -> Update:
        """Return an Update that clears a Tab."""
        return replace(self, clear_tab_slugs=self.clear_tab_slugs.union([slug]))

    def clear_step(self, id: int) -> Update:
        """Return an Update that clears a Step. TODO key by slug, not id."""
        return replace(self, clear_step_ids=self.clear_step_ids.union([id]))

    def clear_steps(self, ids: Iterable[int]) -> Update:
        """Return an Update that clears Steps. TODO key by slug, not id."""
        return replace(self, clear_step_ids=self.clear_step_ids.union(ids))


@dataclass(frozen=True)
class Init:
    """
    Initial state to pass to the client.

    This is modeled after `Update`, with these differences:

    * There are no `clear_xxx` fields (because this is the initial state, so
      there's no state to clear).
    * The creator must ensure no Update values are `None`.
    """

    workflow: WorkflowUpdate
    modules: Dict[str, Module]
    steps: Dict[int, StepUpdate]  # TODO key by slug, not ID
    tabs: Dict[str, TabUpdate]

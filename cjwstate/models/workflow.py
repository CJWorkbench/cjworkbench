from __future__ import annotations

import datetime
import json
from contextlib import contextmanager
from dataclasses import dataclass
from typing import ContextManager, Dict, FrozenSet, List, Set, Tuple

from cjwmodule.spec.paramschema import ParamSchema
from django.contrib.auth.models import User
from django.db import connection, models, transaction
from django.db.models import Exists, F, OuterRef, Q, Sum, Value
from django.db.models.functions import Cast
from django.http import HttpRequest
from django.urls import reverse

from cjwstate import clientside, s3
from cjwstate.models.dbutil import user_display_name
from cjwstate.models.fields import Role
from cjwstate.modules.util import gather_param_tab_slugs


class Workflow(models.Model):
    class Meta:
        app_label = "cjworkbench"
        db_table = "workflow"

    # TODO when we upgrade to Django 2.2, uncomment this and figure out
    # how to migrate our previous RunSQL(CREATE UNIQUE INDEX) code to use it.
    #
    # What we have today: (We'll need to delete this comment and preserve the
    # index):
    # migrations.RunSQL([
    #     """
    #     CREATE UNIQUE INDEX unique_workflow_copy_by_session
    #     ON server_workflow (anonymous_owner_session_key,
    #                         original_workflow_id)
    #     WHERE anonymous_owner_session_key IS NOT NULL
    #       AND original_workflow_id IS NOT NULL
    #     """
    # ])
    #
    # What we want: (We'll want to use the index we previously made with
    # RunSQL())
    # class Meta:
    #     constraints: [
    #         # Each user can have only one "copy" of each original_workflow:
    #         # we don't have any concept of what multiple "copies" would be,
    #         # and right now they'd be lost.
    #         #
    #         # Index by anonymous_owner_session_key/owner_id first: it's more
    #         # likely to be unique.
    #         #
    #         # Don't index NULL values: not because they break business logic,
    #         # but because it would be inefficient.
    #         models.UniqueConstraint(fields=['anonymous_owner_session_key',
    #                                         'original_workflow_id'],
    #                                 name='unique_workflow_copy_by_session',
    #                                 condition=models.Q(
    #                                     anonymous_owner_session_key__isnull=False,
    #                                     original_workflow_id__isnull=False,
    #                                 ),
    #    ]

    name = models.CharField("name", max_length=200)
    creation_date = models.DateTimeField(auto_now_add=True)
    last_viewed_at = models.DateTimeField(default=datetime.datetime.now)
    """Most recent timestamp when _any user_ viewed the workflow.

    This was added 2019-06-18, so that's the minimum last_viewed_at value.
    """

    updated_at = models.DateTimeField(default=datetime.datetime.now)
    """Most recent call to cjwstate.commands.do(), undo() or redo()."""

    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, related_name="owned_workflows"
    )

    anonymous_owner_session_key = models.CharField(
        "anonymous_owner_session_key", max_length=40, null=True, blank=True
    )
    """Non-NULL when a non-user is editing a lesson workflow.

    An anonymous workflow behaves like a private one, except the browser URL
    points to the lesson (so when the end user shares, other people can open
    the URL -- albeit without the user's edits).
    """

    secret_id = models.CharField(blank=True, max_length=100)
    """URL-friendly string that functions as "ID+password".

    Blank string means, only the real ID may be used.
    """

    original_workflow_id = models.IntegerField(null=True, blank=True)
    """If this is a duplicate, the Workflow it is based on."""

    public = models.BooleanField(default=False)

    in_all_users_workflow_lists = models.BooleanField(default=False)
    """If true, all users will see this."""

    dataset_readme_md = models.TextField(
        "dataset_readme_md", max_length=65535, null=False, blank=True, default=""
    )
    """Markdown README.md to publish the next time the workflow is published."""

    lesson_slug = models.CharField("lesson_slug", max_length=100, null=True, blank=True)
    """A string like 'a-lesson' or 'a-course/a-lesson', or NULL.

    If set, this Workflow is the user's journey through a lesson in
    `server/lessons/` or `server/courses/`.

    If you ever change this to NOT NULL, edit `cron/lessonworkflowdeleter`!
    Otherwise most workflows will be deleted :).
    """

    # there is always a tab
    selected_tab_position = models.IntegerField(default=0)

    last_delta_id = models.IntegerField(default=0)
    """ID of the last Delta that was applied.

    This has a dual purpose:

    * `cjwstate.commands` sees it as "pointer into linked list". (But it
      isn't a foreign key! There may be no Delta here.)
    * `renderer` and its caching system uses delta IDs as cache keys. Every
      render request includes a `last_delta_id`. You must send a new render
      request every time `last_delta_id` changes; conversely, try to avoid
      changing `last_delta_id` when you _don't_ want a render request, because
      it may be expensive. ([2021-02-02, adamhooper] it isn't very expensive
      *today*, but we may change algorithms in the future....)

    0 is allowed. It's the default for a new (or duplicated) workflow.

    NULL is _not_ allowed. This isn't a foreign key; NULL would be akin to 0
    plus null-related quirks in calling code and in SQL.
    """

    has_custom_report = models.BooleanField(default=False)

    fetches_per_day = models.FloatField(null=False, default=0.0)
    """Cached summary count of fetches per day.

    This is `sum(86400 / step.update_interval for step in workflow.active_steps)`
    """

    @contextmanager
    def cooperative_lock(self):
        """Yields in a database transaction with self selected FOR UPDATE.

        Example:

            with workflow.cooperative_lock():
                # ... do stuff
                workflow.save()

        This is _cooperative_. It only works if every write uses this method.
        _Always_ use this method: writing without it is a bug.

        It is safe to call cooperative_lock() within a cooperative_lock(). The
        inner one will behave as a no-op.

        Take care with async functions. Transactions don't cross async
        boundaries, anything you `await` while you hold the cooperative lock
        won't be rolled back with the same rules as non-awaited code. You
        should still use cooperative_lock(); but instead of behaving like a
        database transaction, it will behave like a simple advisory lock; and
        _it cannot be nested_.
        """
        with transaction.atomic():
            # Lock the workflow, in the database.
            # This will block until the workflow is released.
            # https://docs.djangoproject.com/en/2.0/ref/models/querysets/#select-for-update
            #
            # list() executes the query
            list(Workflow.objects.select_for_update().filter(id=self.id))
            # save() overwrites all fields, so make sure we have the latest
            # versions.
            # https://code.djangoproject.com/ticket/28344#comment:10
            self.refresh_from_db()
            yield

    @property
    def live_tabs(self):
        return self.tabs.filter(is_deleted=False)

    def request_authorized_read(self, request: HttpRequest) -> bool:
        """True if the Django request may read workflow data."""
        return self.user_session_authorized_read(request.user, request.session)

    def request_authorized_write(self, request: HttpRequest) -> bool:
        """True if the Django request may write workflow data."""
        return self.user_session_authorized_write(request.user, request.session)

    def request_authorized_owner(self, request: HttpRequest) -> bool:
        """True if the Django request may write workflow data."""
        return self.user_session_authorized_owner(request.user, request.session)

    def request_authorized_report_viewer(self, request: HttpRequest) -> bool:
        """True if the Django request may write workflow data."""
        return self.user_session_authorized_report_viewer(request.user, request.session)

    @property
    def is_anonymous(self) -> bool:
        """True if the owner is an anonymous session, not a User.

        With an anonymous workflow:

        * The user can't enable auto-update
        * The user can't add notifications
        * The user can't add eval-style modules
        * We display a banner across the page suggesting the user log in

        Even logged-in users can hold anonymous workflows: these will have
        owner=None.
        """
        return self.anonymous_owner_session_key is not None

    def user_session_authorized_read(self, user, session):
        return (
            self.public
            or self.user_session_authorized_owner(user, session)
            or (
                user
                and not user.is_anonymous
                and self.acl.filter(
                    email=user.email, role__in={Role.EDITOR, Role.VIEWER}
                ).exists()
            )
        )

    def user_session_authorized_write(self, user, session):
        return self.user_session_authorized_owner(user, session) or (
            user
            and not user.is_anonymous
            and self.acl.filter(email=user.email, role=Role.EDITOR).exists()
        )

    def user_session_authorized_owner(self, user, session):
        return (user and user == self.owner) or (
            session
            and session.session_key
            and session.session_key == self.anonymous_owner_session_key
        )

    def user_session_authorized_report_viewer(self, user, session):
        return (
            self.public
            or self.user_session_authorized_owner(user, session)
            or (
                user
                and not user.is_anonymous
                and self.acl.filter(
                    email=user.email,
                    role__in={Role.EDITOR, Role.VIEWER, Role.REPORT_VIEWER},
                )
            )
        )

    @classmethod
    def owned_by_user_session(cls, user, session):
        # FIXME unit-test (security)
        if user and not user.is_anonymous:
            if session and session.session_key:
                mask = Q(owner_id=user.id) | Q(
                    anonymous_owner_session_key=session.session_key
                )
            else:
                mask = Q(owner_id=user.id)
        else:
            assert session and session.session_key
            mask = Q(anonymous_owner_session_key=session.session_key)
        return cls.objects.filter(mask)

    @classmethod
    @contextmanager
    def lookup_and_cooperative_lock(cls, **kwargs) -> ContextManager[Workflow]:
        """Efficiently lookup and lock a Workflow in one operation.

        Usage:

            with Workflow.lookup_and_cooperative_lock(pk=123) as workflow:
                # ... do stuff
                return True

        This is equivalent to:

            workflow = Workflow.objects.get(pk=123)
            with workflow.cooperative_lock()
                # ... do stuff

        But the latter runs three SQL queries, and this method uses just one.

        This is _cooperative_. It only works if every write uses this method.
        _Always_ use this method: writing without it is a bug.

        It is safe to call cooperative_lock() within a cooperative_lock(). The
        inner one will behave as a no-op.

        Take care with async functions. Transactions don't cross async
        boundaries, anything you `await` while you hold the cooperative lock
        won't be rolled back with the same rules as non-awaited code. You
        should still use cooperative_lock(); but instead of behaving like a
        database transaction, it will behave like a simple advisory lock; and
        _it cannot be nested_.

        Raise Workflow.DoesNotExist if it does not exist.
        """
        with transaction.atomic():
            workflow = Workflow.objects.select_for_update().get(**kwargs)
            yield workflow

    @classmethod
    @contextmanager
    def authorized_lookup_and_cooperative_lock(
        cls, level, user, session, **kwargs
    ) -> ContextManager[Workflow]:
        """Efficiently lookup, lock and authenticate a Workflow in one operation.

        Usage:

            with Workflow.authorized_lookup_and_cooperative_lock(
                'read', request.user, request.session, id=123
            ) as workflow:
                # ... do stuff with workflow

        This is _cooperative_. It only works if every write uses this method.
        _Always_ use this method: writing without it is a bug.

        It is safe to call cooperative_lock() within a cooperative_lock(). The
        inner one will behave as a no-op.

        Take care with async functions. Transactions don't cross async
        boundaries, anything you `await` while you hold the cooperative lock
        won't be rolled back with the same rules as non-awaited code. You
        should still use cooperative_lock(); but instead of behaving like a
        database transaction, it will behave like a simple advisory lock; and
        _it cannot be nested_.

        Raise Workflow.DoesNotExist if it does not exist or if access is denied.
        To check for access-denied, test whether
        `err.args[0].endswith('access denied')`. (TODO revisit this oddity.)
        """
        with cls.lookup_and_cooperative_lock(**kwargs) as workflow:
            access = getattr(workflow, "user_session_authorized_%s" % level)
            if not access(user, session):
                raise cls.DoesNotExist("%s access denied" % level)

            yield workflow

    @staticmethod
    def create_and_init(**kwargs):
        """Create and return a _valid_ Workflow: one with a Tab and a Delta."""
        with transaction.atomic():
            workflow = Workflow.objects.create(**kwargs)
            workflow.tabs.create(position=0, slug="tab-1", name="Tab 1")
            return workflow

    def duplicate(self, owner: User) -> "Workflow":
        """
        Save and return a duplicate Workflow owned by `user`.

        The duplicate will have no undo history.
        """
        new_name = f"Copy of {self.name}"  # TODO i18n

        with self.cooperative_lock():
            wf = Workflow.objects.create(
                name=new_name,
                owner=owner,
                original_workflow_id=self.pk,
                selected_tab_position=self.selected_tab_position,
                has_custom_report=self.has_custom_report,
                public=False,
                fetches_per_day=0,  # duplicated steps are manual-update
                last_delta_id=0,  # SECURITY don't clone info we don't need
            )

            tabs = list(self.live_tabs)
            for tab in tabs:
                tab.duplicate_into_new_workflow(wf)

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    WITH tab_id_map AS (
                        SELECT
                            tab1.id AS old_id,
                            tab2.id AS new_id
                        FROM tab tab1
                        INNER JOIN tab tab2 ON tab1.slug = tab2.slug
                        WHERE tab1.workflow_id = %(old_workflow_id)s
                          AND tab2.workflow_id = %(new_workflow_id)s
                    ),
                    step_id_map AS (
                        SELECT
                            step1.id AS old_id,
                            step2.id AS new_id
                        FROM step step1
                        INNER JOIN tab tab1 ON step1.tab_id = tab1.id
                        INNER JOIN tab tab2 ON tab1.slug = tab2.slug
                        INNER JOIN step step2 ON step2.tab_id = tab2.id AND step2.slug = step1.slug
                        WHERE tab1.workflow_id = %(old_workflow_id)s
                          AND tab2.workflow_id = %(new_workflow_id)s
                    )
                    INSERT INTO block (
                        workflow_id,
                        slug,
                        position,
                        block_type,
                        text_markdown,
                        tab_id,
                        step_id
                    )
                    SELECT
                        %(new_workflow_id)s,
                        slug,
                        position,
                        block_type,
                        text_markdown,
                        (SELECT tab_id_map.new_id FROM tab_id_map WHERE tab_id_map.old_id = block.tab_id),
                        (SELECT step_id_map.new_id FROM step_id_map WHERE step_id_map.old_id = block.step_id)
                    FROM block
                    WHERE workflow_id = %(old_workflow_id)s
                    """,
                    {
                        "old_workflow_id": self.id,
                        "new_workflow_id": wf.id,
                    },
                )

        return wf

    def __str__(self):
        return self.name + " - id: " + str(self.id)

    def are_all_render_results_fresh(self):
        """Query whether all live Steps are rendered."""
        from .step import Step

        for step in Step.live_in_workflow(self):
            if step.cached_render_result is None:
                return False
        return True

    def recalculate_fetches_per_day(self):
        """Run database query to update self.fetches_per_day; do not save."""
        from .step import Step

        result = (
            Step.live_in_workflow(self)
            .filter(auto_update_data=True, update_interval__gt=0)
            .aggregate(
                fetches_per_day=Sum(
                    Value(86400.0, output_field=models.FloatField())
                    / Cast(F("update_interval"), output_field=models.FloatField())
                )
            )
        )
        # Did You Know: SQL SUM() of empty set is NULL, not 0? Hence "or 0.0" here
        self.fetches_per_day = result["fetches_per_day"] or 0.0

    def delete_orphan_soft_deleted_tabs(self):
        return (
            self.tabs.filter(is_deleted=True)
            .exclude(Exists(self.deltas.filter(tab_id=OuterRef("id"))))
            .delete()
        )

    def delete_orphan_soft_deleted_steps(self):
        from cjwstate.models import Step

        return (
            Step.objects.filter(tab__workflow_id=self.id, is_deleted=True)
            .exclude(Exists(self.deltas.filter(step_id=OuterRef("id"))))
            .delete()
        )

    def delete_orphan_soft_deleted_models(self):
        """Delete soft-deleted Tabs and Steps that have no Delta.

        (The tests for this are in test_Delta.py, for legacy reasons.)
        """
        self.delete_orphan_soft_deleted_tabs()  # (deletes their steps, of course)
        self.delete_orphan_soft_deleted_steps()

    def delete(self, *args, **kwargs):
        # Clear delta history. Deltas can reference Steps: if we don't
        # clear the deltas, Django may decide to CASCADE to Step first and
        # we'll raise a ProtectedError.
        self.deltas.all().delete()

        # Next, clear Report blocks. Their Step/Tab ON_DELETE is models.PROTECT,
        # because [2020-11-30, adamhooper] we want to test for months before
        # we're confident that we don't delete blocks at the wrong times.
        self.blocks.all().delete()

        # Clear all s3 data. We _should_ clear it in pre-delete hooks on
        # StoredObject, UploadedFile, etc.; but [2019-06-03, adamhooper] the
        # database is inconsistent and Django is hard to use so new bugs may
        # crop up anyway.
        #
        # [2019-06-03, adamhooper] hooks never work in ORMs. Better would be
        # to make `delete()` a controller method, not a funky mishmash of
        # Django-ORM absurdities. TODO nix Django ORM.
        #
        # TL;DR we're double-deleting s3 data, to be extra-safe. The user
        # said "delete." We'll delete.
        if self.id:  # be extra-safe: use if-statement so we don't remove '/'
            s3.remove_recursive(s3.StoredObjectsBucket, f"{self.id}/")
            s3.remove_recursive(s3.UserFilesBucket, f"wf-{self.id}/")

        super().delete(*args, **kwargs)

    def to_clientside(
        self,
        *,
        include_tab_slugs: bool = True,
        include_block_slugs: bool = True,
        include_acl: bool = True,
        include_dataset: bool = False,
    ) -> clientside.WorkflowUpdate:
        if include_tab_slugs:
            tab_slugs = list(self.live_tabs.values_list("slug", flat=True))
        else:
            tab_slugs = None  # faster (for index page)

        if include_block_slugs:
            block_slugs = list(self.blocks.values_list("slug", flat=True))
        else:
            block_slugs = None  # faster (for index page)

        if include_acl:
            acl = [
                clientside.AclEntry(email=e.email, role=e.role.value)
                for e in self.acl.all()
            ]
        else:
            acl = None  # more privacy (for report-viewer)

        if include_dataset:
            try:
                with s3.temporarily_download(
                    s3.DatasetsBucket, f"/wf-{self.id}/datapackage.json"
                ) as path:
                    dataset = json.loads(path.read_bytes())
            except FileNotFoundError:
                dataset = None
        else:
            dataset = None

        return clientside.WorkflowUpdate(
            id=self.id,
            secret_id=self.secret_id,  # if you can read it, you can link to it
            owner_email=self.owner.email if self.owner else None,
            owner_display_name=user_display_name(self.owner) if self.owner else None,
            selected_tab_position=self.selected_tab_position,
            name=self.name,
            tab_slugs=tab_slugs,
            has_custom_report=self.has_custom_report,
            block_slugs=block_slugs,
            public=self.public,
            updated_at=self.updated_at,
            fetches_per_day=self.fetches_per_day,
            acl=acl,
            dataset=dataset,
        )


def _schema_contains_tabs(schema: ParamSchema) -> bool:
    """Determine whether a ParamSchema contains a Tab, recursively."""
    if isinstance(schema, ParamSchema.List):
        return _schema_contains_tabs(schema.inner_schema)
    elif isinstance(schema, ParamSchema.Dict):
        return any(
            _schema_contains_tabs(inner_schema)
            for inner_schema in schema.properties.values()
        )
    elif isinstance(schema, ParamSchema.Map):
        return _schema_contains_tabs(schema.value_schema)
    elif isinstance(schema, ParamSchema.Tab):
        return True
    elif isinstance(schema, ParamSchema.Multitab):
        return True
    else:
        return False


@dataclass(frozen=True)
class DependencyGraph:
    """A graph illustrating which Steps depend on which Steps' output.

    Here are the data structures:

        * `.tabs` List of (slug, [StepIds])
        * `.steps` Dict (keyed by id) of (depends_on_tab_slugs:Set(...))

    We strive for consistent output order given the same inputs. Step IDs
    are always ordered first by tab, then by order within the tab. This makes
    code easier to test and debug.
    """

    @dataclass(frozen=True)
    class Tab:
        slug: str
        step_ids: List[int]
        """List of Steps that depend on one another.

        A Step with a `tab` param depends on the last value in this list.
        """

    @dataclass(frozen=True)
    class Step:
        """
        Metadata we track about a single Step.

        (This is stored in `steps`, which is keyed by step_id.)
        """

        depends_on_tab_slugs: FrozenSet[str]
        """
        Tabs which must be completed before this Step can run.
        """

    tabs: List[DependencyGraph.Tab]
    steps: Dict[int, Step]  # keyed by step_id

    @classmethod
    def load_from_workflow(cls, workflow: Workflow) -> DependencyGraph:
        """Create a DependencyGraph using the database.

        Must be called within a `workflow.cooperative_lock()`.

        Missing or deleted modules are deemed to have no dependencies.
        """
        from cjwstate.models.module_registry import MODULE_REGISTRY

        module_zipfiles = MODULE_REGISTRY.all_latest()

        tabs = []
        steps = {}

        for tab in workflow.live_tabs:
            tab_step_ids = []

            for step in tab.live_steps:
                tab_step_ids.append(step.id)
                try:
                    module_zipfile = module_zipfiles[step.module_id_name]
                except KeyError:
                    steps[step.id] = cls.Step(frozenset())
                    continue

                module_spec = module_zipfile.get_spec()
                schema = module_spec.param_schema

                # Optimization: don't migrate_params() if we know there are no
                # tab params. (get_migrated_params() invokes module code, so we
                # prefer to wait and let it run in the renderer.
                if not _schema_contains_tabs(schema):
                    steps[step.id] = cls.Step(frozenset())
                    continue

                from cjwstate.params import get_migrated_params

                params = get_migrated_params(step)

                # raises ValueError (and we don't handle that right now)
                schema.validate(params)
                steps[step.id] = cls.Step(gather_param_tab_slugs(schema, params))

            tabs.append(cls.Tab(tab.slug, tab_step_ids))

        return cls(tabs, steps)

    def _get_dependent_ids_step(self, tab_slugs: Set[str]) -> Tuple[Set[int], Set[str]]:
        """Find `(set(new_step_ids), set(tab_slugs_of_new_step_ids))`."""
        step_ids = set()
        new_tab_slugs = set()
        for tab in self.tabs:
            dependent = False
            for step_id in tab.step_ids:
                step = self.steps[step_id]
                if not dependent:
                    step = self.steps[step_id]
                    if step.depends_on_tab_slugs & tab_slugs:
                        dependent = True
                        if tab.slug not in tab_slugs:
                            new_tab_slugs.add(tab.slug)
                if dependent:
                    step_ids.add(step_id)
        return (step_ids, new_tab_slugs)

    def get_step_ids_depending_on_tab_slug(self, tab_slug: str) -> List[int]:
        return self.get_step_ids_depending_on_tab_slugs(set([tab_slug]))

    def get_step_ids_depending_on_tab_slugs(self, tab_slugs: Set[str]) -> List[int]:
        step_ids = set()
        tab_slugs = set(tab_slugs)  # don't mutate input

        while True:
            new_step_ids, new_tab_slugs = self._get_dependent_ids_step(tab_slugs)
            step_ids = step_ids | new_step_ids
            # Every step, we must add new tabs to inspect. If we don't have any
            # new tabs to inspect, that's because we've inspected all the tabs;
            # we're done.
            if not (new_tab_slugs - tab_slugs):
                break
            tab_slugs.update(new_tab_slugs)

        ret = []  # sort step_ids
        for tab in self.tabs:
            for step_id in tab.step_ids:
                if step_id in step_ids:
                    ret.append(step_id)
        return ret

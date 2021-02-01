from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass
import datetime
from typing import Callable, Dict, List, Optional, Set, Tuple, FrozenSet
from django.db import connection, models, transaction
from django.db.models import Q
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.urls import reverse
from cjworkbench.models.db_object_cooperative_lock import (
    DbObjectCooperativeLock,
    lookup_and_cooperative_lock,
)
from cjwstate import clientside, s3
from cjwstate.modules.param_spec import ParamDType


def _find_orphan_soft_deleted_tabs(workflow_id: int) -> models.QuerySet:
    from cjwstate.models import Delta, Tab

    # all Delta subclasses that have a tab_id
    relations = [
        f
        for f in Tab._meta.get_fields()
        if f.is_relation and issubclass(f.related_model, Delta)
    ]

    tab_table_alias = Tab._meta.db_table  # Django auto-name

    conditions = [
        f"""
        NOT EXISTS (
            SELECT TRUE
            FROM {r.related_model._meta.db_table}
            WHERE {r.get_joining_columns()[0][1]} = {tab_table_alias}.id
        )
        """
        for r in relations
    ]

    return Tab.objects.filter(workflow_id=workflow_id, is_deleted=True).extra(
        where=conditions
    )


def _find_orphan_soft_deleted_steps(workflow_id: int) -> models.QuerySet:
    from cjwstate.models import Delta, Step

    # all Delta subclasses that have a step_id
    relations = [
        f
        for f in Step._meta.get_fields()
        if f.is_relation and issubclass(f.related_model, Delta)
    ]

    step_table_alias = Step._meta.db_table  # Django auto-name

    conditions = [
        f"""
        NOT EXISTS (
            SELECT TRUE
            FROM {r.related_model._meta.db_table}
            WHERE {r.get_joining_columns()[0][1]} = {step_table_alias}.id
        )
        """
        for r in relations
    ]

    return Step.objects.filter(tab__workflow_id=workflow_id, is_deleted=True).extra(
        where=conditions
    )


class Workflow(models.Model):
    class Meta:
        app_label = "server"
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
    #     """,
    #     """
    #     CREATE UNIQUE INDEX unique_workflow_copy_by_user
    #     ON server_workflow (owner_id, original_workflow_id)
    #     WHERE owner_id IS NOT NULL
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
    #         models.UniqueConstraint(fields=['owner_id', 'original_workflow_id'],
    #                                 name='unique_workflow_copy_by_user',
    #                                 condition=models.Q(
    #                                     owner_id__isnull=False,
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
    """Non-NULL when this is a copy of a of an example workflow.

    Anybody who is not the owner can open an "anonymous" _duplicate_ of the
    workflow, whether that person is logged in or not. An anonymous workflow
    behaves like a private one, except:

        * The browser URL points to the original workflow (so when the end user
          shares, other people can open the URL -- albeit without the user's
          edits being visible to others)
        * `url_id` != `pk`
    """

    original_workflow_id = models.IntegerField(null=True, blank=True)
    """If this is a duplicate, the Workflow it is based on.

    TODO add last_delta_id? Currently, we only use this field for `url_id`.
    """

    public = models.BooleanField(default=False)

    example = models.BooleanField(default=False)
    """If true, users opening this Workflow will just see a duplicate of it."""

    in_all_users_workflow_lists = models.BooleanField(default=False)
    """If true, all users will see this (you may also want example=True)."""

    lesson_slug = models.CharField("lesson_slug", max_length=100, null=True, blank=True)
    """A string like 'a-lesson' or 'a-course/a-lesson', or NULL.

    If set, this Workflow is the user's journey through a lesson in
    `server/lessons/` or `server/courses/`.
    """

    # there is always a tab
    selected_tab_position = models.IntegerField(default=0)

    last_delta = models.ForeignKey(
        "server.Delta",  # string, not model -- avoids circular import
        related_name="+",  # + means no backward link
        blank=True,
        null=True,  # if null, no Commands applied yet
        default=None,
        on_delete=models.SET_NULL,
    )

    has_custom_report = models.BooleanField(default=False)

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
            workflow_lock = DbObjectCooperativeLock("workflow", self)
            yield workflow_lock

        # If we reach here, COMMIT was called and we're returning whatever
        # the `yield` block returned.
        workflow_lock._invoke_after_commit_callbacks()

    @property
    def live_tabs(self):
        return self.tabs.filter(is_deleted=False)

    @property
    def url_id(self) -> int:
        """ID we display in the URL when presenting this Workflow.

        When this is a duplicate of a demo Workflow, the ID we present is the
        _demo_ Workflow ID, not this Workflow's ID.
        """
        if self.is_anonymous:
            return self.original_workflow_id
        else:
            return self.pk

    def request_authorized_read(self, request: HttpRequest) -> bool:
        """True if the Django request may read workflow data."""
        return self.user_session_authorized_read(request.user, request.session)

    def request_authorized_write(self, request: HttpRequest) -> bool:
        """True if the Django request may write workflow data."""
        return self.user_session_authorized_write(request.user, request.session)

    def request_authorized_owner(self, request: HttpRequest) -> bool:
        """True if the Django request may write workflow data."""
        return self.user_session_authorized_owner(request.user, request.session)

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
            or (user and user == self.owner)
            or (
                session
                and session.session_key
                and session.session_key == self.anonymous_owner_session_key
            )
            or (
                user
                and not user.is_anonymous
                and self.acl.filter(email=user.email).exists()
            )
        )

    def user_session_authorized_write(self, user, session):
        return (
            (user and user == self.owner)
            or (
                session
                and session.session_key
                and session.session_key == self.anonymous_owner_session_key
            )
            or (
                user
                and not user.is_anonymous
                and self.acl.filter(email=user.email, can_edit=True).exists()
            )
        )

    def user_session_authorized_owner(self, user, session):
        return (user and user == self.owner) or (
            session
            and session.session_key
            and session.session_key == self.anonymous_owner_session_key
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
    def lookup_and_cooperative_lock(
        cls, **kwargs
    ) -> ContextManager[DbObjectCooperativeLock]:
        """Efficiently lookup and lock a Workflow in one operation.

        Usage:

            with Workflow.lookup_and_cooperative_lock(pk=123) as workflow_lock:
                workflow = workflow_lock.workflow
                # ... do stuff
                workflow.after_commit(lambda: print("called after commit, before True is returned"))
                return True

        This is equivalent to:

            workflow = Workflow.objects.get(pk=123)
            with workflow.cooperative_lock() as workflow_lock:
                # ... do stuff

        But the latter runs three SQL queries, and this method uses just one.

        Raises Workflow.DoesNotExist.
        """
        return lookup_and_cooperative_lock(cls.objects, "workflow", **kwargs)

    @classmethod
    @contextmanager
    def authorized_lookup_and_cooperative_lock(cls, level, user, session, **kwargs):
        """Efficiently lookup and lock a Workflow in one operation.

        Usage:

            with Workflow.authorized_lookup_and_cooperative_lock('read', request.user,
                                                                 request.session,
                                                                 pk=123) as workflow_lock:
                # ... do stuff with workflow_lock.workflow

        Raise Workflow.DoesNotExist when it does not exist. (To check if access was
        denied, check `err.args[0].endswith('access denied')`. TODO revisit this oddity.)
        """
        with cls.lookup_and_cooperative_lock(**kwargs) as workflow_lock:
            workflow = workflow_lock.workflow
            access = getattr(workflow, "user_session_authorized_%s" % level)
            if not access(user, session):
                raise cls.DoesNotExist("%s access denied" % level)

            yield workflow_lock

    @staticmethod
    def create_and_init(**kwargs):
        """Create and return a _valid_ Workflow: one with a Tab and a Delta."""
        from cjwstate.models.commands import InitWorkflow

        with transaction.atomic():
            workflow = Workflow.objects.create(**kwargs)
            InitWorkflow.create(workflow)
            workflow.tabs.create(position=0, slug="tab-1", name="Tab 1")
            return workflow

    def _duplicate(
        self, name: str, owner: Optional[User], session_key: Optional[str]
    ) -> "Workflow":
        with self.cooperative_lock():
            wf = Workflow.objects.create(
                name=name,
                owner=owner,
                original_workflow_id=self.pk,
                anonymous_owner_session_key=session_key,
                selected_tab_position=self.selected_tab_position,
                has_custom_report=self.has_custom_report,
                public=False,
                last_delta=None,
            )

            # Set wf.last_delta and wf.last_delta_id, so we can render.
            # Import here to avoid circular deps
            from cjwstate.models.commands import InitWorkflow

            InitWorkflow.create(wf)

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

    def duplicate(self, owner: User) -> "Workflow":
        """
        Save and return a duplicate Workflow owned by `user`.

        The duplicate will have no undo history.
        """
        new_name = f"Copy of {self.name}"
        return self._duplicate(new_name, owner=owner, session_key=None)

    def duplicate_anonymous(self, session_key: str) -> "Workflow":
        """Save and return a new Workflow with the same contents as this one.

        The duplicate will have no undo history.
        """
        return self._duplicate(self.name, owner=None, session_key=session_key)

    def get_absolute_url(self):
        return reverse("workflow", args=[str(self.pk)])

    def __str__(self):
        return self.name + " - id: " + str(self.id)

    def are_all_render_results_fresh(self):
        """Query whether all live Steps are rendered."""
        from .Step import Step

        for step in Step.live_in_workflow(self):
            if step.cached_render_result is None:
                return False
        return True

    def clear_deltas(self):
        """Become a single-Delta Workflow."""
        from cjwstate.models.commands import InitWorkflow
        from cjwstate.models import Delta

        try:
            first_delta = self.deltas.get(prev_delta_id=None)
            self.last_delta_id = first_delta.id
            self.save(update_fields=["last_delta_id"])
        except Delta.DoesNotExist:
            # Integrity error: missing Delta. Repair.
            first_delta = InitWorkflow.create(self)

        try:
            # Select the _second_ delta.
            second_delta = first_delta.next_delta
        except Delta.DoesNotExist:
            # We're already a 1-delta Workflow
            return

        second_delta.delete_with_successors()
        self.delete_orphan_soft_deleted_models()

    def delete_orphan_soft_deleted_tabs(self):
        _find_orphan_soft_deleted_tabs(self.id).delete()

    def delete_orphan_soft_deleted_steps(self):
        _find_orphan_soft_deleted_steps(self.id).delete()

    def delete_orphan_soft_deleted_models(self):
        """Delete soft-deleted Tabs and Steps that have no Delta.

        (The tests for this are in test_Delta.py, for legacy reasons.)
        """
        self.delete_orphan_soft_deleted_tabs()
        self.delete_orphan_soft_deleted_steps()

    def delete(self, *args, **kwargs):
        # Clear delta history. Deltas can reference Steps: if we don't
        # clear the deltas, Django may decide to CASCADE to Step first and
        # we'll raise a ProtectedError.
        self.clear_deltas()

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
        self, *, include_tab_slugs: bool = True, include_block_slugs: Bool = True
    ) -> clientside.WorkflowUpdate:
        if include_tab_slugs:
            tab_slugs = list(self.live_tabs.values_list("slug", flat=True))
        else:
            tab_slugs = None  # faster (for index page)

        if include_block_slugs:
            block_slugs = list(self.blocks.values_list("slug", flat=True))
        else:
            block_slugs = None  # faster (for index page)

        return clientside.WorkflowUpdate(
            id=self.id,
            url_id=self.url_id,
            owner=self.owner,
            is_example=self.example,
            selected_tab_position=self.selected_tab_position,
            name=self.name,
            tab_slugs=tab_slugs,
            has_custom_report=self.has_custom_report,
            block_slugs=block_slugs,
            public=self.public,
            updated_at=self.updated_at,
            acl=[
                clientside.AclEntry(email=e.email, can_edit=e.can_edit)
                for e in self.acl.all()
            ],
        )


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
                    steps[step.id] = cls.Step(set())
                    continue

                module_spec = module_zipfile.get_spec()
                schema = module_spec.get_param_schema()

                # Optimization: don't migrate_params() if we know there are no
                # tab params. (get_migrated_params() invokes module code, and
                # we'd prefer for module code to execute only in the renderer.)
                if all(
                    (
                        (
                            not isinstance(dtype, ParamDType.Tab)
                            and not isinstance(dtype, ParamDType.Multitab)
                        )
                        for dtype, v in schema.iter_dfs_dtype_values(
                            schema.coerce(None)
                        )
                    )
                ):
                    # There are no tab params.
                    steps[step.id] = cls.Step(set())
                    continue

                from cjwstate.params import get_migrated_params

                params = get_migrated_params(step)

                # raises ValueError (and we don't handle that right now)
                schema.validate(params)
                tab_slugs = frozenset(
                    v
                    for dtype, v in schema.iter_dfs_dtype_values(params)
                    if isinstance(dtype, ParamDType.Tab)
                )
                steps[step.id] = cls.Step(tab_slugs)

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

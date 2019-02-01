from contextlib import contextmanager
from typing import Optional
import warnings
from django.db import models, transaction
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.urls import reverse
from .Lesson import Lesson


# A Workflow is the user's "document," a series of Modules
class Workflow(models.Model):
    name = models.CharField('name', max_length=200)
    creation_date = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        related_name='owned_workflows'
    )

    anonymous_owner_session_key = models.CharField(
        'anonymous_owner_session_key',
        max_length=40,
        null=True, blank=True
    )
    """
    Non-NULL when this is a copy of a of an example workflow.

    Anybody who is not the owner can open an "anonymous" _duplicate_ of the
    workflow, whether that person is logged in or not. An anonymous workflow
    behaves like a private one, except:

        * The browser URL points to the original workflow (so when the end user
          shares, other people can open the URL -- albeit without the user's
          edits being visible to others)
        * `url_id` != `pk`
    """

    original_workflow_id = models.IntegerField(null=True, blank=True)
    """
    If this is a duplicate, the Workflow it is based on.

    TODO add last_delta_id? Currently, we only use this field for `url_id`.
    """

    public = models.BooleanField(default=False)
    example = models.BooleanField(default=False)    # if set, will be duplicated for new users
    in_all_users_workflow_lists = models.BooleanField(default=False)
    lesson_slug = models.CharField('lesson_slug', max_length=100,
                                   null=True, blank=True)

    # there is always a tab
    selected_tab_position = models.IntegerField(default=0)

    last_delta = models.ForeignKey('server.Delta',                # specify as string to avoid circular import
                                   related_name='+',              # + means no backward link
				                   blank=True,
                                   null=True,   # if null, no Commands applied yet
                                   default=None,
                                   on_delete=models.SET_DEFAULT)

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
        return self.user_session_authorized_read(request.user,
                                                 request.session)

    def request_authorized_write(self, request: HttpRequest) -> bool:
        """True if the Django request may write workflow data."""
        return self.user_session_authorized_write(request.user,
                                                  request.session)

    def request_authorized_owner(self, request: HttpRequest) -> bool:
        """True if the Django request may write workflow data."""
        return self.user_session_authorized_owner(request.user,
                                                  request.session)

    def request_read_only(self, request: HttpRequest) -> bool:
        return self.request_authorized_read(request) \
                and not self.request_authorized_write(request)

    @property
    def is_anonymous(self) -> bool:
        """
        True if the owner is an anonymous session, not a User.

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
            or (session and session.session_key
                and session.session_key == self.anonymous_owner_session_key)
            or (user and not user.is_anonymous
                and self.acl.filter(email=user.email).exists())
        )

    def user_session_authorized_write(self, user, session):
        return (
            (user and user == self.owner)
            or (session and session.session_key
                and session.session_key == self.anonymous_owner_session_key)
            or (user and not user.is_anonymous
                and self.acl.filter(email=user.email, can_edit=True).exists())
        )

    def user_session_authorized_owner(self, user, session):
        return (
            (user and user == self.owner)
            or (session and session.session_key
                and session.session_key == self.anonymous_owner_session_key)
        )

    def read_only(self, user):
        warnings.warn("FIXME read_only() should be request_read_only()")
        return user != self.owner

    def last_update(self):
        if not self.last_delta:
            return self.creation_date
        return self.last_delta.datetime

    @classmethod
    @contextmanager
    def lookup_and_cooperative_lock(cls, **kwargs):
        """
        Efficiently lookup and lock a Workflow in one operation.

        Usage:

            with Workflow.lookup_and_cooperative_lock(pk=123) as workflow:
                # ... do stuff

        This is equivalent to:

            workflow = Workflow.objects.get(pk=123)
            with workflow.cooperative_lock():
                # ... do stuff

        But the latter runs three SQL queries, and this method uses just one.

        Raises Workflow.DoesNotExist.
        """
        with transaction.atomic():
            yield cls.objects.select_for_update().get(**kwargs)

    @classmethod
    @contextmanager
    def authorized_lookup_and_cooperative_lock(cls, level, user, session,
                                               **kwargs):
        """
        Efficiently lookup and lock a Workflow in one operation.

        Usage:

            with Workflow.lookup_and_cooperative_lock('read', request.user,
                                                      request.session,
                                                      pk=123) as workflow:
                # ... do stuff

        Raises Workflow.DoesNotExist.
        """
        with cls.lookup_and_cooperative_lock(**kwargs) as workflow:
            access = getattr(workflow, 'user_session_authorized_%s' % level)
            if not access(user, session):
                raise cls.DoesNotExist('%s access denied' % level)

            yield workflow

    @staticmethod
    def create_and_init(**kwargs):
        """Create and return a _valid_ Workflow: one with a Tab and a Delta."""
        from server.models.commands import InitWorkflowCommand
        with transaction.atomic():
            workflow = Workflow.objects.create(**kwargs)
            InitWorkflowCommand.create(workflow)
            workflow.tabs.create(position=0, slug='tab-1', name='Tab 1')
            return workflow

    def _duplicate(self, name: str, owner: Optional[User],
                   session_key: Optional[str]) -> 'Workflow':
        with self.cooperative_lock():
            wf = Workflow.objects.create(
                name=name,
                owner=owner,
                original_workflow_id=self.pk,
                anonymous_owner_session_key=session_key,
                selected_tab_position=self.selected_tab_position,
                public=False,
                last_delta=None
            )

            # Set wf.last_delta and wf.last_delta_id, so we can render.
            # Import here to avoid circular deps
            from server.models.commands import InitWorkflowCommand
            InitWorkflowCommand.create(wf)

            tabs = list(self.live_tabs)
            for tab in tabs:
                tab.duplicate(wf)

        return wf

    def duplicate(self, owner: User) -> 'Workflow':
        """
        Save and return a duplicate Workflow owned by `user`.

        The duplicate will have no undo history.
        """
        new_name = f'Copy of {self.name}'
        return self._duplicate(new_name, owner=owner, session_key=None)

    def duplicate_anonymous(self, session_key: str) -> 'Workflow':
        """
        Save and return a new Workflow with the same contents as this one.

        The duplicate will have no undo history.
        """
        return self._duplicate(self.name, owner=None, session_key=session_key)

    def get_absolute_url(self):
        return reverse('workflow', args=[str(self.pk)])

    def __str__(self):
        return self.name + ' - id: ' + str(self.id)

    def are_all_render_results_fresh(self):
        """Query whether all live WfModules are rendered."""
        from .WfModule import WfModule
        for wf_module in WfModule.live_in_workflow(self):
            if wf_module.cached_render_result is None:
                return False
        return True

    @property
    def lesson(self):
        if self.lesson_slug is None:
            return None
        else:
            try:
                return Lesson.objects.get(self.lesson_slug)
            except Lesson.DoesNotExist:
                return None

    def clear_deltas(self):
        """Become a single-Delta Workflow."""
        from server.models.commands import InitWorkflowCommand

        try:
            from server.models import Delta
            first_delta = self.deltas.get(prev_delta_id=None)
        except Delta.DoesNotExist:
            # Invariant failed. Defensive programming: recover.
            first_delta = InitWorkflowCommand.create(self)

        if not isinstance(first_delta, InitWorkflowCommand):
            # Invariant failed: first delta should be InitWorkflowCommand.
            # Defensive programming: recover. Delete _every_ Delta, and then
            # add the one that belongs.
            first_delta.delete()
            first_delta = InitWorkflowCommand.create(self)
        else:
            self.last_delta_id = first_delta.id
            self.save(update_fields=['last_delta_id'])

        try:
            # Select the _second_ delta.
            second_delta = first_delta.next_delta
        except Delta.DoesNotExist:
            # We're already a 1-delta Workflow
            return

        second_delta.delete_with_successors()

    def delete(self, *args, **kwargs):
        # Clear delta history. Deltas can reference WfModules: if we don't
        # clear the deltas, Django may decide to CASCADE to WfModule first and
        # we'll raise a ProtectedError.
        self.clear_deltas()

        super().delete(*args, **kwargs)

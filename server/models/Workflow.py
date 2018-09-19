from contextlib import contextmanager
from django.db import models, transaction
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.urls import reverse
from server.models.Lesson import Lesson
from typing import Optional
import warnings

# A Workflow is the user's "document," a series of Modules
class Workflow(models.Model):
    name = models.CharField('name',max_length=200)
    creation_date = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True)

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

    TODO add revision? Currently, we only use this field for `url_id`.
    """

    public = models.BooleanField(default=False)
    example = models.BooleanField(default=False)    # if set, will be duplicated for new users
    in_all_users_workflow_lists = models.BooleanField(default=False)
    lesson_slug = models.CharField('lesson_slug', max_length=100,
                                   null=True, blank=True)

    selected_wf_module = models.IntegerField(default=None, null=True, blank=True)

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
        return (
            (request.user and request.user == self.owner) \
            or (request.session.session_key \
                and request.session.session_key == self.anonymous_owner_session_key)
        )

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
        )

    def read_only(self, user):
        warnings.warn("FIXME read_only() should be request_read_only()")
        return user != self.owner

    def last_update(self):
        if not self.last_delta:
            return self.creation_date
        return self.last_delta.datetime

    # use last delta ID as (non sequential) revision number, as later deltas
    # will always have later ids
    def revision(self):
        if not self.last_delta_id:
            return 0
        else:
            return self.last_delta_id

    def _duplicate(self, name: str, owner: Optional[User],
                   session_key: Optional[str]) -> 'Workflow':
        with self.cooperative_lock():
            new_wf = Workflow.objects.create(name=name, owner=owner,
                                             original_workflow_id=self.pk,
                                             anonymous_owner_session_key=session_key,
                                             selected_wf_module=self.selected_wf_module,
                                             public=False, last_delta=None)
            for wfm in self.wf_modules.all():
                wfm.duplicate(new_wf)

        return new_wf

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

    @property
    def lesson(self):
        if self.lesson_slug is None:
            return None
        else:
            try:
                return Lesson.objects.get(self.lesson_slug)
            except Lesson.DoesNotExist:
                return None

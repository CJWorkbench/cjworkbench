from contextlib import contextmanager
from django.db import models, transaction
from django.contrib.auth.models import User
from server.models.WfModule import WfModule
from django.urls import reverse
from server.models.Lesson import Lesson

# A Workflow is the user's "document," a series of Modules
class Workflow(models.Model):
    name = models.CharField('name',max_length=200)
    creation_date = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    public = models.BooleanField(default=False)
    example = models.BooleanField(default=False)    # if set, will be duplicated for new users
    lesson_slug = models.CharField('lesson_slug', max_length=100, null=True)

    module_library_collapsed = models.BooleanField(default=False)
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
        # savepoint=False because on sqlite, savepoints commit before start
        with transaction.atomic(savepoint=False):
            # Lock the workflow, in the database.
            # This will block until the workflow is released.
            # https://docs.djangoproject.com/en/2.0/ref/models/querysets/#select-for-update
            #
            # In sqlite select_for_update() is a no-op; but we're safe because
            # sqlite doesn't allow concurrent transactions.
            #
            # list() executes the query
            list(Workflow.objects.select_for_update().filter(id=self.id))

            yield

    def user_authorized_read(self, user):
        return user == self.owner or self.public == True

    def user_authorized_write(self, user):
        return user == self.owner

    def read_only(self, user):
        return self.user_authorized_read(user) and not self.user_authorized_write(user)

    def last_update(self):
        if not self.last_delta:
            return self.creation_date
        return self.last_delta.datetime

    # use last delta ID as (non sequential) revision number, as later deltas will always have later ids
    def revision(self):
        if not self.last_delta:
            return 0
        else:
            return self.last_delta.id

    # duplicate workflow, make it belong to specified user
    # No authorization checking here, that needs to be handled in the view
    # Loses undo history (do we want that?)
    def duplicate(self, target_user):
        new_wf_name = 'Copy of ' + self.name if not self.example else self.name  # don't prepend 'Copy of' to examples

        with self.cooperative_lock():
            new_wf = Workflow.objects.create(name=new_wf_name, owner=target_user, public=False, last_delta=None)
            for wfm in WfModule.objects.filter(workflow=self):
                wfm.duplicate(new_wf)

        return new_wf

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

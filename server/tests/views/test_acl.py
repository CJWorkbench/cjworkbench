from django.contrib.auth.models import User
from django.utils import timezone
from cjwstate.models import Workflow
from cjwstate.tests.utils import DbTestCase


class AclTest(DbTestCase):
    def _put_entry(self, workflow, user, email, data):
        if user:
            self.client.force_login(user)

        return self.client.put(
            f"/api/workflows/{workflow.id}/acl/{email}",
            data=data,
            content_type="application/json",
        )

    def _delete_entry(self, workflow, user, email):
        if user:
            self.client.force_login(user)

        return self.client.delete(f"/api/workflows/{workflow.id}/acl/{email}")

    def test_put_entry(self):
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)
        response = self._put_entry(workflow, user, "a@example.org", '{"canEdit": true}')
        self.assertEqual(response.status_code, 204)

        entry = workflow.acl.first()
        self.assertEqual(entry.email, "a@example.org")
        self.assertEqual(entry.can_edit, True)

    def test_put_entry_as_anonymous(self):
        workflow = Workflow.objects.create(
            owner=None, anonymous_owner_session_key=self.client.session.session_key
        )
        response = self._put_entry(workflow, None, "a@example.org", '{"canEdit": true}')
        self.assertEqual(response.status_code, 404)

    def test_put_entry_as_non_owner(self):
        # Even editors don't get to edit the user list
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)
        user2 = User.objects.create(
            username="other@example.org", email="other@example.org"
        )
        workflow.acl.create(email="other@example.org", can_edit=True)

        response = self._put_entry(
            workflow, user2, "a@example.org", '{"canEdit": true}'
        )
        self.assertEqual(response.status_code, 403)

    def test_put_entry_invalid_email(self):
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)
        response = self._put_entry(workflow, user, "a@example@org", '{"canEdit": true}')
        self.assertEqual(response.status_code, 400)

    def test_put_entry_owner(self):
        user = User.objects.create(email="a@example.org")
        workflow = Workflow.objects.create(owner=user)
        response = self._put_entry(workflow, user, "a@example.org", '{"canEdit": true}')
        self.assertEqual(response.status_code, 400)

    def test_put_entry_dup(self):
        # dup overwrites the existing entry
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)

        dt = timezone.datetime(2018, 10, 3, 19, 28, 1, tzinfo=timezone.utc)

        workflow.acl.create(email="a@example.org", can_edit=False, created_at=dt)
        response = self._put_entry(workflow, user, "a@example.org", '{"canEdit": true}')
        self.assertEqual(response.status_code, 204)

        # No new entry added
        self.assertEqual(len(workflow.acl.all()), 1)

        # ... but entry was updated
        entry = workflow.acl.first()
        self.assertEqual(entry.email, "a@example.org")  # not changed
        self.assertEqual(entry.can_edit, True)  # changed
        self.assertEqual(entry.created_at, dt)  # not changed

    def test_delete_entry_owner(self):
        user = User.objects.create(email="a@example.org")
        workflow = Workflow.objects.create(owner=user)
        response = self._delete_entry(workflow, user, "a@example.org")
        self.assertEqual(response.status_code, 400)

    def test_delete_entry(self):
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)

        workflow.acl.create(email="a@example.org", can_edit=False)
        workflow.acl.create(email="b@example.org", can_edit=True)

        response = self._delete_entry(workflow, user, "a@example.org")
        self.assertEqual(response.status_code, 204)

        # Entry deleted
        self.assertEqual(len(workflow.acl.all()), 1)
        self.assertEqual(len(workflow.acl.filter(email="b@example.org")), 1)

    def test_delete_entry_missing(self):
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)

        # A different user
        workflow.acl.create(email="b@example.org", can_edit=True)

        response = self._delete_entry(workflow, user, "a@example.org")
        self.assertEqual(response.status_code, 204)

        # Non-requested entry not deleted
        self.assertEqual(len(workflow.acl.all()), 1)

    def test_delete_entry_invalid_email(self):
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)
        response = self._delete_entry(workflow, user, "a@example@org")
        self.assertEqual(response.status_code, 400)

    def test_delete_entry_as_anonymous(self):
        # Anonyous workflows can't be shared: they must be duplicated first.
        workflow = Workflow.objects.create(
            owner=None, anonymous_owner_session_key=self.client.session.session_key
        )
        response = self._delete_entry(workflow, None, "a@example.org")
        self.assertEqual(response.status_code, 404)

    def test_delete_entry_as_non_owner(self):
        # Even editors don't get to edit the user list
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)
        user2 = User.objects.create(
            username="other@example.org", email="other@example.org"
        )
        workflow.acl.create(email="other@example.org", can_edit=True)

        response = self._delete_entry(workflow, user2, "a@example.org")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(workflow.acl.all()), 1)

import json
from django.contrib.auth.models import AnonymousUser, User
from django.utils import timezone
from server.models import AclEntry, User, Workflow
from server.views import acl
from server.tests.utils import DbTestCase


class AclTest(DbTestCase):
    def _get_list(self, workflow, user):
        if user:
            self.client.force_login(user)

        return self.client.get(f'/api/workflows/{workflow.id}/acl')

    def _put_entry(self, workflow, user, email, data):
        if user:
            self.client.force_login(user)

        return self.client.put(f'/api/workflows/{workflow.id}/acl/{email}',
                               data=data, content_type='application/json')

    def _delete_entry(self, workflow, user, email):
        if user:
            self.client.force_login(user)

        return self.client.delete(f'/api/workflows/{workflow.id}/acl/{email}')

    def test_get_list_empty(self):
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)
        response = self._get_list(workflow, user)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data, [])

    def test_get_list(self):
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)

        dt = timezone.datetime(2018, 10, 3, 19, 28, 1, tzinfo=timezone.utc)

        workflow.acl.create(email='a@example.org', can_edit=False,
                            created_at=dt)
        workflow.acl.create(email='b@example.org', can_edit=True,
                            created_at=dt)

        response = self._get_list(workflow, user)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data, [
            {'workflow_id': workflow.pk, 'email': 'a@example.org',
             'created_at': '2018-10-03T19:28:01Z', 'can_edit': False},
            {'workflow_id': workflow.pk, 'email': 'b@example.org',
             'created_at': '2018-10-03T19:28:01Z', 'can_edit': True},
        ])

    def test_get_list_as_unauthorized(self):
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)
        user2 = User.objects.create(username='other@example.org')
        response = self._get_list(workflow, user2)
        self.assertEqual(response.status_code, 403)

    def test_get_list_as_reader(self):
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)
        workflow.acl.create(email='other@example.org', can_edit=True)
        user2 = User.objects.create(username='other@example.org',
                                    email='other@example.org')
        response = self._get_list(workflow, user2)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([e['email'] for e in json.loads(response.content)],
                         ['other@example.org'])

    def test_get_list_anonymous(self):
        # Anonyous workflows can't be shared: they must be duplicated first.
        workflow = Workflow.objects.create(
            owner=None,
            anonymous_owner_session_key=self.client.session.session_key
        )
        response = self._get_list(workflow, None)
        self.assertEqual(response.status_code, 404)

    def test_put_entry(self):
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)
        response = self._put_entry(workflow, user, 'a@example.org',
                                   '{"can_edit": true}')
        self.assertEqual(response.status_code, 204)

        entry = workflow.acl.first()
        self.assertEqual(entry.email, 'a@example.org')
        self.assertEqual(entry.can_edit, True)

    def test_put_entry_as_anonymous(self):
        workflow = Workflow.objects.create(
            owner=None,
            anonymous_owner_session_key=self.client.session.session_key
        )
        response = self._put_entry(workflow, None, 'a@example.org',
                                   '{"can_edit": true}')
        self.assertEqual(response.status_code, 404)

    def test_put_entry_as_non_owner(self):
        # Even editors don't get to edit the user list
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)
        user2 = User.objects.create(username='other@example.org',
                                    email='other@example.org')
        workflow.acl.create(email='other@example.org', can_edit=True)

        response = self._put_entry(workflow, user2, 'a@example.org',
                                   '{"can_edit": true}')
        self.assertEqual(response.status_code, 403)

    def test_put_entry_invalid_email(self):
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)
        response = self._put_entry(workflow, user, 'a@example@org',
                                   '{"can_edit": true}')
        self.assertEqual(response.status_code, 400)

    def test_put_entry_owner(self):
        user = User.objects.create(email='a@example.org')
        workflow = Workflow.objects.create(owner=user)
        response = self._put_entry(workflow, user, 'a@example.org',
                                   '{"can_edit": true}')
        self.assertEqual(response.status_code, 400)

    def test_put_entry_dup(self):
        # dup overwrites the existing entry
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)

        dt = timezone.datetime(2018, 10, 3, 19, 28, 1, tzinfo=timezone.utc)

        workflow.acl.create(email='a@example.org', can_edit=False,
                            created_at=dt)
        response = self._put_entry(workflow, user, 'a@example.org',
                                   '{"can_edit": true}')
        self.assertEqual(response.status_code, 204)

        # No new entry added
        self.assertEqual(len(workflow.acl.all()), 1)

        # ... but entry was updated
        entry = workflow.acl.first()
        self.assertEqual(entry.email, 'a@example.org')  # not changed
        self.assertEqual(entry.can_edit, True)  # changed
        self.assertEqual(entry.created_at, dt)  # not changed

    def test_delete_entry_owner(self):
        user = User.objects.create(email='a@example.org')
        workflow = Workflow.objects.create(owner=user)
        response = self._delete_entry(workflow, user, 'a@example.org')
        self.assertEqual(response.status_code, 400)

    def test_delete_entry(self):
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)

        workflow.acl.create(email='a@example.org', can_edit=False)
        workflow.acl.create(email='b@example.org', can_edit=True)

        response = self._delete_entry(workflow, user, 'a@example.org')
        self.assertEqual(response.status_code, 204)

        # Entry deleted
        self.assertEqual(len(workflow.acl.all()), 1)
        self.assertEqual(len(workflow.acl.filter(email='b@example.org')), 1)

    def test_delete_entry_missing(self):
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)

        # A different user
        workflow.acl.create(email='b@example.org', can_edit=True)

        response = self._delete_entry(workflow, user, 'a@example.org')
        self.assertEqual(response.status_code, 204)

        # Non-requested entry not deleted
        self.assertEqual(len(workflow.acl.all()), 1)

    def test_delete_entry_invalid_email(self):
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)
        response = self._delete_entry(workflow, user, 'a@example@org')
        self.assertEqual(response.status_code, 400)

    def test_delete_entry_as_anonymous(self):
        # Anonyous workflows can't be shared: they must be duplicated first.
        workflow = Workflow.objects.create(
            owner=None,
            anonymous_owner_session_key=self.client.session.session_key
        )
        response = self._delete_entry(workflow, None, 'a@example.org')
        self.assertEqual(response.status_code, 404)

    def test_delete_entry_as_non_owner(self):
        # Even editors don't get to edit the user list
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)
        user2 = User.objects.create(username='other@example.org',
                                    email='other@example.org')
        workflow.acl.create(email='other@example.org', can_edit=True)

        response = self._delete_entry(workflow, user2, 'a@example.org')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(workflow.acl.all()), 1)

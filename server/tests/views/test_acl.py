import datetime
import json
import secrets
from http import HTTPStatus as status
from unittest.mock import patch

from django.contrib.auth.models import User

from cjworkbench.models.product import Product
from cjworkbench.models.userprofile import UserProfile
from cjwstate.models import Workflow
from cjwstate.models.fields import Role
from cjwstate.tests.utils import DbTestCase


def create_user(email: str = "user@example.com", can_create_secret_link: bool = False):
    user = User.objects.create(email=email)
    UserProfile.objects.create(user=user)

    if can_create_secret_link:
        product = Product.objects.create(
            stripe_product_id="prod_1",
            stripe_product_name="Premium",
            can_create_secret_link=True,
        )
        price = product.prices.create(
            stripe_price_id="price_1",
            stripe_amount=1,
            stripe_currency="usd",
            stripe_active=True,
        )
        user.subscriptions.create(
            price_id=price.id,
            stripe_status="active",
            created_at=datetime.datetime.now(),
            renewed_at=datetime.datetime.now(),
        )

    return user


class IndexTest(DbTestCase):
    def test_private_no_secret_to_public_no_secret(self):
        owner = create_user()
        workflow = Workflow.create_and_init(owner=owner, public=False, secret_id="")

        self.client.force_login(owner)
        response = self.client.put(
            f"/workflows/{workflow.id}/acl",
            {"public": True},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.OK)
        self.assertEqual(
            json.loads(response.content),
            {"workflow": {"public": True, "secret_id": ""}},
        )
        workflow.refresh_from_db()
        self.assertEqual(workflow.public, True)
        self.assertEqual(workflow.secret_id, "")

    def test_public_no_secret_to_private_no_secret(self):
        owner = create_user()
        workflow = Workflow.create_and_init(owner=owner, public=True, secret_id="")

        self.client.force_login(owner)
        response = self.client.put(
            f"/workflows/{workflow.id}/acl",
            {"public": False},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.OK)
        self.assertEqual(
            json.loads(response.content),
            {"workflow": {"public": False, "secret_id": ""}},
        )
        workflow.refresh_from_db()
        self.assertEqual(workflow.public, False)
        self.assertEqual(workflow.secret_id, "")

    def test_no_secret_to_secret(self):
        owner = create_user(can_create_secret_link=True)
        workflow = Workflow.create_and_init(owner=owner, public=False, secret_id="")

        self.client.force_login(owner)
        with patch.object(secrets, "choice") as c:
            c.return_value = "X"
            response = self.client.put(
                f"/workflows/{workflow.id}/acl",
                {"public": False, "has_secret": True},
                content_type="application/json",
            )

        self.assertEqual(response.status_code, status.OK)
        self.assertEqual(
            json.loads(response.content),
            {
                "workflow": {
                    "public": False,
                    "secret_id": "wXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                }
            },
        )
        workflow.refresh_from_db()
        self.assertEqual(workflow.public, False)
        self.assertEqual(workflow.secret_id, "wXXXXXXXXXXXXXXXXXXXXXXXXXXX")

    def test_no_secret_to_secret_not_allowed_with_no_subscription(self):
        owner = create_user(can_create_secret_link=False)
        workflow = Workflow.create_and_init(owner=owner, public=False, secret_id="")

        self.client.force_login(owner)
        response = self.client.put(
            f"/workflows/{workflow.id}/acl",
            {"public": False, "has_secret": True},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.FORBIDDEN)
        workflow.refresh_from_db()
        self.assertEqual(workflow.public, False)
        self.assertEqual(workflow.secret_id, "")

    def test_secret_to_no_secret(self):
        owner = create_user()
        workflow = Workflow.create_and_init(
            owner=owner, public=True, secret_id="wAAAAAAAAAAAAAAAAAAAAAAAAAA"
        )

        self.client.force_login(owner)
        response = self.client.put(
            f"/workflows/{workflow.id}/acl",
            {"public": False, "has_secret": False},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.OK)
        self.assertEqual(
            json.loads(response.content),
            {"workflow": {"public": False, "secret_id": ""}},
        )
        workflow.refresh_from_db()
        self.assertEqual(workflow.public, False)
        self.assertEqual(workflow.secret_id, "")

    def test_secret_to_public_with_secret(self):
        owner = create_user()
        workflow = Workflow.create_and_init(
            owner=owner, public=False, secret_id="wAAAAAAAAAAAAAAAAAAAAAAAAAA"
        )

        self.client.force_login(owner)
        response = self.client.put(
            f"/workflows/{workflow.id}/acl",
            {"public": True, "has_secret": True},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.OK)
        self.assertEqual(
            json.loads(response.content),
            {"workflow": {"public": True, "secret_id": "wAAAAAAAAAAAAAAAAAAAAAAAAAA"}},
        )
        workflow.refresh_from_db()
        self.assertEqual(workflow.public, True)
        self.assertEqual(workflow.secret_id, "wAAAAAAAAAAAAAAAAAAAAAAAAAA")


class EntryTest(DbTestCase):
    def _put_entry(self, workflow, user, email, data):
        if user:
            self.client.force_login(user)

        return self.client.put(
            f"/workflows/{workflow.id}/acl/{email}",
            data,
            content_type="application/json",
        )

    def _delete_entry(self, workflow, user, email):
        if user:
            self.client.force_login(user)

        return self.client.delete(f"/workflows/{workflow.id}/acl/{email}")

    def test_put_entry(self):
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)
        response = self._put_entry(
            workflow, user, "a@example.org", '{"role": "editor"}'
        )
        self.assertEqual(response.status_code, 204)

        entry = workflow.acl.first()
        self.assertEqual(entry.email, "a@example.org")
        self.assertEqual(entry.role, Role.EDITOR)

    def test_put_entry_as_anonymous(self):
        workflow = Workflow.objects.create(
            owner=None, anonymous_owner_session_key=self.client.session.session_key
        )
        response = self._put_entry(
            workflow, None, "a@example.org", '{"role": "editor"}'
        )
        self.assertEqual(response.status_code, 403)

    def test_put_entry_as_non_owner(self):
        # Even editors don't get to edit the user list
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)
        user2 = User.objects.create(
            username="other@example.org", email="other@example.org"
        )
        workflow.acl.create(email="other@example.org", role=Role.EDITOR)

        response = self._put_entry(
            workflow, user2, "a@example.org", '{"role": "editor"}'
        )
        self.assertEqual(response.status_code, 403)

    def test_put_entry_invalid_email(self):
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)
        response = self._put_entry(
            workflow, user, "a@example@org", '{"role": "editor"}'
        )
        self.assertEqual(response.status_code, 400)

    def test_put_entry_owner(self):
        user = User.objects.create(email="a@example.org")
        workflow = Workflow.objects.create(owner=user)
        response = self._put_entry(
            workflow, user, "a@example.org", '{"role": "editor"}'
        )
        self.assertEqual(response.status_code, 400)

    def test_put_entry_dup(self):
        # dup overwrites the existing entry
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)

        dt = datetime.datetime(2018, 10, 3, 19, 28, 1)

        workflow.acl.create(email="a@example.org", role=Role.VIEWER, created_at=dt)
        response = self._put_entry(
            workflow, user, "a@example.org", '{"role": "editor"}'
        )
        self.assertEqual(response.status_code, 204)

        # No new entry added
        self.assertEqual(len(workflow.acl.all()), 1)

        # ... but entry was updated
        entry = workflow.acl.first()
        self.assertEqual(entry.email, "a@example.org")  # not changed
        self.assertEqual(entry.role, Role.EDITOR)  # changed
        self.assertEqual(entry.created_at, dt)  # not changed

    def test_delete_entry_owner(self):
        user = User.objects.create(email="a@example.org")
        workflow = Workflow.objects.create(owner=user)
        response = self._delete_entry(workflow, user, "a@example.org")
        self.assertEqual(response.status_code, 400)

    def test_delete_entry(self):
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)

        workflow.acl.create(email="a@example.org", role=Role.VIEWER)
        workflow.acl.create(email="b@example.org", role=Role.EDITOR)

        response = self._delete_entry(workflow, user, "a@example.org")
        self.assertEqual(response.status_code, 204)

        # Entry deleted
        self.assertEqual(len(workflow.acl.all()), 1)
        self.assertEqual(len(workflow.acl.filter(email="b@example.org")), 1)

    def test_delete_entry_missing(self):
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)

        # A different user
        workflow.acl.create(email="b@example.org", role=Role.EDITOR)

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
        self.assertEqual(response.status_code, 403)

    def test_delete_entry_as_non_owner(self):
        # Even editors don't get to edit the user list
        user = User.objects.create()
        workflow = Workflow.objects.create(owner=user)
        user2 = User.objects.create(
            username="other@example.org", email="other@example.org"
        )
        workflow.acl.create(email="other@example.org", role=Role.EDITOR)

        response = self._delete_entry(workflow, user2, "a@example.org")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(workflow.acl.all()), 1)

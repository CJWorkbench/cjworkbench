import time

from integrationtests.helpers import accounts
from integrationtests.utils import WorkbenchBase


class TestWorkflow(WorkbenchBase):
    def _create_workflow(self):
        b = self.browser
        b.visit("/workflows")
        b.click_button("Create your first workflow", wait=True)  # wait for React render
        # Wait for page to load
        b.assert_element('input[name="name"][value="Untitled Workflow"]', wait=True)

    def _share_workflow_with(self, email, role):
        b = self.browser
        b.click_button("Share")

        with b.scope(".share-modal", wait=True):  # wait for dialog
            b.fill_in("email", "b@example.org")
            b.click_button("Grant access")

            # This fires and forgets an AJAX request. Wait for it to finish.
            time.sleep(2)

        if role != "Can view":
            b.click_button("Can view")
            b.click_button(role)
            # This fires and forgets a _second_ AJAX request. Again: wait
            # for it to finish.
            time.sleep(2)

        with b.scope(".share-modal"):
            b.click_button("Close")

    def test_403_then_log_in_as_owner(self):
        self.account_admin.create_user("alice@example.org", is_staff=False)
        b = self.browser
        accounts.login(b, "alice@example.org", "alice@example.org")
        self._create_workflow()
        url = b.get_url()

        b.clear_cookies()
        b.visit(url)

        b.assert_element("h1", text="Private workflow")
        b.click_link("Sign in", wait=True)

        b.fill_in("login", "alice@example.org")
        b.fill_in("password", "alice@example.org")
        b.click_button("Sign In")

        b.wait_for_element("main.workflow-root")
        self.assertEqual(b.get_url(), url)

    def test_403_then_log_in_as_different_user(self):
        self.account_admin.create_user("alice@example.org", is_staff=False)
        self.account_admin.create_user("bob@example.org", is_staff=False)

        b = self.browser

        accounts.login(b, "alice@example.org", "alice@example.org")
        self._create_workflow()
        url = b.get_url()

        b.clear_cookies()
        accounts.login(b, "bob@example.org", "bob@example.org")
        b.visit(url)

        b.assert_element("h1", text="Private workflow")
        b.click_button("Sign in as a different user", wait=True)

        b.fill_in("login", "alice@example.org")
        b.fill_in("password", "alice@example.org")
        b.click_button("Sign In")

        b.wait_for_element("main.workflow-root")
        self.assertEqual(b.get_url(), url)

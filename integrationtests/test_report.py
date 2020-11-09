import time
from integrationtests.utils import LoggedInIntegrationTest
from integrationtests.helpers import accounts


class TestReport(LoggedInIntegrationTest):
    def _create_workflow(self, title=None):
        b = self.browser

        b.visit("/workflows/")
        b.click_button("Create Workflow", wait=True)  # wait for React render
        # Wait for page to load
        b.assert_element('input[name="name"][value="Untitled Workflow"]', wait=True)
        if title:
            b.fill_in("name", title)

    def _build_chart(self):
        self.import_module("pastecsv")
        self.add_data_step("Paste data")
        b = self.browser
        b.fill_in("csv", "Category,Number\nA,2,\nB,3", wait=True)
        self.submit_step()

        self.import_module("columnchart")
        self.add_step("Column Chart")
        self.select_column("Column Chart", "x_column", "Category")
        self.select_column("Column Chart", "y_columns", "Number")
        self.submit_step()

    def test_report_appears(self):
        self._create_workflow(title="Example Workflow")
        self._build_chart()

        b = self.browser
        b.click_button("Report")  # switch to report
        b.assert_element(".add-block-prompt")
        url = b.text(".share-card .url .copy", wait=True)
        b.visit(url)

        b.assert_element("h1", text="Example Workflow", wait=True)
        # Let's not bother testing that Vega renders correctly: that's out of
        # the scope of these tests. Instead, test that we did indeed load
        # columnchart.html. It includes <div id="vega">.
        with b.iframe("iframe", wait=True):
            b.assert_element("#vega", wait=True)

    def test_report_share_with_collaborators(self):
        user1 = self.account_admin.create_user("a@example.org")
        user2 = self.account_admin.create_user("b@example.org")

        self._create_workflow(title="Example Workflow")
        self._build_chart()

        # Share report with user1, but not user2
        b = self.browser
        b.click_button("Report")  # switch to report
        with b.scope(".share-card"):
            b.click_button("Edit privacy", wait=True)
        with b.scope(".share-modal", wait=True):  # wait for dialog
            b.fill_in("email", user1.email)
            b.click_button("Grant access")
            # This fires and forgets an AJAX request. Wait for it to finish.
            time.sleep(2)
            b.click_button("Close")
        b.assert_element(".share-card .accessible-to", text="Only collaborators")
        url = b.text(".share-card .url .copy", wait=True)

        # user1 can view the report
        accounts.logout(b)
        accounts.login(b, user1.email, user1.password)
        b.visit(url)
        b.assert_element("h1", text="Example Workflow", wait=True)

        # user2 can't access the report (we test for its title)
        accounts.logout(b)
        accounts.login(b, user2.email, user2.password)
        b.visit(url)
        b.assert_no_element("h1", text="Example Workflow", wait=True)

    def test_report_share_public_iframe(self):
        user1 = self.account_admin.create_user("a@example.org")

        self._create_workflow(title="Example Workflow")
        self._build_chart()

        # Share report with public
        b = self.browser
        b.click_button("Report")  # switch to report
        with b.scope(".share-card"):
            b.click_button("Edit privacy", wait=True)
        with b.scope(".share-modal", wait=True):  # wait for dialog
            b.check("Anyone can view")
            # This fires and forgets an AJAX request. Wait for it to finish.
            time.sleep(2)
            b.click_button("Close")
        b.assert_element(".share-card .accessible-to", text="Anyone can view")
        iframe_url = b.text(".share-card .url .copy", wait=True)

        # user1 can view the report
        accounts.logout(b)
        accounts.login(b, user1.email, user1.password)
        b.visit(iframe_url)
        b.assert_element("h1", text="Example Workflow", wait=True)

        # anonymous user can view the report
        accounts.logout(b)
        b.visit(iframe_url)
        b.assert_element("h1", text="Example Workflow", wait=True)

    def test_report_read_only(self):
        user1 = self.account_admin.create_user("a@example.org")

        self._create_workflow(title="Example Workflow")
        self._build_chart()

        # Share report with public
        b = self.browser
        b.click_button("Report")  # switch to report
        with b.scope(".share-card"):
            b.click_button("Edit privacy", wait=True)
        with b.scope(".share-modal", wait=True):  # wait for dialog
            b.check("Anyone can view")
            # This fires and forgets an AJAX request. Wait for it to finish.
            time.sleep(2)
            b.click_button("Close")
        b.assert_element(".share-card .accessible-to", text="Anyone can view")
        url = b.get_url()

        # anonymous user can view the report
        accounts.logout(b)
        b.visit(url)
        b.assert_element("h1", text="Example Workflow", wait=True)
        b.assert_no_element(".add-block-prompt")

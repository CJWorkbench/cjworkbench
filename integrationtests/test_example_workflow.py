from integrationtests.helpers import accounts
from integrationtests.utils import WorkbenchBase


class TestExampleWorkflow(WorkbenchBase):
    def setUp(self):
        super().setUp()

        self.admin = self.account_admin.create_user(
            "admin@example.org", is_staff=True, is_superuser=True
        )

        self.user1 = self.account_admin.create_user("user1@example.org")

    def _create_example_workflow(self):
        b = self.browser

        accounts.login(b, self.admin.email, self.admin.email)

        b.visit("/workflows/")
        b.click_button("Create your first workflow")
        # Wait for page to load
        b.assert_element('input[name="name"][value="Untitled Workflow"]', wait=True)

        b.fill_in("name", "Example Workflow")

        self.import_module("pastecsv")
        self.add_data_step("Paste data")
        b.fill_in("csv", "foo,bar,baz\n1,2,\n2,3,\n3,4,", wait=True)
        self.submit_step()

        self.import_module("nulldropper")
        self.add_step("Drop empty columns")

        # Wait for _any_ output to load
        b.assert_element(".column-key", text="bar", wait=True)
        # Wait for the _final_ output to load -- which means the "baz" column
        # will not be there.
        b.assert_no_element(".column-key", text="baz", wait=True)
        # Wait for the _data_ to load -- not just the headers
        b.assert_element(".react-grid-Cell", text="2", wait=True)

        url = b.get_url()

        # Make it an example
        b.visit("/adminserver/workflow/")
        b.click_link("Example Workflow", wait=True)
        b.check("Public")
        b.check("Example")
        b.check("In all users workflow lists")
        b.click_button("Save")
        b.assert_element("li.success")

        b.clear_cookies()

        return url

    def test_other_user_can_edit(self):
        self._create_example_workflow()

        b = self.browser

        accounts.login(b, self.user1.email, self.user1.email)

        # Demo should appear in Workflow list
        b.visit("/workflows/examples")
        # Wait for page to load
        b.assert_element("a", text="Example Workflow", wait=True)
        b.click_link("Example Workflow")

        # Wait for page to load
        b.assert_element(".module-name", text="Drop empty columns", wait=True)
        # Prove it's editable by editing it!
        self.delete_step(1)
        b.assert_element(".column-key", text="baz", wait=True)

    def test_anonymous_can_edit(self):
        url = self._create_example_workflow()

        b = self.browser

        b.visit(url)

        # Wait for page to load
        b.assert_element(".module-name", text="Drop empty columns", wait=True)
        # Prove it's editable by editing it!
        self.delete_step(1)
        b.assert_element(".column-key", text="baz", wait=True)

    def test_everybody_gets_a_version(self):
        b = self.browser
        url = self._create_example_workflow()

        def wait_for_page_load_then_edit():
            # wait for page load _and_ assert the edit has not happened
            b.assert_element(".module-name", text="Drop empty columns", wait=True)
            self.delete_step(1)
            # Wait for output to update
            b.assert_element(".column-key", text="baz", wait=True)

        # Anonymous
        b.visit(url)
        wait_for_page_load_then_edit()
        b.clear_cookies()

        # User1
        accounts.login(b, self.user1.email, self.user1.email)
        b.visit(url)
        wait_for_page_load_then_edit()
        b.clear_cookies()

        # Owner
        accounts.login(b, self.admin.email, self.admin.email)
        b.visit(url)
        wait_for_page_load_then_edit()
        b.clear_cookies()

        # Now a new anonymous user will see the edits
        b.visit(url)
        b.assert_element(".module-name", text="Paste data", wait=True)
        b.assert_no_element(".module-name", text="Drop empty columns")

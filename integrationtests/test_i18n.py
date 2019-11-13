from integrationtests.utils import WorkbenchBase
from integrationtests.helpers import accounts


class TestExampleWorkflow(WorkbenchBase):
    def setUp(self):
        super().setUp()
        self.user = self.account_admin.create_user(
            "user@example.org", first_name="Jane", last_name="Doe"
        )

    def test_js_english_interpolation(self):
        # "by {owner}" is a message that uses JS interpolation
        # It's in WorkflowNavBar.js
        b = self.browser

        accounts.login(b, self.user.email, self.user.email)
        b.visit("/workflows/")
        b.click_button("Create Workflow")
        # Wait for page to load
        b.assert_element('input[name="name"][value="Untitled Workflow"]', wait=True)
        b.assert_element(".attribution .metadata", text="by Jane Doe")

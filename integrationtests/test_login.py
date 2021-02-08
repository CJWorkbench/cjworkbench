from integrationtests.utils import WorkbenchBase
from integrationtests.helpers import accounts


class TestLogin(WorkbenchBase):
    def setUp(self):
        super().setUp()

        self.user = self.account_admin.create_user("user@example.org")

    def test_login(self):
        # TODO make this test suite non-redundant. We already test this in
        # LoggedInIntegrationTest.
        accounts.login(self.browser, self.user.email, self.user.password)
        self.browser.assert_element("button", text="Create your first workflow")

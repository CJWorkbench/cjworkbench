from integrationtests.utils import WorkbenchBase
from integrationtests.helpers import accounts


class TestLogin(WorkbenchBase):
    def setUp(self):
        super().setUp()

        self.user = self.account_admin.create_user('user@example.org')
        self.user_email = self.account_admin.verify_user_email(self.user)

    def tearDown(self):
        self.account_admin.destroy_user_email(self.user_email)
        self.account_admin.destroy_user(self.user)

        super().tearDown()

    def test_login(self):
        # TODO make this test suite non-redundant. We already test this in
        # LoggedInIntegrationTest.
        accounts.login(self.browser, self.user.email, self.user.password)
        self.browser.assert_element('button', text='Create Workflow')

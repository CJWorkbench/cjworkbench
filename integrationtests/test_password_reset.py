from integrationtests.utils import WorkbenchBase, find_url_in_email
from integrationtests.helpers import accounts


class TestPasswordReset(WorkbenchBase):
    def setUp(self):
        super().setUp()

        self.user = self.account_admin.create_user("user@example.org")

    def _begin_password_reset(self, email):
        b = self.browser
        b.visit("/")
        b.click_link("Forgot Password?")
        b.fill_in("email", email)
        b.click_button("Send me instructions")

    def _try_log_in_to_current_page(self, email, password):
        b = self.browser
        b.fill_in("login", email)
        b.fill_in("password", password)
        b.click_button("Sign In")

    def _begin_password_reset_and_follow_email_to_form(self, email):
        # Asserts that the email is indeed one that can be reset
        self._begin_password_reset(email)

        self.browser.assert_element("h1", text="Instructions sent!")

        message = self.account_admin.latest_sent_email
        self.assertIsNotNone(message)
        self.assertEqual(email, message["To"])
        url = find_url_in_email(message)
        self.assertIsNotNone(url)

        self.browser.visit(url)

    def _try_reset_password(self, password1, password2):
        b = self.browser
        b.assert_element("legend", text="Change Password")
        b.fill_in("password1", password1)
        b.fill_in("password2", password2)
        b.click_button("change password")

    def test_password_reset(self):
        b = self.browser

        self._begin_password_reset_and_follow_email_to_form("user@example.org")

        self._try_reset_password("9owyidIaj|", "9owyidIaj|")

        b.assert_element("legend", text="Your new password is set!")
        b.click_link("Back to login")

        self._try_log_in_to_current_page("user@example.org", "9owyidIaj|")
        b.assert_element("button", "Create Workflow")

    def test_password_reset_wrong_email(self):
        b = self.browser

        self._begin_password_reset("nonexistent-user@example.org")
        self.browser.assert_element(
            "ul.errorlist>li", text="not assigned to any user account"
        )

    def test_try_reset_to_invalid_passwords(self):
        # https://www.pivotaltracker.com/story/show/158275603
        b = self.browser

        self._begin_password_reset_and_follow_email_to_form("user@example.org")

        self._try_reset_password("9owyidIaj|", "9owyidIaj|1")
        b.assert_element(
            "ul.errorlist", text="You must type the same password each time"
        )

        self._try_reset_password("user@example.org", "user@example.org")
        b.assert_element("ul.errorlist", text="too similar to the email address")

        self._try_reset_password("Fo0!", "Fo0!")
        b.assert_element("ul.errorlist", text="too short")

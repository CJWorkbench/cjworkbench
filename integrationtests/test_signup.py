from integrationtests.utils import WorkbenchBase, find_url_in_email
from integrationtests.test_i18n import LocaleSwitcherIntegrationTest


class TestSignup(LocaleSwitcherIntegrationTest):
    def test_signup(self):
        b = self.browser
        b.visit(self.live_server_url + "/account/signup/")

        # self.assertTrue(b.is_element_present_by_text('Use Facebook account'))
        # self.assertTrue(b.is_element_present_by_text('Use Google account'))

        b.fill_in("email", "user@example.org")
        b.fill_in("first_name", "Jane")
        b.fill_in("last_name", "Doe")
        b.fill_in("password1", "?P455W0rd!")
        b.fill_in("password2", "?P455W0rd!")
        b.click_button("Register")

        b.assert_element("h1", text="Verify Your E-mail Address", wait=True)

        # Test the email is right
        email = self.account_admin.latest_sent_email
        self.assertIsNotNone(email)
        self.assertEqual("user@example.org", email["To"])
        url = find_url_in_email(email)
        self.assertIsNotNone(url)

        # Follow the link
        b.visit(url)
        b.click_button("Confirm", wait=True)

        # Now log in with our new account
        # TODO _why_? The user already logged in
        b.fill_in("login", "user@example.org", wait=True)
        b.fill_in("password", "?P455W0rd!")
        b.click_button("Sign In")
        b.wait_for_element("a", text="MY WORKFLOWS", wait=True)

    def test_signup_el(self):
        b = self.browser
        b.visit(self.live_server_url + "/account/signup/")
        self.switch_locale_django("el")

        # self.assertTrue(b.is_element_present_by_text('Use Facebook account'))
        # self.assertTrue(b.is_element_present_by_text('Use Google account'))

        b.fill_in("email", "user-el@example.org")
        b.fill_in("first_name", "Jane")
        b.fill_in("last_name", "Doe")
        b.fill_in("password1", "?P455W0rd!")
        b.fill_in("password2", "?P455W0rd!")
        b.click_button("Εγγραφή")

        b.assert_element(
            "h1", text="Επιβεβαιώστε τη διεύθυνση του ηλ. ταχυδρομείου σας", wait=True
        )

        # Test the email is right
        email = self.account_admin.latest_sent_email
        self.assertIsNotNone(email)
        self.assertEqual("user-el@example.org", email["To"])
        url = find_url_in_email(email)
        self.assertIsNotNone(url)

        # Follow the link
        b.visit(url)
        b.click_button("Επιβεβαίωση", wait=True)

        # Now log in with our new account
        # TODO _why_? The user already logged in
        b.fill_in("login", "user-el@example.org", wait=True)
        b.fill_in("password", "?P455W0rd!")
        b.click_button("Σύνδεση")
        b.wait_for_element("a", text="ΟΙ ΡΟΈΣ ΕΡΓΑΣΊΑΣ ΜΟΥ", wait=True)

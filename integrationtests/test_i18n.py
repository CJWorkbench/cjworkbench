from integrationtests.utils import WorkbenchBase, find_url_in_email
from integrationtests.browser import Browser


def login(browser: Browser, email: str, password: str) -> None:
    """Log in through `/account/login` as the given user.
    The login page must be in `locale_id`, while the workflows page must be in `after_login_locale_id`
    """
    browser.visit("/account/login")
    browser.fill_in("login", email)
    browser.fill_in("password", password)
    browser.click_whatever('.account_form.login button[type="submit"]')
    browser.wait_for_element(".create-workflow")


def logout(browser: Browser) -> None:
    """Log out through `/account/logout` as the given user.
    
    The logout page must be in `locale_id`
    """
    browser.visit("/account/logout")
    browser.click_whatever('.account_form button[type="submit"]')
    browser.wait_for_element(".account_form.login")


def switch_locale_django(browser: Browser, to_locale_name: str):
    browser.click_whatever("a#locale-switcher-dropdown", wait=True)
    browser.click_button(to_locale_name, wait=True)

    # check that the language has indeed changed
    browser.wait_for_element("a#locale-switcher-dropdown", text=to_locale_name)


def switch_locale_react(browser: Browser, to_locale_name: str):
    browser.click_whatever(".navbar .dropdown button", wait=True)
    browser.click_whatever(".locale-switcher-show", wait=True)
    browser.click_button(to_locale_name, wait=True)

    # check that the language has indeed changed
    browser.click_whatever(".navbar .dropdown button", wait=True)
    browser.click_whatever(".locale-switcher-show", wait=True)
    browser.wait_for_element(
        ".modal.locale-switcher form button[disabled]", text=to_locale_name
    )
    browser.click_whatever(".modal.locale-switcher .modal-footer .close-button")


class TestI18n(WorkbenchBase):
    def setUp(self):
        super().setUp()
        self.user = self.account_admin.create_user(
            "user@example.org", first_name="Jane", last_name="Doe"
        )

    def test_js_english_interpolation(self):
        # "by {owner}" is a message that uses JS interpolation
        # It's in WorkflowNavBar.js
        b = self.browser

        login(b, self.user.email, self.user.email)
        b.visit("/workflows/")
        b.click_button("Create Workflow")
        # Wait for page to load
        b.assert_element('input[name="name"][value="Untitled Workflow"]', wait=True)
        b.assert_element(".attribution .metadata", text="by Jane Doe")

    def test_language_switch_in_django_templates_not_logged_in(self):
        # You can change from "en" to "el" and back and the UI will be translated
        b = self.browser
        # Start in login page with en
        b.visit("/")
        b.assert_element('input[name="password"][placeholder="Password"]', wait=True)
        b.assert_element('button[type="submit"]', text="Sign In")
        # Change locale to el
        switch_locale_django(b, "Ελληνικά")
        b.assert_element('input[name="password"][placeholder="Συνθηματικό"]', wait=True)
        b.assert_element('button[type="submit"]', text="Σύνδεση")
        # Move to another page and confirm it's in el too
        b.click_link("Εγγραφή")
        b.assert_element('input[name="first_name"][placeholder="Όνομα"]', wait=True)
        b.assert_element('button[type="submit"]', text="Εγγραφή")
        # Change locale to en again
        switch_locale_django(b, "English")
        b.assert_element(
            'input[name="first_name"][placeholder="First name"]', wait=True
        )
        b.assert_element('button[type="submit"]', text="Register")

    def test_language_switch_in_react(self):
        # You can change from "en" to "el" and back and the UI will be translated
        b = self.browser

        login(b, self.user.email, self.user.email)
        b.visit("/workflows/")
        # Start in workflows page with en
        b.assert_element(
            'form.create-workflow button[type="submit"]',
            text="Create Workflow",
            wait=True,
        )
        # Change locale to el
        switch_locale_react(b, "Ελληνικά")
        b.assert_element(
            'form.create-workflow button[type="submit"]',
            text="Δημιουργία ροής εργασιών",
            wait=True,
        )
        # Move to another page and confirm it's in el too
        b.click_link("ΕΚΠΑΙΔΕΥΣΗ")
        b.assert_element("a", text="ΜΑΘΗΜΑΤΑ", wait=True)
        # Change locale to en again
        switch_locale_react(b, "English")
        b.assert_element("a", text="TUTORIALS", wait=True)

    def test_signup_el(self):
        b = self.browser
        b.visit(self.live_server_url + "/account/signup/")
        switch_locale_django(b, "Ελληνικά")

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
        b.wait_for_element("a", text="ΟΙ ΡΟΈΣ ΕΡΓΑΣΙΏΝ ΜΟΥ")

    def test_remember_signup_locale(self):
        b = self.browser
        b.visit(self.live_server_url + "/account/signup/")
        switch_locale_django(b, "Ελληνικά")

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

        # Change locale to English and browse
        switch_locale_django(b, "English")
        b.click_link("Sign up", wait=True)
        b.assert_element(
            'input[name="first_name"][placeholder="First name"]', wait=True
        )
        b.assert_element('button[type="submit"]', text="Register")
        b.click_link("Sign in")

        # Now log in with our new account
        # TODO _why_? The user already logged in
        b.fill_in("login", "user-el@example.org", wait=True)
        b.fill_in("password", "?P455W0rd!")
        b.click_button("Sign In")
        b.wait_for_element("a", text="ΟΙ ΡΟΈΣ ΕΡΓΑΣΙΏΝ ΜΟΥ")

        # After logout, page must still be in Greek.
        logout(b)
        b.assert_element('input[name="password"][placeholder="Συνθηματικό"]', wait=True)
        b.assert_element('button[type="submit"]', text="Σύνδεση")

    def test_remember_locale_on_login(self):
        # When a user logs out, their locale continues to be used.
        # When a user logs in, the locale they used the last time they were logged in is used.
        b = self.browser

        # Login (in English)
        login(b, self.user.email, self.user.email)
        b.visit("/workflows/")

        b.assert_element(
            'form.create-workflow button[type="submit"]',
            text="Create Workflow",
            wait=True,
        )

        # Switch to Greek and then logout. After logout, page must still be in Greek.
        switch_locale_react(b, "Ελληνικά")
        logout(b)
        b.assert_element('input[name="password"][placeholder="Συνθηματικό"]', wait=True)
        b.assert_element('button[type="submit"]', text="Σύνδεση")

        # Switch to English and then login. After login, page must be in Greek.
        switch_locale_django(b, "English")
        login(b, self.user.email, self.user.email)
        b.assert_element(
            'form.create-workflow button[type="submit"]',
            text="Δημιουργία ροής εργασιών",
            wait=True,
        )

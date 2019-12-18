from integrationtests.utils import WorkbenchBase
from integrationtests.helpers import accounts


_locale_names = {"en": "English", "el": "Ελληνικά"}


class LocaleSwitcherIntegrationTest(WorkbenchBase):
    def switch_locale_django(self, to_locale_id: str):
        b = self.browser

        old_locale_name = b.text("a#locale-switcher-dropdown", wait=True)
        b.click_link(old_locale_name)
        b.click_button(_locale_names[to_locale_id], wait=True)
        b.wait_for_element(
            "a#locale-switcher-dropdown", text=_locale_names[to_locale_id], wait=True
        )

    def switch_locale_react(self, from_locale_id, to_locale_id: str):
        b = self.browser
        hamburger_menu_title = {"en": "menu", "el": "μενού"}
        language_menu_label = {"en": "Languages", "el": "Languages"}
        create_workflow_text = {
            "en": "Create Workflow",
            "el": "Δημιουργία ροής εργασιών",
        }

        b.click_button(hamburger_menu_title[from_locale_id], wait=True)
        b.click_button(language_menu_label[from_locale_id], wait=True)
        b.click_button(_locale_names[to_locale_id], wait=True)
        b.assert_element(
            'form.create-workflow button[type="submit"]',
            text=create_workflow_text[to_locale_id],
            wait=True,
        )


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


class TestLocaleSwitch(LocaleSwitcherIntegrationTest):
    def setUp(self):
        super().setUp()
        self.user = self.account_admin.create_user(
            "user@example.org", first_name="Jane", last_name="Doe"
        )

    def test_language_switch_in_django_templates(self):
        # You can change from "en" to "el" and back and the UI will be translated
        b = self.browser
        b.visit("/")
        b.assert_element('input[name="password"][placeholder="Password"]', wait=True)
        b.assert_element('button[type="submit"]', text="Sign In")
        self.switch_locale_django("el")
        b.assert_element('input[name="password"][placeholder="Συνθηματικό"]', wait=True)
        b.assert_element('button[type="submit"]', text="Σύνδεση")
        self.switch_locale_django("en")
        b.assert_element('input[name="password"][placeholder="Password"]', wait=True)
        b.assert_element('button[type="submit"]', text="Sign In")

    def test_language_switch_in_react(self):
        # You can change from "en" to "el" and back and the UI will be translated
        b = self.browser

        accounts.login(b, self.user.email, self.user.email)
        b.visit("/workflows/")

        b.assert_element(
            'form.create-workflow button[type="submit"]',
            text="Create Workflow",
            wait=True,
        )
        self.switch_locale_react("en", "el")
        b.assert_element(
            'form.create-workflow button[type="submit"]',
            text="Δημιουργία ροής εργασιών",
            wait=True,
        )
        self.switch_locale_react("el", "en")
        b.assert_element(
            'form.create-workflow button[type="submit"]',
            text="Create Workflow",
            wait=True,
        )


class TestLocaleOnLogin(LocaleSwitcherIntegrationTest):
    def setUp(self):
        super().setUp()
        self.user = self.account_admin.create_user(
            "user@example.org", first_name="Jane", last_name="Doe"
        )

    def test_remember_locale_on_login(self):
        # When a user logs out, their locale continues to be used
        # When a user logs in, their previous locale is used.
        b = self.browser

        # Login (in English)
        accounts.login(b, self.user.email, self.user.email)
        b.visit("/workflows/")

        b.assert_element(
            'form.create-workflow button[type="submit"]',
            text="Create Workflow",
            wait=True,
        )

        # Switch to Greek and then logout. Page must still be in Greek
        self.switch_locale_react("en", "el")
        accounts.logout(b, "el")
        #
        b.assert_element('input[name="password"][placeholder="Συνθηματικό"]', wait=True)
        b.assert_element('button[type="submit"]', text="Σύνδεση")

        # Switch to English and then login. After login, page must be in Greek
        self.switch_locale_django("en")
        accounts.login(b, self.user.email, self.user.email, "en", "el")
        b.assert_element(
            'form.create-workflow button[type="submit"]',
            text="Δημιουργία ροής εργασιών",
            wait=True,
        )

# Utilities for integration tests

import subprocess
import unittest
import email.message
from typing import Optional
import re

from integrationtests.browser import Browser
from integrationtests.helpers import accounts
from integrationtests.helpers.modules import import_workbench_module


_url_regex = re.compile('https?://[^\\s]+')

def find_url_in_email(message: email.message.Message) -> Optional[str]:
    """Return the first URL in the given message's payload, or None."""
    body = message.get_payload()
    match = _url_regex.search(body)

    if not match: return None
    return match.group(0)


def _find_server_url():
    """Get URL using `docker port`"""
    process = subprocess.run([
        'docker',
        'port',
        'cjworkbench_integrationtest_django',
        '8000/tcp'
    ], stdout=subprocess.PIPE)
    port_str = process.stdout.decode('ascii').split(':')[1].strip()
    return f"http://localhost:{port_str}"


class WorkbenchBase(unittest.TestCase):
    serve_static = True
    account_admin = accounts.AccountAdmin()
    live_server_url = _find_server_url()

    def setUp(self):
        super().setUp()

        self.account_admin.clear_data_from_previous_tests()

        #self.current_site = Site.objects.get_current()
        #self.SocialApp1 = self.current_site.socialapp_set.create(
        #    provider="facebook",
        #    name="Facebook",
        #    client_id="1234567890",
        #    secret="0987654321",
        #)
        #self.SocialApp2 = self.current_site.socialapp_set.create(
        #    provider="google",
        #    name="Google",
        #    client_id="1234567890",
        #    secret="0987654321",
        #)

        self.browser = Browser(base_url=self.live_server_url)


    def tearDown(self):
        self.browser.quit()


    def create_browser(self):
        return Browser(base_url=self.live_server_url)


    def import_module(self, slug: str) -> None:
        import_workbench_module(self.browser, slug)


    def add_wf_module(self, name: str, position=None) -> None:
        """Adds module with name 'name' to the workflow.

        Keyword arguments:
        position -- if set, add after the 'position'th existing module.
        """
        b = self.browser

        if position is None:
            with b.scope('.in-between-modules:last-child'):
                b.click_button('Add Module')
        else:
            i = position * 2 + 1
            with b.scope(f'.in-between-modules:nth-child({i})'):
                b.click_button('Add Module')

        # Search. That way, we won't need to worry about overflow:auto
        b.fill_in('moduleQ', name)

        b.click_whatever('li.module-search-result', text=name)

        b.assert_element(f'.wf-module[data-module-name="{name}"]', wait=True)


    def delete_wf_module(self, position: int) -> None:
        """Deletes module at index `position` from the workflow.

        The first module has `position == 0`.
        """
        b = self.browser

        with b.scope(f'.wf-module:nth-child({position * 2 + 2})'):
            b.click_button('more')
            b.click_button('Delete')


# Derive from this to perform all tests logged in
class LoggedInIntegrationTest(WorkbenchBase):
    def setUp(self):
        super().setUp()

        self.user = self.account_admin.create_user('user@example.org')
        self.user_email = self.account_admin.verify_user_email(self.user)

        accounts.login(self.browser, self.user.email, self.user.email)


    def tearDown(self):
        self.account_admin.destroy_user_email(self.user_email)
        self.account_admin.destroy_user(self.user)
        self.account_admin.destroy_modules()

        super().tearDown()

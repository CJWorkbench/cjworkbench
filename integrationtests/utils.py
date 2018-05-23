# Utilities for integration tests

import subprocess
import unittest

from integrationtests.browser import Browser
from integrationtests.helpers import accounts


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

        super().tearDown()

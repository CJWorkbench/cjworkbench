# Utilities for integration tests

from channels.testing import ChannelsLiveServerTestCase
from django.contrib.sites.models import Site
from server.initmodules import init_modules


from integrationtests.browser import Browser
from integrationtests.helpers import accounts

class WorkbenchBase(ChannelsLiveServerTestCase):
    serve_static = True

    def setUp(self):
        super().setUp()

        self.current_site = Site.objects.get_current()
        self.SocialApp1 = self.current_site.socialapp_set.create(
            provider="facebook",
            name="Facebook",
            client_id="1234567890",
            secret="0987654321",
        )
        self.SocialApp2 = self.current_site.socialapp_set.create(
            provider="google",
            name="Google",
            client_id="1234567890",
            secret="0987654321",
        )

        init_modules() # the server should run with a least core modules loaded

        self.browser = Browser(base_url=self.live_server_url)
        self.account_admin = accounts.AccountAdmin()

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

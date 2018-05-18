# Utilities for integration tests

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from splinter import Browser
from server.models import User
from server.initmodules import init_modules
from allauth.account.models import EmailAddress
from django.contrib.sites.models import Site


class WorkbenchBase(StaticLiveServerTestCase):
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

        self.browser = Browser()

    def tearDown(self):
        self.browser.quit()

# Derive from this to perform all tests logged in
class LoggedInIntegrationTest(WorkbenchBase):
    def setUp(self):
        super().setUp()

        self.password = 'password'
        self.user = User.objects.create_user(username='username', email='user@users.com', password=self.password)
        # django-allauth uses a seperate model to keep track of verified emails. Without this, we can't log in.
        self.email = EmailAddress.objects.create(user=self.user, email='user@users.com', primary=True, verified=True)

        b = self.browser
        b.visit(self.live_server_url + '/account/login')
        b.fill('login', self.user.email)
        b.fill('password', self.password)
        b.find_by_tag('button').click()

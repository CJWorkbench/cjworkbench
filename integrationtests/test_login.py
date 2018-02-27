from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth.models import User
from allauth.account.models import EmailAddress
from splinter import Browser
from django.contrib.sites.models import Site
import time

class TestLogin(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.current_site = Site.objects.get_current()
        cls.SocialApp1 = cls.current_site.socialapp_set.create(
            provider="facebook",
            name="Facebook",
            client_id="1234567890",
            secret="0987654321",
        )
        cls.SocialApp2 = cls.current_site.socialapp_set.create(
            provider="google",
            name="Google",
            client_id="1234567890",
            secret="0987654321",
        )

        cls.password = 'password' # cannot be retrieved from User object, save it here
        cls.user = User.objects.create_user(username='username', email='user@users.com', password=cls.password)
        cls.email = EmailAddress.objects.create(user=cls.user, email='user@users.com', primary=True, verified=True)

        cls.browser = Browser()

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super().tearDownClass()

    def test_login(self):
        b = self.browser
        b.visit(self.live_server_url + '/account/login')

        social_buttons = b.find_by_css('.socialLoginButton')
        self.assertEqual(len(social_buttons), 2)

        b.fill('login', self.user.email)
        b.fill('password', self.password)
        b.find_by_tag('button').click()
        time.sleep(2)
        # if we logged in sucessfully, we should be at an empty Workflows screen
        self.assertTrue(b.url.endswith('/workflows/'))
        self.assertTrue(b.find_by_css('.new-workflow-button'))

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth.models import User
from splinter import Browser

class TestLogin(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.password = 'password' # cannot be retrieved from User object, save it here
        cls.user = User.objects.create_user(username='username', email='user@users.com', password=cls.password)
        cls.browser = Browser()

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super().tearDownClass()

    def test_login(self):
        b = self.browser
        b.visit(self.live_server_url + '/account/login')
        b.fill('email', self.user.email)
        b.fill('password', self.password)

        b.find_by_tag('button').click()

        # if we logged in sucessfully, we should be at an empty Workflows screen
        self.assertTrue(b.url.endswith('/workflows/'))
        self.assertTrue(b.find_by_css('.new-workflow-button'))

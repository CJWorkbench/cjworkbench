# Utilities for integration tests

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth.models import User
from splinter import Browser
from server.initmodules import init_modules

# Derive from this to perform all tests logged in
class LoggedInIntegrationTest(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        init_modules() # the server should run with a least core modules loaded

        cls.password = 'password'
        cls.user = User.objects.create_user(username='username', email='user@users.com', password=cls.password)

        b = Browser()
        b.visit(cls.live_server_url + '/account/login')
        b.fill('email', cls.user.email)
        b.fill('password', cls.password)
        b.find_by_tag('button').click()

        cls.browser = b

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super().tearDownClass()

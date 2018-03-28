from django.contrib.auth.models import User
from allauth.account.models import EmailAddress
from splinter import Browser
from integrationtests.utils import WorkbenchBase

import time


class TestLogin(WorkbenchBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

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
        self.assertTrue(b.is_element_present_by_text('Use Facebook account'))
        self.assertTrue(b.is_element_present_by_text('Use Google account'))
        b.fill('login', self.user.email)
        b.fill('password', self.password)
        b.find_by_tag('button').click()
        time.sleep(2)
        # if we logged in sucessfully, we should be at an empty Workflows screen
        self.assertTrue(b.url.endswith('/workflows/'))
        self.assertTrue(b.find_by_css('.new-workflow-button'))

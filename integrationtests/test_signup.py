from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from splinter import Browser
from django.contrib.sites.models import Site
from django.core import mail
import time
import re


class TestSignup(StaticLiveServerTestCase):
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

        cls.browser = Browser()

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super().tearDownClass()

    def test_signup(self):
        url_regex = re.compile('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

        b = self.browser
        # This will break when signup is open to the public
        b.visit(self.live_server_url + '/xyzzy/signup/')
        b.fill('email', 'user@user.org')
        b.fill('first_name', 'Jane')
        b.fill('last_name', 'Doe')
        b.fill('password1', '?P455W0rd!') # Should we actually allow someone to use this password?
        b.fill('password2', '?P455W0rd!')
        b.find_by_tag('button').click()
        time.sleep(2)

        # if we signed up successfully, we should be at the 'verify your email' screen
        self.assertTrue(b.url.endswith('/confirm-email/'))
        self.assertEqual(len(mail.outbox), 1)
        email_text = mail.outbox[0].message().get_payload()
        url = url_regex.search(email_text)
        self.assertTrue(url[0])
        b.visit(url[0])
        b.find_by_tag('button').click()
        self.assertTrue(b.url.endswith('/login/'))

        # Now log in with our new account
        b.fill('login', 'user@user.org')
        b.fill('password', '?P455W0rd!')
        b.find_by_tag('button').click()
        self.assertTrue(b.url.endswith('/workflows/'))
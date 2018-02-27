# Utilities for integration tests

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth.models import User
from splinter import Browser
from server.initmodules import init_modules
from server.tests.utils import *
from server.models import ModuleVersion
from allauth.account.models import EmailAddress
from django.contrib.sites.models import Site

# Derive from this to perform all tests logged in
class LoggedInIntegrationTest(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        init_modules() # the server should run with a least core modules loaded

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

        cls.password = 'password'
        cls.user = User.objects.create_user(username='username', email='user@users.com', password=cls.password)
        # django-allauth uses a seperate model to keep track of verified emails. Without this, we can't log in.
        cls.email = EmailAddress.objects.create(user=cls.user, email='user@users.com', primary=True, verified=True)


        b = Browser()
        b.visit(cls.live_server_url + '/account/login')
        b.fill('login', cls.user.email)
        b.fill('password', cls.password)
        b.find_by_tag('button').click()

        cls.browser = b

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super().tearDownClass()


# Integration test starting from a simple workflow with dummy data
class DummyWorkflowIntegrationTest(StaticLiveServerTestCase):

    @classmethod
    def create_test_workflow(cls):
        cls.wf = add_new_workflow("Integration Test Workflow")
        csvspec = ModuleVersion.objects.get(module__id_name='pastecsv')
        cls.wfm = add_new_wf_module(cls.wf, csvspec)
        csv_pval = get_param_by_id_name('csv')
        csv_pval.set_value(mock_csv_text2)
        csv_pval.save()

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

        init_modules() # the server should run with a least core modules loaded

        cls.password = 'password'
        cls.user = User.objects.create_user(username='username', email='user@users.com', password=cls.password)
        # django-allauth uses a seperate model to keep track of verified emails. Without this, we can't log in.
        cls.email = EmailAddress.objects.create(user=cls.user, email='user@users.com', primary=True, verified=True)

        cls.create_test_workflow()

        b = Browser()
        b.visit(cls.live_server_url + '/account/login?next=%2fworkflows%2f' + str(cls.wf.id) + '%2f')
        b.fill('login', cls.user.email)
        b.fill('password', cls.password)
        b.find_by_tag('button').click()

        cls.browser = b

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super().tearDownClass()



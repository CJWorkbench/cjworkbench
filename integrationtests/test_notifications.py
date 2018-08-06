# coding=utf-8
from selenium.webdriver.support.wait import WebDriverWait
from integrationtests.utils import LoggedInIntegrationTest


class TestNotifications(LoggedInIntegrationTest):
    def setUp(self):
        super().setUp()

        b = self.browser
        b.click_button('Create Workflow')

        # wait for page load
        b.assert_element('input[name="name"][value="New Workflow"]', wait=True)

    def test_notifications(self):
        b = self.browser

        self.import_module('random20floats')
        self.import_module('filter')

        self.add_wf_module('Random 20 Floats')
        b.click_button('Update')

        self.add_wf_module('Filter')
        self.select_column('column', 'data', wait=True)  # wait for module load
        b.select('condition', 'Greater than')
        b.fill_in('value', '-0.5', wait=True)  # wait for field to appear

        # Enable notifications
        with b.scope('.wf-module[data-module-name="Filter"]'):
            b.click_button('Email alerts disabled')
        # 'Turn on' is a checkbox, but it has display:none so Webdriver can't
        # see it.
        b.click_whatever('label', text='Turn on', wait=True)  # wait for modal
        b.click_button('×')

        # Now change the fetched data
        b.click_button('Update')

        path = '/' + b.get_url().split('/', 3)[-1]

        def got_notification_email(_unused):
            message = self.account_admin.latest_sent_email
            if not message:
                return False
            # Get payload at index 1: the text/html payload
            body = message.get_payload()[1].get_payload()
            return path in body and 'has been updated with new data' in body

        timeout = b.default_wait_timeout
        WebDriverWait(None, timeout).until(got_notification_email)

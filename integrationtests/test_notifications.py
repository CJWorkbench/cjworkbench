# coding=utf-8
from selenium.webdriver.support.wait import WebDriverWait
from integrationtests.utils import LoggedInIntegrationTest


class TestNotifications(LoggedInIntegrationTest):
    def setUp(self):
        super().setUp()

        b = self.browser
        b.click_button('Create Workflow')

        # wait for page load
        b.assert_element('input[name="name"][value="Untitled Workflow"]', wait=True)

    def test_notifications(self):
        b = self.browser

        self.import_module('random20floats')
        self.import_module('filter')

        self.add_wf_module('Random 20 Floats')
        b.click_button('Update')
        # Wait for the update to finish
        b.assert_element('button', text='Update', wait=True)

        self.add_wf_module('Filter by condition')
        # wait for module load
        self.select_column('Filter by condition', 'filters', 'data', wait=True)
        b.select('filters[0][0][condition]', 'Number is greater than')
        # wait for field to appear
        b.fill_in('filters[0][0][value]', '-0.1', wait=True)
        self.submit_wf_module()

        # Enable notifications
        with b.scope('.wf-module[data-module-name="Filter by condition"]'):
            # [adamhooper, 2018-10-26] wait because one time I got
            # ElementNotFound on my dev machine
            b.click_button('Email alerts disabled', wait=True)
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
        WebDriverWait(None, 30 + timeout).until(got_notification_email)

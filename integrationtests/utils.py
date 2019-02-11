# Utilities for integration tests
import unittest
import email.message
from typing import Optional
import re

from integrationtests.browser import Browser
from integrationtests.helpers import accounts
from integrationtests.helpers.modules import import_workbench_module


_url_regex = re.compile('https?://[^\\s]+')


def find_url_in_email(message: email.message.Message) -> Optional[str]:
    """Return the first URL in the given message's payload, or None."""
    body = message.get_payload()
    match = _url_regex.search(body)

    if not match:
        return None
    return match.group(0)


class WorkbenchBase(unittest.TestCase):
    serve_static = True
    live_server_url = 'http://frontend:8080'
    db_connect_str = 'user=cjworkbench host=workbench-db password=cjworkbench'
    data_path = '/app'
    account_admin = accounts.AccountAdmin(live_server_url, db_connect_str,
                                          data_path)

    def setUp(self):
        super().setUp()

        self.account_admin.clear_data_from_previous_tests()

        # self.current_site = Site.objects.get_current()
        # self.SocialApp1 = self.current_site.socialapp_set.create(
        #     provider="facebook",
        #     name="Facebook",
        #     client_id="1234567890",
        #     secret="0987654321",
        # )
        # self.SocialApp2 = self.current_site.socialapp_set.create(
        #     provider="google",
        #     name="Google",
        #     client_id="1234567890",
        #     secret="0987654321",
        # )

        self.browser = Browser(base_url=self.live_server_url)

    def tearDown(self):
        self.browser.quit()

    def create_browser(self):
        return Browser(base_url=self.live_server_url)

    # TODO move to a helper .py file
    def import_module(self, slug: str) -> None:
        import_workbench_module(self.browser, slug)

    # TODO move to a helper .py file
    def add_wf_module(self, name: str, position=None) -> None:
        """Adds module with name 'name' to the workflow.

        Keyword arguments:
        position -- if set, add after the 'position'th existing module.
        """
        b = self.browser

        if position is None:
            with b.scope('.in-between-modules:last-child'):
                b.click_button('ADD STEP')
        else:
            i = position * 2 + 1
            with b.scope(f'.in-between-modules:nth-child({i})'):
                b.click_button('ADD STEP')

        # Search. That way, we won't need to worry about overflow:auto
        b.fill_in('moduleQ', name)

        b.click_whatever('li.module-search-result', text=name)

        b.assert_element(
            f'.wf-module[data-module-name="{name}"]:not(.status-busy)',
            wait=True
        )

    # TODO move to a helper .py file
    def delete_wf_module(self, position: int) -> None:
        """Deletes module at index `position` from the workflow.

        The first module has `position == 0`.
        """
        b = self.browser

        with b.scope(f'.wf-module:nth-child({position * 2 + 2})'):
            b.click_button('more', visible='all')

        # Dropdown menu is at root of document (in a <Portal>)
        with b.scope('.dropdown-menu'):
            b.click_button('Delete')

    # TODO move to a helper .py file
    def add_csv_data_module(self, csv=None):
        """Adds Paste Data module to the workflow with given data

        csv -- Text of csv. If not set, use default data.
        """
        if csv is None:
            csv = '\n'.join([
                'Month,Amount,Name',
                'Jan,10,Alicia Aliciason',
                'Feb,666,Fred Frederson',
            ])

        self.browser.click_button('ADD STEP')
        self.browser.fill_in('moduleQ', 'Paste data')
        self.browser.click_whatever('.module-search-result', text='Paste data')

        # wait for wfmodule to appear
        self.browser.fill_in('csv', csv, wait=True)
        # blur, to begin saving result to server
        self.browser.click_whatever('ul.metadata-container', text='by')
        # and for some reason, that doesn't do the trick! Focus again?
        self.browser.click_whatever('textarea[name="csv"]')

    # TODO move to a helper .py file
    def select_column(self, module_name: str, name: str, text: str,
                      **kwargs) -> None:
        """Selects 'text' in the ColumnSelect box with name 'name'.

        Waits for '.loading' to disappear before filling in the text.

        Note: unlike browser.select(), this does _not_ handle id or
        label locators.

        Keyword arguments:
        wait -- True or number of seconds to wait until element appears
        """
        with self.browser.scope(
            (
                f'.wf-module[data-module-name="{module_name}"] '
                f'.param[data-name="{name}"]'
            ),
            **kwargs
        ):
            self.browser.assert_element(
                f'.react-select:not(.loading)',
                wait=True
            )
            self.browser.click_whatever('.react-select__dropdown-indicator')

        self.browser.click_whatever('.react-select__option', text=text)

    # TODO move to a helper .py file
    def select_tab_param(self, module_name: str, name: str, text: str,
                         **kwargs) -> None:
        """
        Select 'text' in the TabParam box with name 'name'.

        Note: unlike browser.select(), this does _not_ handle id or
        label locators.

        Keyword arguments:
        wait -- True or number of seconds to wait until element appears
        """
        with self.browser.scope(
            (
                f'.wf-module[data-module-name="{module_name}"] '
                f'.param[data-name="{name}"]'
            ),
            **kwargs
        ):
            self.browser.click_whatever('.react-select__dropdown-indicator')

        self.browser.click_whatever('.react-select__option', text=text)

    def submit_wf_module(self, **kwargs):
        """
        Click the submit button of the active WfModule.

        Keyword arguments:
        wait -- True or number of seconds to wait until element is ready
        """
        self.browser.click_whatever(
            'form.module-card-params button[name=submit]:not(:disabled)',
            **kwargs
        )


# Derive from this to perform all tests logged in
class LoggedInIntegrationTest(WorkbenchBase):
    def setUp(self):
        super().setUp()

        # is_staff=True so user can import modules to use in e.g. lesson tests
        self.user = self.account_admin.create_user('user@example.org',
                                                   is_staff=True)

        accounts.login(self.browser, self.user.email, self.user.email)

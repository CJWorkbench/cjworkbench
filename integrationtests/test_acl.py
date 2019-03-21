import time
from integrationtests.utils import WorkbenchBase
from integrationtests.helpers import accounts


class TestExampleWorkflow(WorkbenchBase):
    def setUp(self):
        super().setUp()

        self.user1 = self.account_admin.create_user('a@example.org')
        self.user2 = self.account_admin.create_user('b@example.org')

    def _create_workflow(self):
        b = self.browser

        b.visit('/workflows/')
        b.click_button('Create Workflow', wait=True)  # wait for React render
        # Wait for page to load
        b.assert_element('input[name="name"][value="Untitled Workflow"]',
                         wait=True)

        b.fill_in('name', 'Example Workflow')

        self.add_wf_module('Paste data')
        b.fill_in('csv', 'foo,bar,baz\n1,2,\n2,3,\n3,4,', wait=True)

    def _share_workflow_with(self, email, can_edit):
        b = self.browser
        b.click_button('Share')

        with b.scope('.share-modal', wait=True):  # wait for dialog
            # wait for collaborators to load
            b.fill_in('email', 'b@example.org', wait=True)
            b.click_button('Grant access')
            url = b.text('.url')

            # This fires and forgets an AJAX request. Wait for it to finish.
            time.sleep(2)

        if can_edit:
            b.click_button('Can view')
            b.click_button('Can edit')
            # This fires and forgets a _second_ AJAX request. Again: wait
            # for it to finish.
            time.sleep(2)

        with b.scope('.share-modal'):
            b.click_button('Close')

        return url

    def test_share_read_only(self):
        b = self.browser

        accounts.login(b, 'a@example.org', 'a@example.org')
        self._create_workflow()
        url = self._share_workflow_with('b@example.org', False)

        self.browser.clear_cookies()

        accounts.login(b, 'b@example.org', 'b@example.org')
        b.visit(url)

        # We see things
        b.assert_element('.wf-module[data-module-name="Paste data"]',
                         wait=True)

        # We can't edit them
        b.assert_no_element('button', text='ADD STEP')

        # We can view collaborators, read-only
        b.click_button('Share')
        with b.scope('.share-modal', wait=True):  # wait for dialog
            b.assert_element('.acl-entry.owner', text='a@example.org',
                             wait=True)  # wait for collaborator list
            b.assert_element('.acl-entry .email', text='b@example.org')
            b.assert_no_element('button.delete')  # can't edit collaborators

    def test_share_read_write(self):
        b = self.browser

        accounts.login(b, 'a@example.org', 'a@example.org')
        self._create_workflow()
        url = self._share_workflow_with('b@example.org', True)

        self.browser.clear_cookies()

        accounts.login(b, 'b@example.org', 'b@example.org')
        b.visit(url)

        # We see things
        b.assert_element('.wf-module[data-module-name="Paste data"]',
                         wait=True)

        # We can edit them
        b.fill_in('csv', 'A,B\n1,2')
        self.submit_wf_module()
        b.assert_element('.column-key', text='A', wait=True)

        # We can view collaborators, read-only
        b.click_button('Share')
        with b.scope('.share-modal', wait=True):  # wait for dialog
            b.assert_element('.acl-entry.owner', text='a@example.org',
                             wait=True)  # wait for collaborator list
            b.assert_element('.acl-entry .email', text='b@example.org')
            b.assert_no_element('button.delete')  # can't edit collaborators

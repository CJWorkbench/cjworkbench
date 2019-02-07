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
        b.assert_element('input[name="name"][value="Untitled Workflow"]', wait=True)

        b.fill_in('name', 'Example Workflow')

        self.add_wf_module('Paste data')
        b.fill_in('csv', 'A,B\n1,2,\n2,3', wait=True)

    def test_tabs_have_distinct_modules(self):
        b = self.browser

        accounts.login(b, 'a@example.org', 'a@example.org')
        self._create_workflow()

        b.click_button('Create tab')

        # Switch to Tab 2
        # Needs visible=False because there is no visible text. The user sees
        # the tab name as an <input> _value_; 'Tab 2' also appears as text but
        # that text is _invisible_, used only to size the <input>.
        b.click_whatever('div.tabs>ul>li:not(.pending) .tab-name',
                         text='Tab 2', visible=False, wait=True)
        b.assert_no_element('.wf-module[data-module-name="Paste data"]')

        # Add a module that should not appear on Tab 1
        self.add_wf_module('Add from URL')

        # Switch to Tab 1
        # visible=False again
        b.click_whatever('.tab-name', text='Tab 1', visible=False)
        b.assert_element('.wf-module[data-module-name="Paste data"]')
        b.assert_no_element('.wf-module[data-module-name="Add from URL"]')

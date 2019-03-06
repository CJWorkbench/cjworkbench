from integrationtests.utils import LoggedInIntegrationTest


class TestQuickFix(LoggedInIntegrationTest):
    def _blur(self):
        self.browser.click_whatever('.module-name', text='Paste data')

    def _create_simple_workflow(self):
        b = self.browser

        b.click_button('Create Workflow')
        b.assert_element('input[name="name"][value="Untitled Workflow"]',
                         wait=True)  # Wait for page to load

        b.fill_in('name', 'Example Workflow')

        self.add_wf_module('Paste data')
        b.fill_in('csv', 'A,B\n2012-01-01,1\n2012-02-03,3\n2012-01-01,2',
                  wait=True)
        self.submit_wf_module()

        # Wait for table to load
        b.assert_element('.column-key', text='A text', wait=True)

    def test_quick_fix_group_by_date(self):
        # https://www.pivotaltracker.com/story/show/160700316
        b = self.browser

        self._create_simple_workflow()

        self.import_module('converttodate')

        self.add_wf_module('Group by date')
        self.select_column('Group by date', 'column', 'A')
        self.submit_wf_module()

        # Wait for error to occur
        b.assert_element('.wf-module-error-msg',
                         text='Column "A" must be Date & Time',
                         wait=True)
        b.click_button('Convert')

        # Wait for module to appear
        b.assert_element('.module-name', text='Convert to date & time',
                         wait=True)

        # Click back to "Group by date" to see its output
        b.click_whatever('.module-name', text='Group by date')
        # Wait for render
        b.assert_no_element('.wf-module-error-msg', wait=True)
        # Wait for table render
        b.assert_element('.column-key', text='count number', wait=True)

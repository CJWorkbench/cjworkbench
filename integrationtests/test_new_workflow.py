from integrationtests.utils import LoggedInIntegrationTest
import re

class TestNewWorkflow(LoggedInIntegrationTest):

    def test_new_workflow(self):
        b = self.browser

        b.find_by_css('.new-workflow-button').click()

        # should now be at workflow screen
        self.assertTrue(re.match(r'.*/workflows/\d+/?$', b.url))

        # Empty module stack
        self.assertTrue(b.is_text_present('DROP MODULE HERE'))

        # Module library
        self.assertTrue(b.is_text_present('Add data'))
        self.assertTrue(b.is_text_present('Add data alert'))

        # nav bar and context menu
        self.assertTrue(b.is_text_present('Duplicate'))
        self.assertTrue(b.is_text_present('Share'))

        self.assertTrue(b.is_text_present('My Workflows'))
        self.assertTrue(b.is_text_present('Log Out'))
        self.assertTrue(b.is_text_present('Import Module'))

        # output pane
        self.assertTrue(b.is_text_present('Rows'))
        self.assertTrue(b.is_text_present('Columns'))

from integrationtests.utils import LoggedInIntegrationTest
import re

class TestNewWorkflow(LoggedInIntegrationTest):

    def test_new_workflow(self):
        b = self.browser

        b.find_by_css('.new-workflow-button').click()

        # should now be at workflow screen
        self.assertTrue(re.match(r'.*/workflows/\d+/?$', b.url))

        # Empty module stack
        self.assertTrue(b.is_text_present('DRAG AND DROP MODULE HERE'))

        # Module library
        self.assertTrue(b.is_text_present('Add data'))
        self.assertTrue(b.is_text_present('Add data alert'))
        self.assertTrue(b.is_text_present('IMPORT CUSTOM MODULE'))

        # nav bar
        self.assertTrue(b.is_text_present('Duplicate'))
        self.assertTrue(b.is_text_present('Share'))

        # output pane
        self.assertTrue(b.is_text_present('Rows'))
        self.assertTrue(b.is_text_present('Columns'))

from integrationtests.utils import LoggedInIntegrationTest
import re

class TestNewWorkflow(LoggedInIntegrationTest):

    def test_new_workflow(self):
        b = self.browser
        b.visit(self.live_server_url + '/workflows')

        b.find_by_css('.new-workflow-button').click()

        # if we created a new workflow, we should now be at workflow screen
        self.assertTrue(re.match(r'.*/workflows/\d+/?$', b.url))

        # Check that all the parts exist
        self.assertTrue(b.is_text_present('DRAG AND DROP MODULE HERE'))
        self.assertTrue(b.is_text_present('Add data'))
        self.assertTrue(b.is_text_present('IMPORT CUSTOM MODULE'))
        self.assertTrue(b.is_text_present('Duplicate'))
        self.assertTrue(b.is_text_present('Rows'))

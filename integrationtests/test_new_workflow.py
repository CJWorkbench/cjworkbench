from integrationtests.utils import LoggedInIntegrationTest
import re

class TestNewWorkflow(LoggedInIntegrationTest):
    def test_new_workflow(self):
        b = self.browser

        b.click_button('Create Workflow')

        # Empty module stack
        # wait: for page to load
        b.wait_for_element('.modulestack-empty', text='DROP MODULE HERE')

        # Module library
        b.assert_element('.category-name', text='Add data')
        b.assert_element('.ML-module', text='Add from URL')

        # nav bar
        with b.scope('nav'):
            b.assert_element('button', text='Duplicate')
            b.assert_element('button', text='Share')

            b.click_button('menu')
            b.assert_element('.dropdown-item', text='Import Module')
            b.assert_element('.dropdown-item', text='My Workflows')
            b.assert_element('.dropdown-item', text='Log Out')

        # output pane
        with b.scope('.outputpane-table'):
            b.assert_element('.outputpane-header div', text='Rows')
            b.assert_element('.outputpane-header div', text='Columns')

from integrationtests.utils import LoggedInIntegrationTest


class TestNewWorkflow(LoggedInIntegrationTest):
    def test_new_workflow(self):
        b = self.browser

        b.click_button("Create Workflow")

        # Empty module stack
        b.wait_for_element(".module-stack", wait=True)

        # nav bar
        with b.scope(".navbar"):
            b.assert_element("button", text="Duplicate")
            b.assert_element("button", text="Share")

        # output pane
        with b.scope(".outputpane-table"):
            b.assert_element(".outputpane-header div", text="ROWS")
            b.assert_element(".outputpane-header div", text="COLUMNS")

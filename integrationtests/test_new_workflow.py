from integrationtests.utils import LoggedInIntegrationTest


class TestNewWorkflow(LoggedInIntegrationTest):
    def test_new_workflow(self):
        b = self.browser

        b.click_button("Create your first workflow")

        self.import_module("pastecsv")

        # empty output pane
        b.assert_element(".add-data-modal h5", text="CHOOSE A DATA SOURCE")

        b.click_link("Paste data")
        b.assert_element(".cell-text", wait=True)

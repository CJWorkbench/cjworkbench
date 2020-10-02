from integrationtests.utils import LoggedInIntegrationTest


class TestStep(LoggedInIntegrationTest):
    def setUp(self):
        super().setUp()

        b = self.browser
        b.click_button("Create Workflow")  # navigate to a workflow page

        # wait for page load
        b.assert_element('input[name="name"][value="Untitled Workflow"]', wait=True)

    def test_module_buttons_exist(self):
        b = self.browser

        self.add_csv_data_module()

        # should be un-collapsed
        b.assert_element('button[name="collapse module"] .icon-caret-down')

        b.hover_over_element(".module-name")
        b.assert_element('a[title="Help for this module"]')
        b.assert_element('button[title="Edit Note"]')
        b.assert_element("button[title=more]")

    def test_export(self):
        b = self.browser

        self.add_csv_data_module()

        b.hover_over_element(".module-card-header", wait=True)
        b.click_button("more")
        b.click_button("Export")

        # Wait for modal to appear
        b.assert_element("a[download][href$=csv]", wait=True)
        b.assert_element("a[download][href$=json]")
        # TODO actually test the export.

    # def test_zzz_delete_module(self):
    #     b = self.browser
    #
    #     self.assertTrue(b.is_element_present_by_css('.wf-card'))
    #
    #     b.find_by_css('.module-context-menu--icon').click()
    #     b.find_by_text('Delete').first.click()
    #
    #     self.assertFalse(b.is_element_present_by_css('.wf-card'))

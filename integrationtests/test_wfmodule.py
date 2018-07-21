from integrationtests.utils import LoggedInIntegrationTest


class TestWfModule(LoggedInIntegrationTest):
    def setUp(self):
        super().setUp()

        b = self.browser
        b.click_button('Create Workflow')  # navigate to a workflow page

        # wait for page load
        b.assert_element('input[name="name"][value="New Workflow"]', wait=True)

    def test_module_buttons_exist(self):
        b = self.browser

        self.add_csv_data_module()

        # Wait for wfmodule to appear
        b.hover_over_element('.module-card-header', wait=True)

        b.assert_element('.icon-caret-down')  # should be uncollapsed
        b.assert_element('.icon-help')
        b.assert_element('.icon-note')
        b.assert_element('button[title=more]')

    def test_export(self):
        self.add_csv_data_module()

        b = self.browser
        b.hover_over_element('.module-card-header', wait=True)
        b.click_button('more')
        b.click_button('Export')

        b.assert_element('a[download][href$=csv]')
        b.assert_element('a[download][href$=json]')
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

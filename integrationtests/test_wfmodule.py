from integrationtests.utils import LoggedInIntegrationTest

# WfModule expand/collapse, notes, context menu, export, delete
class TestWfModule(LoggedInIntegrationTest):
    def setUp(self):
        super().setUp()

        b = self.browser
        b.click_button('Create Workflow') # navigate to a workflow page

        # wait for page load
        b.assert_element('input[name="name"][value="New Workflow"]', wait=True)


    def _add_paste_data_module(self):
        self.browser.click_button('Add Module')
        self.browser.fill_in('moduleQ', 'Paste data')
        self.browser.click_whatever('.module-search-result', text='Paste data')


    def _add_csv_data(self):
        csv = 'Month,Amount,Name\nJan,10,Alicia Aliciason\nFeb,666,Fred Frederson\n'

        self._add_paste_data_module()

        # wait for wfmodule to appear
        self.browser.fill_in('csv', csv, wait=True)
        # blur, to begin saving result to server
        self.browser.click_whatever('ul.metadata-container', text='by')
        # and for some reason, that doesn't do the trick! Focus again?
        self.browser.click_whatever('textarea[name="csv"]')


    def test_paste_csv_workflow(self):
        self._add_csv_data()

        b = self.browser

        b.assert_element('label', text='Has header row')

        # output table with correct values
        # Wait for the table to load
        b.assert_element('.react-grid-HeaderCell', text='Month', wait=500)
        b.assert_element('.react-grid-Cell', text='Jan')
        b.assert_element('.react-grid-Cell', text='Feb')
        b.assert_element('.react-grid-HeaderCell', text='Name')
        b.assert_element('.react-grid-Cell', text='Alicia Aliciason')
        b.assert_element('.react-grid-Cell', text='Fred Frederson')


    def test_module_buttons_exist(self):
        b = self.browser

        self._add_paste_data_module()

        # Wait for wfmodule to appear
        b.hover_over_element('.module-card-header', wait=True)

        b.assert_element('.icon-sort-down') # should be uncollapsed
        b.assert_element('.icon-help')
        b.assert_element('.icon-note')
        b.assert_element('button[title=more]')


    def test_export(self):
        self._add_csv_data()

        b = self.browser
        b.hover_over_element('.module-card-header', wait=True)
        b.click_button('more')
        b.click_button('Export')

        b.assert_element('a[download][href$=csv]')
        b.assert_element('a[download][href$=json]')
        # TODO actually test the export.


    # Delete module test fails because it depends on websockets, and manage.py does not run channels server

    # zzz to ensure this test runs last
    # def test_zzz_delete_module(self):
    #     b = self.browser
    #
    #     self.assertTrue(b.is_element_present_by_css('.wf-card')) # module is there
    #
    #     b.find_by_css('.module-context-menu--icon').click()
    #     b.find_by_text('Delete').first.click()
    #
    #     self.assertFalse(b.is_element_present_by_css('.wf-card')) # now it's gone

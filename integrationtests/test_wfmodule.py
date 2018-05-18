from integrationtests.utils import LoggedInIntegrationTest
from server.models import ModuleVersion
from server.tests.utils import mock_csv_text2, add_new_workflow, add_new_wf_module, get_param_by_id_name

# WfModule expand/collapse, notes, context menu, export, delete
class TestWfModule(LoggedInIntegrationTest):
    def setUp(self):
        super().setUp()

        b = self.browser
        b.click_button('New') # navigate to a workflow page

        # wait for page load
        b.assert_element('input[name="title"]', text='New Workflow', wait=True)


    def test_paste_csv_workflow(self):
        csv = 'Month,Amount,Name\nJan,10,Alicia Aliciason\nFeb,666,Fred Frederson'

        b = self.browser

        b.click_link('Paste data')
        # wait for wfmodule to appear
        b.fill_in('textarea[name=csv]', csv, wait=True)

        b.click_whatever('.outputpane-header')

        b.assert_element('

        self.assertTrue(b.is_element_present_by_text('Has header row'))

        # output table with correct values
        self.assertTrue(b.is_element_present_by_text('Jan'))
        self.assertTrue(b.is_element_present_by_text('Feb'))
        self.assertTrue(b.is_element_present_by_text('Alicia Aliciason'))
        self.assertTrue(b.is_element_present_by_text('Fred Frederson'))

    def test_module_buttons_exist(self):
        b = self.browser

        header = b.find_by_css('.module-card-header')
        header.first.mouse_over()

        self.assertTrue(b.is_element_present_by_css('.icon-help'))
        self.assertTrue(b.is_element_present_by_css('.icon-sort-up'))  # should be uncollapsed, else .icon-collapse-o
        self.assertTrue(b.is_element_present_by_css('.icon-note'))
        self.assertTrue(b.is_element_present_by_css('.context-button'))

    def test_context_menu_and_export_dialog(self):
        b = self.browser
        header = b.find_by_css('.module-card-header')
        header.find_by_css('.context-buttons--container').first.mouse_over()
        header.find_by_css('.context-button--icon').click()

        # check for correct items
        self.assertTrue(header.find_by_css('.dropdown-item').first.visible)
        self.assertEqual(len(header.find_by_css('.dropdown-item')), 2)
        self.assertTrue(header.find_by_text('Export'))
        self.assertTrue(header.find_by_text('Delete'))

        # open, then close the export dialog
        header.find_by_text('Export').first.click()
        self.assertTrue(b.is_element_present_by_text('EXPORT DATA'))
        self.assertTrue(b.find_link_by_partial_href('/public/moduledata/live/' + str(self.wfm.id) + '.csv')) # b not header as modal is a portal component
        self.assertTrue(b.find_link_by_partial_href('/public/moduledata/live/' + str(self.wfm.id) + '.json'))

        b.find_by_text('Done').first.click()
        self.assertFalse(b.is_element_present_by_text('Export Data'))


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

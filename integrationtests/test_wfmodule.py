from integrationtests.utils import DummyWorkflowIntegrationTest
from server.tests.utils import mock_csv_text2
import time

# WfModule expand/collapse, notes, context menu, export, delete
class TestWfModule(DummyWorkflowIntegrationTest):

    # utility to replace broken mouse_out, https://github.com/cobrateam/splinter/issues/579
    def mouse_to_logo(self):
        self.browser.find_by_text('Workbench').first.mouse_over()

    def test_paste_csv_workflow(self):
        b = self.browser

        # module library
        self.assertTrue(b.is_element_present_by_text('Paste data'))
        self.assertTrue(b.is_element_present_by_text(mock_csv_text2))

        self.assertTrue(b.is_element_present_by_text('Has header row'))

        # output table with correct values
        self.assertTrue(b.is_element_present_by_text('Jan')) 
        self.assertTrue(b.is_element_present_by_text('Feb'))
        self.assertTrue(b.is_element_present_by_text('Alicia Aliciason'))
        self.assertTrue(b.is_element_present_by_text('Fred Frederson'))

    def test_module_buttons_exist(self):
        b = self.browser

        header = b.find_by_css('.module-header-content')
        header.first.mouse_over()

        self.assertTrue(b.is_element_present_by_css('.icon-help'))
        self.assertTrue(b.is_element_present_by_css('.icon-sort-up'))  # should be uncollapsed, else .icon-collapse-o
        self.assertTrue(b.is_element_present_by_css('.icon-note'))
        self.assertTrue(b.is_element_present_by_css('.context-button'))

    def test_context_menu_and_export_dialog(self):
        b = self.browser
        header = b.find_by_css('.module-header-content')

        # context menu not open yet
        self.assertFalse(header.find_by_css('.dropdown-menu-item').first.visible)

        header.find_by_css('.module-menu-icon').click()

        # check for correct items
        self.assertTrue(header.find_by_css('.dropdown-menu-item').first.visible)
        self.assertEqual(len(header.find_by_css('.dropdown-menu-item')), 2)
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
    #     b.find_by_css('.module-menu-icon').click()
    #     b.find_by_text('Delete').first.click()
    #
    #     self.assertFalse(b.is_element_present_by_css('.wf-card')) # now it's gone

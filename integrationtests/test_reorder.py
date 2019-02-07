# Uncomment when drag-and-drop testing is fixed (Firefox upgrade?)
#import json
#import re
#
#from integrationtests.utils import LoggedInIntegrationTest
#
#class TestReorderColumns(LoggedInIntegrationTest):
#    def setUp(self):
#        super().setUp()
#
#        b = self.browser
#        b.click_button('Create Workflow') # navigate to a workflow page
#
#        # wait for page load
#        b.assert_element('input[name="name"][value="Untitled Workflow"]', wait=True)
#
#        self.browser.click_button('ADD STEP')
#        self.browser.fill_in('moduleQ', 'Paste data')
#        self.browser.click_whatever('.module-search-result', text='Paste data')
#
#        csv = 'Month,Amount,Name\nJan,10,Alicia Aliciason\nFeb,666,Fred Frederson\n'
#
#        # wait for wfmodule to appear
#        b.fill_in('csv', csv, wait=True)
#        # blur, to begin saving result to server
#        b.click_whatever('ul.WF-meta span', text='by')
#        # and for some reason, that doesn't do the trick! Focus again?
#        b.click_whatever('textarea[name="csv"]')
#
#        # wait for table to appear
#        b.assert_element('.react-grid-HeaderCell', text='Month', wait=True)
#
#
#    def test_drag_once(self):
#        # Drill past Browser's layer of abstraction: use Capybara for drag-and-drop
#        page = self.browser.page
#        source = page.find('.react-grid-HeaderCell', text='Name')
#        target = page.find('.react-grid-HeaderCell', text='Amount')
#
#        source.drag_to(target)
#        #import time; time.sleep(200)
#
#        b = self.browser
#        # wait for module to be created
#        b.assert_element('.module-card-header', name='Reorder columns', wait=True)
#        # wait for table to reload
#        b.assert_element('.react-grid-HeaderRow', text=re.compile('.*Month.*Name.*Amount.*'))

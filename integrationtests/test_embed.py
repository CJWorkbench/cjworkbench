from integrationtests.utils import LoggedInIntegrationTest
import re

# WfModule expand/collapse, notes, context menu, export, delete
class TestEmbed(LoggedInIntegrationTest):
    def setUp(self):
        super().setUp()

        b = self.browser
        b.click_button('Create Workflow') # navigate to a workflow page

        # wait for page load
        b.assert_element('input[name="name"][value="Untitled Workflow"]', wait=True)


    def test_embed(self):

        b = self.browser

        # Create workflow with chart
        self.add_csv_data_module("a,b,c\n1,2,3")
        self.import_module('linechart')
        self.add_wf_module('Line Chart')

        b.assert_element('iframe', wait=True) # chart should load
        b.assert_no_element('.spinner-container-transparent', wait=True) # embed button not clickable until spinner goes away

        # Open embed dialog, set public and get code
        b.click_button('embed')
        b.assert_element('div', text='This workflow is currently private', wait=True)
        b.click_whatever('.action-button', text='Set Public', wait=True)
        embed_text = b.text('.modal-body code', wait=True)

        url = re.search('<iframe src="(http://.*/embed/\d+)" .*>', embed_text).group(1)

        # Vist URL and ensure it loads the embedded content correctly
        b.visit(url)
        b.assert_element('iframe', wait=True)

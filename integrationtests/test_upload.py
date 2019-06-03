from pathlib import Path
from integrationtests.utils import LoggedInIntegrationTest


class TestUpload(LoggedInIntegrationTest):
    def test_upload_xlsx(self):
        b = self.browser
        b.click_button('Create Workflow')

        # Empty module stack
        b.wait_for_element('.module-stack')

        self.add_data_step('Upload')
        b.wait_for_element('label', text='Browse')
        b.attach_file('file',
                      Path(__file__).parent / 'files' / 'example.xlsx',
                      wait=True) # Wait for file input to exist
        # submit happens automatically

        self.browser.wait_for_element(
            '.react-grid-Row:nth-child(1) .react-grid-Cell:nth-child(1)',
            text='1'
        )

    def test_upload_multipart_csv(self):
        b = self.browser
        b.click_button('Create Workflow')

        # Empty module stack
        b.wait_for_element('.module-stack')

        self.add_data_step('Upload')
        b.wait_for_element('label', text='Browse')
        b.attach_file('file',
                      Path(__file__).parent / 'files' / 'multipart.csv',
                      wait=True) # Wait for file input to exist
        # submit happens automatically

        self.browser.wait_for_element(
            '.react-grid-Row:nth-child(1) .react-grid-Cell:nth-child(1)',
            text='This file is >5MB'
        )

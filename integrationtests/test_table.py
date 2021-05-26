import re

from integrationtests.browser import Keys
from integrationtests.utils import LoggedInIntegrationTest


class TestTable(LoggedInIntegrationTest):
    def _blur(self):
        self.browser.click_whatever(".module-name", text="Paste data")

    def _create_simple_workflow(self):
        b = self.browser

        b.click_button("Create your first workflow")
        # Wait for page to load
        b.assert_element('input[name="name"][value="Untitled Workflow"]', wait=True)

        b.fill_in("name", "Example Workflow")

        self.import_module("pastecsv")
        self.add_data_step("Paste data")
        b.fill_in("csv", "string,int\nfoo,1\nbar,3\nbaz,2", wait=True)
        self.submit_step()

        # Wait for table to load
        b.assert_element(".big-table th .column-key", text="string", wait=True)

    def test_rename_column(self):
        b = self.browser

        self._create_simple_workflow()
        self.import_module("renamecolumns")

        b.click_whatever(".big-table th .column-key", text="string")
        # wait for span to become input
        b.fill_in("new-column-key", "Column A", wait=True)
        b.send_keys("new-column-key", Keys.ENTER)

        # Wait for rename module to appear, selected and set
        b.assert_element('.step[data-module-name="Rename columns"].selected', wait=True)
        b.assert_element(
            '.rename-entry[data-column-name="string"] input[value="Column A"]',
            wait=True,
        )

        # Wait for table to reload. This is crazy-hard, so we hack with sleep()
        # TODO [2018-10-11] it should be easier now, using .table-loaded
        import time

        time.sleep(1)
        b.assert_no_element(".spinner-container-transparent", wait=True)

        # Edit another column
        # Wait for spinner to disappear first
        b.click_whatever(".big-table th .column-key", text="int")
        # wait for span to become input
        b.fill_in("new-column-key", "Column B", wait=True)
        b.send_keys("new-column-key", Keys.ENTER)

        # Wait for rename module to be updated
        b.assert_element(
            '.rename-entry[data-column-name=int] input[value="Column B"]', wait=True
        )

        # Select previous output to check old column names
        b.click_whatever(".module-name", text="Paste data")
        b.assert_element(".big-table thead", text=re.compile("string.*int"), wait=True)

        # Select new output to check new column names
        b.click_whatever(".module-name", text="Rename columns")
        b.assert_element(
            ".big-table thead", text=re.compile("Column A.*Column B"), wait=True
        )

    # def _carefully_double_click_element(self, *selector, **kwargs):
    #     """Work around react-data-grid by slowwwwly double-clicking.
    #
    #     Often, double-clicks don't open an input. [adamhooper, 2018-06-20] I
    #     can't figure out why. But handling hover and click beforehand seems
    #     to fix the issue.
    #
    #     It probably has to do with react-data-grid re-rendering the cell when
    #     it changes. This sequence means the double-click will happen after
    #     all re-renders.
    #     """
    #     self.browser.hover_over_element(*selector, **kwargs)
    #     self.browser.click_whatever(*selector, **kwargs)
    #     self.browser.double_click_whatever(*selector, **kwargs)
    #
    # def test_edit_cell(self):
    #     b = self.browser
    #
    #     self._create_simple_workflow()
    #
    #     self._carefully_double_click_element('.react-grid-Cell:not(.react-grid-Cell--locked)', text='1')
    #     b.fill_text_in_whatever('4', '.react-grid-Cell input', wait=True)  # wait for prompt
    #     self._blur()  # commit
    #
    #     # Wait for edit module to appear, selected and set
    #     b.assert_element('.step[data-module-name="Edit Cells"].selected', wait=True)
    #     b.assert_no_element('.react-grid-Cell:not(.react-grid-Cell--locked)', text='1', wait=True)
    #     b.assert_element('.react-grid-Cell', text='4', wait=True)
    #
    #     # Fill in one more edit
    #     self._carefully_double_click_element('.react-grid-Cell:not(.react-grid-Cell--locked)', text='3')
    #     b.fill_text_in_whatever('5', '.react-grid-Cell input', wait=True)  # wait for prompt
    #
    #     b.click_whatever('i.context-collapse-button.icon-caret-right')
    #     b.assert_element('.edited-column', text='int', wait=True)

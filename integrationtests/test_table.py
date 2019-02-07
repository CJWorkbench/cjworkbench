import re
from integrationtests.utils import LoggedInIntegrationTest
from integrationtests.browser import Keys


class TestTable(LoggedInIntegrationTest):
    def _blur(self):
        self.browser.click_whatever('.module-name', text='Paste data')

    def _create_simple_workflow(self):
        b = self.browser

        b.click_button('Create Workflow')
        # Wait for page to load
        b.assert_element('input[name="name"][value="Untitled Workflow"]', wait=True)

        b.fill_in('name', 'Example Workflow')

        self.add_wf_module('Paste data')
        b.fill_in('csv', 'string,int\nfoo,1\nbar,3\nbaz,2', wait=True)
        self.submit_wf_module()

        self._blur()  # to load table

        # Wait for table to load
        b.assert_element('.column-key', text='string', wait=True)

    # def test_click_to_sort(self):
    #     b = self.browser
    #
    #     self._create_simple_workflow()
    #
    #     with b.scope('.react-grid-HeaderCell:nth-child(1)'):
    #         b.hover_over_element('.sort-container')
    #         b.click_button('Sort', wait=True)  # wait for it to appear
    #
    #     # Wait for sort module to appear, selected
    #     b.assert_element('.wf-module[data-module-name=Sort].selected', wait=True)
    #     # Wait for table to load
    #     b.assert_element('.wf-module[data-module-name=Sort] select[name=column] option:checked', text='string')
    #     b.assert_element('.wf-module[data-module-name=Sort] select[name=dtype] option:checked', text='String')
    #     b.assert_element('.wf-module[data-module-name=Sort] select[name=direction] option:checked', text='Ascending')
    #
    #     # Click again, see "descending"
    #     with b.scope('.react-grid-HeaderCell:nth-child(1)'):
    #         b.hover_over_element('.sort-container')
    #         b.click_button('Sort', wait=True)  # wait for it to appear
    #     b.assert_element('.wf-module[data-module-name=Sort] select[name=direction] option:checked', text='Descending', wait=True)
    #
    #     # Assert sorted in descending order: "foo", "baz", "bar"
    #     # We may need to wait for the table to load. We may need to wait more
    #     # than once, too, as table ordering can change repeatedly from above
    #     # steps.
    #     b.assert_element('.react-grid-Row:nth-child(1)', text='foo', wait=True)
    #     b.assert_element('.react-grid-Row:nth-child(2)', text='baz', wait=True)
    #     b.assert_element('.react-grid-Row:nth-child(3)', text='bar', wait=True)

    def test_rename_column(self):
        b = self.browser

        self._create_simple_workflow()

        b.click_whatever('.column-key', text='string')
        # wait for span to become input
        b.fill_in('new-column-key', 'Column A', wait=True)
        b.send_keys('new-column-key', Keys.ENTER)

        # Wait for rename module to appear, selected and set
        b.assert_element('.wf-module[data-module-name="Rename columns"].selected', wait=True)
        b.assert_element('.rename-entry[data-column-name="string"] input[value="Column A"]', wait=True)

        # Wait for table to reload. This is crazy-hard, so we hack with sleep()
        # TODO [2018-10-11] it should be easier now, using .table-loaded
        import time; time.sleep(1)
        b.assert_no_element('.spinner-container-transparent', wait=True)

        # Edit another column
        # Wait for spinner to disappear first
        b.click_whatever('.column-key', text='int')
        # wait for span to become input
        b.fill_in('new-column-key', 'Column B', wait=True)
        b.send_keys('new-column-key', Keys.ENTER)

        # Wait for rename module to be updated
        b.assert_element(
            '.rename-entry[data-column-name=int] input[value="Column B"]',
            wait=True
        )

        # Select previous output to check old column names
        b.click_whatever('.module-name', text='Paste data')
        b.assert_element('.react-grid-Header', text=re.compile('string.*int'),
                         wait=True)

        # Select new output to check new column names
        b.click_whatever('.module-name', text='Rename columns')
        b.assert_element('.react-grid-Header',
                         text=re.compile('Column A.*Column B'), wait=True)

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
    #     b.assert_element('.wf-module[data-module-name="Edit Cells"].selected', wait=True)
    #     b.assert_no_element('.react-grid-Cell:not(.react-grid-Cell--locked)', text='1', wait=True)
    #     b.assert_element('.react-grid-Cell', text='4', wait=True)
    #
    #     # Fill in one more edit
    #     self._carefully_double_click_element('.react-grid-Cell:not(.react-grid-Cell--locked)', text='3')
    #     b.fill_text_in_whatever('5', '.react-grid-Cell input', wait=True)  # wait for prompt
    #
    #     b.click_whatever('i.context-collapse-button.icon-caret-right')
    #     b.assert_element('.edited-column', text='int', wait=True)

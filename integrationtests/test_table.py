from integrationtests.utils import LoggedInIntegrationTest

class TestTable(LoggedInIntegrationTest):
    def _create_simple_workflow(self):
        b = self.browser

        b.click_button('Create Workflow')
        # Wait for page to load
        b.assert_element('input[name="name"][value="New Workflow"]', wait=True)

        b.fill_in('name', 'Example Workflow')

        self.add_wf_module('Paste data')
        b.fill_in('csv', 'string,int\nfoo,1\nbar,3\nbaz,2', wait=True)

        # Blur, to load table
        b.click_whatever('div.table-info', text='ROWS')

        # Wait for table to load
        b.assert_element('.column-key', text='string', wait=True)


    def test_click_to_sort(self):
        b = self.browser

        self._create_simple_workflow()

        with b.scope('.react-grid-HeaderCell:nth-child(1)'):
            b.hover_over_element('.sort-container')
            b.click_button('Sort', wait=True)  # wait for it to appear

        # Wait for sort module to appear, selected
        b.assert_element('.wf-module[data-module-name=Sort] .module-output--selected', wait=True)
        # Wait for table to load
        b.assert_element('.wf-module[data-module-name=Sort] select[name=column] option:checked', text='string')
        b.assert_element('.wf-module[data-module-name=Sort] select[name=dtype] option:checked', text='String')
        b.assert_element('.wf-module[data-module-name=Sort] select[name=direction] option:checked', text='Ascending')

        # Click again, see "descending"
        with b.scope('.react-grid-HeaderCell:nth-child(1)'):
            b.hover_over_element('.sort-container')
            b.click_button('Sort', wait=True)  # wait for it to appear
        b.assert_element('.wf-module[data-module-name=Sort] select[name=direction] option:checked', text='Descending', wait=True)

        # Assert sorted in descending order: "foo", "baz", "bar"
        # We may need to wait for the table to load. We may need to wait more
        # than once, too, as table ordering can change repeatedly from above
        # steps.
        b.assert_element('.react-grid-Row:nth-child(1)', text='foo', wait=True)
        b.assert_element('.react-grid-Row:nth-child(2)', text='baz', wait=True)
        b.assert_element('.react-grid-Row:nth-child(3)', text='bar', wait=True)

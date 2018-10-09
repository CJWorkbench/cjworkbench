import re
from integrationtests.utils import LoggedInIntegrationTest

class TestRefine(LoggedInIntegrationTest):
    def setUp(self):
        super().setUp()

        b = self.browser
        b.click_button('Create Workflow')

        # Empty module stack
        b.wait_for_element('.module-stack')

        self.add_wf_module('Paste data')
        b.wait_for_element('textarea[name="csv"]')
        b.fill_in('csv', '''A,B
a,1
aa,1
b a,9
a b,1
a b,1
a,1
xxxy,2
xxxy,2
yxxx,1
yxyx,1
''')

        self.add_wf_module('Refine')
        self.select_column('Refine', 'column', 'A')
        b.wait_for_element('input[value="xxxy"]')

    def _fill_in_and_blur(self, *args, **kwargs):
        """
        Call fill_in(), then click to blur (thus submitting the value).

        You'll usually want to wait for the commit to complete afterwards.
        That's challenging because we don't know ahead of time what's meant
        to change.
        """
        b = self.browser
        b.fill_in(*args, **kwargs)
        b.click_whatever('.module-name', text='Refine')

    def _wait_for_table_value(self, row, column, value):
        """
        Wait for the table to show a value.

        This is the easiest way to wait for the table to update. The table
        updates _after_ the rest of the UI, and if it's adding a new value then
        we know that at the time that value is displayed, the entire update is
        complete
        """
        self.browser.wait_for_element(
            f'.react-grid-Row:nth-child({row + 1}) '
            f'.react-grid-Cell:nth-child({column + 1}) ',
            text=value
        )

    def test_manual_edits(self):
        b = self.browser

        self._fill_in_and_blur('rename[xxxy]', 'yyyy')
        self._wait_for_table_value(6, 0, 'yyyy')
        self._wait_for_table_value(7, 0, 'yyyy')
        self._fill_in_and_blur('rename[yxyx]', 'yyyy')
        self._wait_for_table_value(9, 0, 'yyyy')

        # Now the UI lets you see the group
        b.assert_element('dt:nth-child(1) input[value="yyyy"]')
        b.assert_element('dt:nth-child(1) .count', text=3)
        b.click_whatever('dt:nth-child(1) label.expand')
        b.assert_element('dd', text='xxxy')

        # That's enough. Unit tests cover all the edge cases.

    def test_cluster(self):
        b = self.browser

        b.click_button('Cluster')

        # Default algorithm: fingerprint. There may be a momentary blip of
        # progressbar.
        b.wait_for_element('th', text='Values')
        b.assert_element('.refine-modal td.cluster-size', text='3')
        b.assert_element('.refine-modal td.new-value textarea', text='a b')
        b.fill_in('value-0', 'yxyx')  # a twist: input into the next algo
        b.click_button('Merge selected')

        # Now the UI lets you see the change
        b.assert_element('dt:nth-child(1) input[value="yxyx"]')
        # here count=4, because there was an existing yxyx row
        b.assert_element('dt:nth-child(1) .count', text=4)
        self._wait_for_table_value(2, 0, 'yxyx')
        self._wait_for_table_value(3, 0, 'yxyx')
        self._wait_for_table_value(4, 0, 'yxyx')

        b.click_button('Cluster')
        b.select('algorithm', 'Edit distance')
        b.fill_in('maxDistance', '2')
        # Wait for algo to finish
        b.assert_element('.refine-modal td.cluster-size', text='5', wait=True)
        # The group is 'yxyx yxxx' => 'yxyx'
        b.fill_in('value-0', 'YYYY')
        b.uncheck('selected-1')  # Deselect the group, 'a aa => a'
        b.click_button('Merge selected')

        self._wait_for_table_value(0, 0, 'a')
        self._wait_for_table_value(1, 0, 'aa')  # deselected - not clustered
        self._wait_for_table_value(2, 0, 'YYYY')
        self._wait_for_table_value(3, 0, 'YYYY')
        self._wait_for_table_value(4, 0, 'YYYY')  # yxyx from previous step
        self._wait_for_table_value(6, 0, 'xxxy')  # distance=2 - not clustered
        self._wait_for_table_value(8, 0, 'YYYY')  # yxxx clustered

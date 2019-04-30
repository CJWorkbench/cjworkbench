from integrationtests.utils import LoggedInIntegrationTest


class TestQuickFix(LoggedInIntegrationTest):
    def test_hide_deprecated_module_from_quickfix(self):
        """A deprecated module should not appear in module search."""
        b = self.browser

        b.click_button('Create Workflow')
        b.assert_element('input[name="name"][value="Untitled Workflow"]',
                         wait=True)  # Wait for page to load

        self.import_module('deprecated-soon')

        b.click_button('ADD STEP')
        b.fill_in('moduleQ', 'Deprecation-test')
        b.assert_no_element('button.module-search-result',
                            text='Deprecation-test module')

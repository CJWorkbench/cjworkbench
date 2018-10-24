from integrationtests.utils import LoggedInIntegrationTest

class TestNewWorkflow(LoggedInIntegrationTest):
    def setUp(self):
        super().setUp()

        b = self.browser
        b.click_button('Create Workflow')

        # Empty module stack
        b.wait_for_element('.module-stack', wait=True)
        self.add_wf_module('Python')

        # Wait for dynamically-loaded editor component
        b.wait_for_element('.ace-wrapper', wait=True)

    def _execute_code(self, code):
        """Sets code in the in-browser ACE editor."""
        b = self.browser

        # Weird hack to make React aware of new code...:
        b.exec_js('ace.edit("code-editor").setValue(arguments[0])', code)
        b.click_whatever('#code-editor')

        # Code set. Run it!
        b.click_button('Run')

    def test_return_dataframe(self):
        self._execute_code("""
def process(table):
    return pd.DataFrame({"a": [1, 2]})
""")

        b = self.browser
        # wait for values to arrive from server
        b.assert_element('span.column-key', text='a', wait=True)
        b.assert_element('.react-grid-Cell', text='1', wait=True)

    def test_error_message(self):
        self._execute_code("""
def process(table):
    return p.DataFrame({"a": [1, 2]})
""")

        b = self.browser
        b.assert_element(
            '.wf-module-error-msg',
            text="Line 3: NameError: name 'p' is not defined",
            wait=True  # wait for error to arrive from server
        )

    def test_console(self):
        self._execute_code("""
def process(table):
    # Test both print() _and_ traceback
    print('Hello, world!')
    return p.DataFrame({"a": [1, 2]})
""")

        b = self.browser
        # wait for iframe to appear
        b.assert_element('.outputpane-iframe iframe', wait=True)
        with b.iframe('.outputpane-iframe iframe'):
            # wait for page load
            b.assert_element('pre', text='Hello, world!', wait=True)
            b.assert_element('pre', text="NameError: name 'p' is not defined")
